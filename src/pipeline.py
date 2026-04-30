import os
import logging
import time
import torch
import gc
import json
import numpy as np
from .proxy import generate_proxy
from .evaluator import SceneEvaluator
from .trimmer import StabilityTrimmer
from .director import Director
from . import config as default_config

logger = logging.getLogger("DroneCutPipeline")

class DroneCutPipeline:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.director = Director()
        self.evaluator = None 
        
    def _update_progress(self, status, progress):
        if self.progress_callback:
            self.progress_callback(status, progress)
        logger.info(f"[{progress*100:.0f}%] {status}")

    def clear_vram(self):
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

    def _find_peaks(self, heatmap, min_score, min_distance_sec):
        peaks = []
        if not heatmap: return peaks
        scores = np.array([h["score"] for h in heatmap])
        times = np.array([h["timestamp"] for h in heatmap])
        for i in range(1, len(scores) - 1):
            if scores[i] >= scores[i-1] and scores[i] >= scores[i+1]:
                if scores[i] >= min_score:
                    peaks.append({"timestamp": times[i], "score": scores[i]})
        if not peaks:
            sorted_indices = np.argsort(scores)[::-1]
            for idx in sorted_indices:
                if scores[idx] >= min_score:
                    peaks.append({"timestamp": times[idx], "score": scores[idx]})
                if len(peaks) > 20: break
        peaks.sort(key=lambda x: x["score"], reverse=True)
        filtered_peaks = []
        for p in peaks:
            too_close = False
            for fp in filtered_peaks:
                if abs(p["timestamp"] - fp["timestamp"]) < min_distance_sec:
                    too_close = True; break
            if not too_close: filtered_peaks.append(p)
        return sorted(filtered_peaks, key=lambda x: x["timestamp"])

    def _merge_scenes(self, scenes, heatmap_data, merge_threshold):
        if len(scenes) < 2: return scenes
        def get_features(ts):
            closest = min(heatmap_data, key=lambda x: abs(x["timestamp"] - ts))
            return np.array(closest["features"])
        scenes.sort(key=lambda x: x["trimmed_start"])
        merged = []
        for curr in scenes:
            if not merged: merged.append(curr); continue
            prev = merged[-1]
            if curr["trimmed_start"] < prev["trimmed_end"]:
                f_prev, f_curr = get_features(prev["hero_timestamp"]), get_features(curr["hero_timestamp"])
                sim = np.dot(f_prev, f_curr) / (np.linalg.norm(f_prev) * np.linalg.norm(f_curr) + 1e-9)
                if sim > merge_threshold:
                    prev["trimmed_end"] = max(prev["trimmed_end"], curr["trimmed_end"])
                    prev["duration"] = round(prev["trimmed_end"] - prev["trimmed_start"], 2)
                    if curr["aesthetic_score"] > prev["aesthetic_score"]:
                        prev["aesthetic_score"] = curr["aesthetic_score"]; prev["hero_timestamp"] = curr["hero_timestamp"]
                else:
                    prev["trimmed_end"] = curr["trimmed_start"]
                    prev["duration"] = round(prev["trimmed_end"] - prev["trimmed_start"], 2)
                    if prev["duration"] >= 1.0: merged.append(curr)
                    else: merged[-1] = curr
            else: merged.append(curr)
        for idx, scene in enumerate(merged): scene["id"] = idx + 1
        return merged

    def run(self, video_path, gui_params=None, project_dir=None):
        cfg = {
            "MIN_HERO_SCORE": gui_params.get("min_hero_score", 4.5),
            "MIN_PEAK_DISTANCE_SEC": gui_params.get("min_peak_distance", 5.0),
            "SEMANTIC_MERGE_THRESHOLD": gui_params.get("merge_threshold", 0.88),
            "EXPANSION_BUFFER_SEC": gui_params.get("expansion_buffer", 4.0),
            "MIN_SCENE_DURATION": gui_params.get("min_scene_duration", 2.0),
            "EXP_SEMANTIC_MAX": gui_params.get("exp_semantic_max", 0.85),
            "EXP_SEMANTIC_MIN": gui_params.get("exp_semantic_min", 0.75),
            "MAX_CHAOS_MAGNITUDE": gui_params.get("max_chaos", 12.0),
            "MAX_JITTER_THRESHOLD": gui_params.get("max_jitter", 3.0),
            "EXPORT_HIGH_RES": gui_params.get("export_high_res", True)
        }

        start_time = time.time()
        
        heatmap_cache = os.path.join(project_dir, "heatmap.json") if project_dir else None
        stability_cache = os.path.join(project_dir, "stability.json") if project_dir else None
        
        heatmap = None
        stability_map = None
        proxy_path = None

        # 🚀 1. SMART RESUME (Load Cache)
        if heatmap_cache and stability_cache and os.path.exists(heatmap_cache) and os.path.exists(stability_cache):
            self._update_progress("⚡ Caricamento Analisi AI & Stabilità...", 0.35)
            try:
                with open(heatmap_cache, "r") as f: heatmap = json.load(f)
                with open(stability_cache, "r") as f: stability_map = json.load(f)
                proxy_path = generate_proxy(video_path, output_dir=project_dir)
            except Exception: heatmap = None

        # 🎬 2. FULL ANALYSIS (If no cache)
        if heatmap is None or stability_map is None:
            self._update_progress("Compressione Video (Proxy)...", 0.05)
            proxy_path = generate_proxy(video_path, output_dir=project_dir)
            
            self._update_progress("Analisi Estetica AI...", 0.15)
            if self.evaluator is None: self.evaluator = SceneEvaluator()
            heatmap = self.evaluator.generate_heatmap(proxy_path)
            
            self._update_progress("Analisi Stabilità (Flow)...", 0.30)
            trimmer_tool = StabilityTrimmer(proxy_path)
            stability_map = trimmer_tool.analyze_stability()
            
            # Save Cache
            if project_dir:
                try:
                    with open(heatmap_cache, "w") as f:
                        json.dump([{"timestamp": h["timestamp"], "score": h["score"], "features": h["features"].tolist() if hasattr(h["features"], "tolist") else h["features"]} for h in heatmap], f)
                    with open(stability_cache, "w") as f: json.dump(stability_map, f)
                except Exception: pass
            self.clear_vram()

        # 🎯 3. RE-TUNING STAGE (Always re-runs, but instant)
        self._update_progress("Identificazione Hero Frames...", 0.45)
        hero_frames = self._find_peaks(heatmap, cfg["MIN_HERO_SCORE"], cfg["MIN_PEAK_DISTANCE_SEC"])
        if not hero_frames: return []

        self._update_progress(f"Espansione Dinamica ({len(hero_frames)} clip)...", 0.65)
        trimmer = StabilityTrimmer(proxy_path)
        trimmer.stability_map = stability_map # INJECT CACHE
        
        expanded_scenes = []
        all_discarded = []
        for i, hero in enumerate(hero_frames):
            feat = np.array(next(h["features"] for h in heatmap if h["timestamp"] == hero["timestamp"]))
            res = trimmer.bidirectional_expand(hero["timestamp"], feat, heatmap, buffer_sec=cfg["EXPANSION_BUFFER_SEC"], min_duration=cfg["MIN_SCENE_DURATION"], semantic_max=cfg["EXP_SEMANTIC_MAX"], semantic_min=cfg["EXP_SEMANTIC_MIN"], max_chaos=cfg["MAX_CHAOS_MAGNITUDE"], max_jitter=cfg["MAX_JITTER_THRESHOLD"])
            if res:
                res["id"] = i + 1; res["aesthetic_score"] = hero["score"]; res["hero_timestamp"] = hero["timestamp"]
                expanded_scenes.append(res)
            else:
                all_discarded.append(hero)
        
        self._update_progress("Merging Semantico...", 0.85)
        final_scenes = self._merge_scenes(expanded_scenes, heatmap, cfg["SEMANTIC_MERGE_THRESHOLD"])
        
        self._update_progress("Finalizzazione...", 0.95)
        project_timeline = self.director.serialize_project(final_scenes, video_path, proxy_path=proxy_path)
        
        if cfg["EXPORT_HIGH_RES"]:
            self._update_progress("Esportazione Alta Risoluzione...", 0.95)
            p_name = os.path.basename(project_dir) if project_dir else "DroneCut_Export"
            self.director.export_timeline(video_path, final_scenes, project_name=p_name)
            
        if default_config.DEBUG_MODE:
            self.director.save_debug_report(all_discarded, project_dir=project_dir)
            
        total_time = time.time() - start_time
        self._update_progress(f"✅ Pronto in {total_time:.1f}s!", 1.0)
        return project_timeline

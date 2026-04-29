import os
import logging
import time
import shutil
import torch
import gc
import cv2
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

    def clean_dirs(self):
        # Clean only transient data (Caches)
        for d in [default_config.DEBUG_DIR, default_config.PROXY_DIR]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d, exist_ok=True)

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
                    too_close = True
                    break
            if not too_close:
                filtered_peaks.append(p)
        return sorted(filtered_peaks, key=lambda x: x["timestamp"])

    def _merge_scenes(self, scenes, heatmap_data, merge_threshold):
        if len(scenes) < 2:
            return scenes
            
        def get_features(ts):
            closest_sample = min(heatmap_data, key=lambda x: abs(x["timestamp"] - ts))
            return closest_sample["features"]

        scenes.sort(key=lambda x: x["trimmed_start"])
        merged = []
        
        i = 0
        while i < len(scenes):
            curr = scenes[i]
            if not merged:
                merged.append(curr)
                i += 1
                continue
                
            prev = merged[-1]
            if curr["trimmed_start"] < prev["trimmed_end"]:
                feat_prev = get_features(prev["hero_timestamp"])
                feat_curr = get_features(curr["hero_timestamp"])
                similarity = np.dot(feat_prev, feat_curr) / (np.linalg.norm(feat_prev) * np.linalg.norm(feat_curr) + 1e-9)
                
                if similarity > merge_threshold:
                    prev["trimmed_end"] = max(prev["trimmed_end"], curr["trimmed_end"])
                    prev["duration"] = round(prev["trimmed_end"] - prev["trimmed_start"], 2)
                    if curr["aesthetic_score"] > prev["aesthetic_score"]:
                        prev["aesthetic_score"] = curr["aesthetic_score"]
                        prev["hero_timestamp"] = curr["hero_timestamp"]
                else:
                    prev["trimmed_end"] = curr["trimmed_start"]
                    prev["duration"] = round(prev["trimmed_end"] - prev["trimmed_start"], 2)
                    if prev["duration"] >= 1.0:
                        merged.append(curr)
                    else:
                        merged[-1] = curr
            else:
                merged.append(curr)
            i += 1
        for idx, scene in enumerate(merged): scene["id"] = idx + 1
        return merged

    def run(self, video_path, gui_params=None):
        # Resolve config
        cfg = {
            "MIN_HERO_SCORE": gui_params.get("min_hero_score", default_config.MIN_HERO_SCORE) if gui_params else default_config.MIN_HERO_SCORE,
            "MIN_PEAK_DISTANCE_SEC": gui_params.get("min_peak_distance", default_config.MIN_PEAK_DISTANCE_SEC) if gui_params else default_config.MIN_PEAK_DISTANCE_SEC,
            "SEMANTIC_MERGE_THRESHOLD": gui_params.get("merge_threshold", default_config.SEMANTIC_MERGE_THRESHOLD) if gui_params else default_config.SEMANTIC_MERGE_THRESHOLD,
            "EXPANSION_BUFFER_SEC": gui_params.get("expansion_buffer", default_config.EXPANSION_BUFFER_SEC) if gui_params else default_config.EXPANSION_BUFFER_SEC,
            "MIN_SCENE_DURATION": gui_params.get("min_scene_duration", default_config.MIN_SCENE_DURATION) if gui_params else default_config.MIN_SCENE_DURATION,
            "EXP_SEMANTIC_MAX": gui_params.get("exp_semantic_max", default_config.EXP_SEMANTIC_MAX) if gui_params else default_config.EXP_SEMANTIC_MAX,
            "EXP_SEMANTIC_MIN": gui_params.get("exp_semantic_min", default_config.EXP_SEMANTIC_MIN) if gui_params else default_config.EXP_SEMANTIC_MIN,
            "MAX_CHAOS_MAGNITUDE": gui_params.get("max_chaos", default_config.MAX_CHAOS_MAGNITUDE) if gui_params else default_config.MAX_CHAOS_MAGNITUDE,
            "MAX_JITTER_THRESHOLD": gui_params.get("max_jitter", default_config.MAX_JITTER_THRESHOLD) if gui_params else default_config.MAX_JITTER_THRESHOLD,
            "EXPORT_HIGH_RES": gui_params.get("export_high_res", True) if gui_params else True
        }

        start_time = time.time()
        self._update_progress("Initializing AI Core...", 0.05)
        self.clean_dirs()
        self.clear_vram()
        
        # 1. Aesthetic Heatmap
        self._update_progress("Stage 1/5: Generating Heatmap...", 0.20)
        proxy_path = generate_proxy(video_path)
        if self.evaluator is None: self.evaluator = SceneEvaluator()
        heatmap = self.evaluator.generate_heatmap(proxy_path, heatmap_fps=default_config.HEATMAP_FPS)
        self.clear_vram()
        
        # 2. Peak Detection
        self._update_progress("Stage 2/5: Identifying Hero Frames...", 0.40)
        hero_frames = self._find_peaks(heatmap, cfg["MIN_HERO_SCORE"], cfg["MIN_PEAK_DISTANCE_SEC"])
        
        if not hero_frames:
            logger.warning("No Hero Frames detected.")
            return []

        # 3. Expansion
        self._update_progress(f"Stage 3/5: Expanding {len(hero_frames)} Hero Frames...", 0.60)
        trimmer = StabilityTrimmer(proxy_path)
        
        expanded_scenes = []
        all_discarded = []
        
        for i, hero in enumerate(hero_frames):
            hero_features = next(h["features"] for h in heatmap if h["timestamp"] == hero["timestamp"])
            
            res = trimmer.bidirectional_expand(
                hero["timestamp"], 
                hero_features, 
                heatmap,
                buffer_sec=cfg["EXPANSION_BUFFER_SEC"],
                min_duration=cfg["MIN_SCENE_DURATION"],
                semantic_max=cfg["EXP_SEMANTIC_MAX"],
                semantic_min=cfg["EXP_SEMANTIC_MIN"],
                max_chaos=cfg["MAX_CHAOS_MAGNITUDE"],
                max_jitter=cfg["MAX_JITTER_THRESHOLD"]
            )
            
            if res:
                res["id"] = i + 1
                res["aesthetic_score"] = hero["score"]
                res["hero_timestamp"] = hero["timestamp"]
                expanded_scenes.append(res)
            else:
                all_discarded.append(hero)
        
        # 4. Semantic Merging
        self._update_progress("Stage 4/5: Semantic Merging...", 0.80)
        final_scenes = self._merge_scenes(expanded_scenes, heatmap, cfg["SEMANTIC_MERGE_THRESHOLD"])
        
        # 5. Final Serialization & Rendering
        self._update_progress("Stage 5/5: Final Serialization...", 0.90)
        project_timeline = self.director.serialize_project(final_scenes, video_path, proxy_path=proxy_path)
        
        if cfg["EXPORT_HIGH_RES"]:
            self._update_progress("Exporting High-Res Clips...", 0.95)
            self.director.export_timeline(video_path, final_scenes)
            
        self.director.save_debug_report(all_discarded)
        
        total_time = time.time() - start_time
        self._update_progress(f"✅ V5.2 Complete in {total_time:.1f}s!", 1.0)
        return project_timeline

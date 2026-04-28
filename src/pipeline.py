import os
import logging
import time
import shutil
import torch
import gc
import cv2
from PIL import Image
from .proxy import generate_proxy
from .semantic import SemanticAnalyzer
from .trimmer import StabilityTrimmer
from .evaluator import SceneEvaluator
from .director import Director
from .config import OUTPUT_DIR, DEBUG_DIR, DEBUG_MODE, MIN_SCENE_DURATION

logger = logging.getLogger("DroneCutPipeline")

class DroneCutPipeline:
    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback
        self.director = Director()
        self.evaluator = None # Lazy load
        
    def _update_progress(self, status, progress):
        if self.progress_callback:
            self.progress_callback(status, progress)
        logger.info(f"[{progress*100:.0f}%] {status}")

    def clean_dirs(self):
        for d in [OUTPUT_DIR, DEBUG_DIR]:
            if os.path.exists(d):
                shutil.rmtree(d)
            os.makedirs(d, exist_ok=True)

    def clear_vram(self):
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

    def run(self, video_path, theme_prompt=None):
        start_time = time.time()
        self._update_progress("Initializing...", 0.05)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Input not found: {video_path}")

        self.clean_dirs()
        self.clear_vram()
        
        all_discarded = []

        # 1. Proxy
        self._update_progress("Stage 1/7: Proxy Generation...", 0.1)
        proxy_path = generate_proxy(video_path)
        
        # 2. Semantic Mapping
        self._update_progress("Stage 2/7: Semantic Mapping...", 0.2)
        analyzer = SemanticAnalyzer(batch_size=32)
        raw_scenes = analyzer.detect_scenes(proxy_path)
        del analyzer
        self.clear_vram()
        
        # 3. Early Clustering & Filter
        self._update_progress("Stage 3/7: Semantic Audit...", 0.35)
        semantic_survivors, semantic_discarded = self.director.cluster_and_filter_v3(raw_scenes)
        
        if DEBUG_MODE:
            self.director.visualize_clusters(raw_scenes, os.path.join(DEBUG_DIR, "clustering_map.png"))
            self.director.export_debug_frames(video_path, semantic_discarded, os.path.join(DEBUG_DIR, "discarded_semantic"))
        
        all_discarded.extend(semantic_discarded)

        filtered_survivors = []
        for s in semantic_survivors:
            if (s["end_sec"] - s["start_sec"]) >= MIN_SCENE_DURATION:
                filtered_survivors.append(s)
            else:
                s["discard_reason"] = "Too_Short_Initial"
                all_discarded.append(s)

        if not filtered_survivors:
            logger.warning("No scenes survived semantic audit.")
            self.director.save_debug_report(all_discarded)
            return []

        # 4. Targeted Trimming
        self._update_progress("Stage 4/7: Stability Audit...", 0.5)
        trimmer = StabilityTrimmer(video_path)
        trimmed_survivors, stability_discarded = trimmer.process_scenes(filtered_survivors)
        
        final_survivors = []
        for s in trimmed_survivors:
            if (s["trimmed_end"] - s["trimmed_start"]) >= MIN_SCENE_DURATION:
                final_survivors.append(s)
            else:
                s["discard_reason"] = "Too_Short_After_Trim"
                stability_discarded.append(s)

        if DEBUG_MODE:
            self.director.export_debug_frames(video_path, stability_discarded, os.path.join(DEBUG_DIR, "discarded_stability"))
        
        all_discarded.extend(stability_discarded)

        if not final_survivors:
            logger.warning("No scenes survived stability audit.")
            self.director.save_debug_report(all_discarded)
            return []

        # 5. Aesthetic Scoring
        self._update_progress("Stage 5/7: Aesthetic Scoring...", 0.65)
        if self.evaluator is None:
            self.evaluator = SceneEvaluator()
        scored_scenes = self.evaluator.process_scenes_optimized(video_path, final_survivors)
        self.clear_vram()
        
        # 6. Creative Selection & VLM Director
        self._update_progress("Stage 6/7: VLM Creative Selection...", 0.8)
        selected_timeline, vlm_discarded = self.director.run_creative_selection(scored_scenes, self.evaluator, theme_prompt)
        
        if DEBUG_MODE:
            logger.info("Saving VLM discarded frames...")
            self.director.export_debug_frames(video_path, vlm_discarded, os.path.join(DEBUG_DIR, "discarded_vlm"))
        
        all_discarded.extend(vlm_discarded)
        self.director.save_debug_report(all_discarded)
        
        self.clear_vram()
        
        if not selected_timeline:
            return []

        # 7. Final Render & Thumbnail Generation
        self._update_progress("Stage 7/7: Final Timeline Render...", 0.95)
        self.director.export_timeline(video_path, selected_timeline)
        self.director.save_manifest(selected_timeline)
        
        # Generate thumbnails for GUI
        results = []
        thumb_dir = os.path.join(OUTPUT_DIR, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        for i, scene in enumerate(selected_timeline):
            mid_sec = (scene["trimmed_start"] + scene["trimmed_end"]) / 2
            cap.set(cv2.CAP_PROP_POS_MSEC, mid_sec * 1000)
            ret, frame = cap.read()
            if ret:
                thumb_name = f"thumb_{i:03d}.jpg"
                thumb_path = os.path.join(thumb_dir, thumb_name)
                cv2.imwrite(thumb_path, frame)
                
                results.append({
                    "thumbnail_path": thumb_path,
                    "caption": scene.get("caption", "No caption"),
                    "start": scene["trimmed_start"],
                    "end": scene["trimmed_end"]
                })
        cap.release()
        
        total_time = time.time() - start_time
        self._update_progress(f"✅ Complete in {total_time:.1f}s!", 1.0)
        
        return results

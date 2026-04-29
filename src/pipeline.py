import os
import logging
import time
import shutil
import torch
import gc
import cv2
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
        """
        DroneCut Pipeline v4: The Chronological Scalpel
        """
        start_time = time.time()
        self._update_progress("Initializing...", 0.05)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Input not found: {video_path}")

        self.clean_dirs()
        self.clear_vram()
        
        all_discarded = []

        # 1. Chronological Scene Detection (CLIP)
        self._update_progress("Stage 1/4: Chronological Scene Detection...", 0.15)
        proxy_path = generate_proxy(video_path)
        analyzer = SemanticAnalyzer(batch_size=32)
        raw_chapters = analyzer.detect_scenes(proxy_path)
        del analyzer
        self.clear_vram()
        
        if not raw_chapters:
            logger.warning("No scenes detected in Stage 1.")
            return []

        # 2. Surgical Stability Trimming (OpenCV)
        self._update_progress("Stage 2/4: Surgical Stability Trimming...", 0.40)
        trimmer = StabilityTrimmer(video_path)
        final_stability_survivors, stability_discarded = trimmer.process_scenes(raw_chapters)
        
        if DEBUG_MODE:
            self.director.export_debug_frames(video_path, stability_discarded, os.path.join(DEBUG_DIR, "discarded_stability"))
        
        all_discarded.extend(stability_discarded)

        if not final_stability_survivors:
            logger.warning("No scenes survived stability audit.")
            self.director.save_debug_report(all_discarded)
            return []

        # 3. Aesthetic Scoring (CLIP-Aesthetic)
        self._update_progress("Stage 3/4: Aesthetic Scoring...", 0.70)
        if self.evaluator is None:
            self.evaluator = SceneEvaluator()
        
        scored_scenes = self.evaluator.process_scenes_optimized(video_path, final_stability_survivors)
        self.clear_vram()
        
        # 4. Final Serialization (ProjectState)
        self._update_progress("Stage 4/4: Final Serialization...", 0.90)
        project_timeline = self.director.serialize_project(scored_scenes, video_path)
        
        # Optional: Final Render
        self.director.export_timeline(video_path, scored_scenes)
        self.director.save_debug_report(all_discarded)
        
        total_time = time.time() - start_time
        self._update_progress(f"✅ Complete in {total_time:.1f}s!", 1.0)
        
        return project_timeline

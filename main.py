import os
import sys
import logging
import time
import shutil
import torch
import gc
from src.proxy import generate_proxy
from src.semantic import SemanticAnalyzer
from src.trimmer import StabilityTrimmer
from src.evaluator import SceneEvaluator
from src.director import Director
from src.config import OUTPUT_DIR, DEBUG_DIR, DEBUG_MODE, MIN_SCENE_DURATION

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("DroneAutoCutter")

def clean_dirs():
    for d in [OUTPUT_DIR, DEBUG_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

def clear_vram():
    gc.collect()
    if torch.backends.mps.is_available():
        torch.mps.empty_cache()

def run_pipeline(video_path, theme_prompt=None):
    start_time = time.time()
    logger.info(f"🚀 DroneCut V3: THE SEMANTIC ARCHITECT")
    if theme_prompt:
        logger.info(f"🎬 Theme: '{theme_prompt}'")
    
    if not os.path.exists(video_path):
        logger.error(f"Input not found: {video_path}")
        return

    clean_dirs()

    try:
        # 1. Proxy
        logger.info("--- Stage 1: Proxy Generation ---")
        proxy_path = generate_proxy(video_path)
        
        # 2. Semantic Mapping
        logger.info("--- Stage 2: Semantic Mapping ---")
        analyzer = SemanticAnalyzer(batch_size=32)
        raw_scenes = analyzer.detect_scenes(proxy_path)
        del analyzer
        clear_vram()
        
        # 3. Early Clustering & Filter
        logger.info("--- Stage 3: Semantic Audit (DBSCAN) ---")
        director = Director()
        semantic_survivors, semantic_discarded = director.cluster_and_filter_v3(raw_scenes)
        
        if DEBUG_MODE:
            logger.info("Generating clustering map...")
            director.visualize_clusters(raw_scenes, os.path.join(DEBUG_DIR, "clustering_map.png"))
            director.export_debug_frames(video_path, semantic_discarded, os.path.join(DEBUG_DIR, "discarded_semantic"))

        # Filter by duration
        filtered_survivors = []
        for s in semantic_survivors:
            if (s["end_sec"] - s["start_sec"]) >= MIN_SCENE_DURATION:
                filtered_survivors.append(s)
            else:
                s["discard_reason"] = "Too_Short_Initial"
                semantic_discarded.append(s)

        if not filtered_survivors:
            logger.warning("No scenes survived semantic audit.")
            return

        # 4. Targeted Trimming
        logger.info("--- Stage 4: Stability Audit (Surgical OpenCV) ---")
        trimmer = StabilityTrimmer(video_path)
        trimmed_survivors, stability_discarded = trimmer.process_scenes(filtered_survivors)
        
        # Enforce MIN_SCENE_DURATION AFTER trimming
        final_survivors = []
        for s in trimmed_survivors:
            if (s["trimmed_end"] - s["trimmed_start"]) >= MIN_SCENE_DURATION:
                final_survivors.append(s)
            else:
                s["discard_reason"] = "Too_Short_After_Trim"
                stability_discarded.append(s)

        if DEBUG_MODE:
            director.export_debug_frames(video_path, stability_discarded, os.path.join(DEBUG_DIR, "discarded_stability"))

        if not final_survivors:
            logger.warning("No scenes survived stability audit.")
            return

        # 5. Aesthetic Scoring
        logger.info("--- Stage 5: Aesthetic Scoring ---")
        evaluator = SceneEvaluator()
        scored_scenes = evaluator.process_scenes_optimized(video_path, final_survivors)
        clear_vram()
        
        # 6. Creative Selection & VLM Director
        logger.info("--- Stage 6: VLM Creative Selection ---")
        selected_timeline, vlm_discarded = director.run_creative_selection(scored_scenes, evaluator, theme_prompt)
        
        if DEBUG_MODE:
            logger.info("Saving VLM discarded frames...")
            director.export_debug_frames(video_path, vlm_discarded, os.path.join(DEBUG_DIR, "discarded_vlm"))
        
        clear_vram()
        
        if not selected_timeline:
            logger.warning("No scenes approved by the VLM Director.")
            return

        # 7. Final Render
        logger.info(f"--- Stage 7: Final Timeline Render ({len(selected_timeline)} shots) ---")
        director.export_timeline(video_path, selected_timeline)
        director.save_manifest(selected_timeline)
        
        total_time = time.time() - start_time
        logger.info(f"✅ V3 Complete in {total_time:.1f}s! Timeline ready in data/output/timeline")

    except Exception as e:
        logger.exception(f"❌ Pipeline failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <path_to_video> [theme_prompt]")
    else:
        path = sys.argv[1]
        theme = sys.argv[2] if len(sys.argv) > 2 else None
        run_pipeline(path, theme)

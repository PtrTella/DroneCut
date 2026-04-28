import os
import logging
import tempfile
import json
from tqdm import tqdm
from .video import create_proxy, extract_clip, concatenate_clips, add_background_music
from .scenes import detect_scenes
from ..analysis.manager import AnalysisManager

logger = logging.getLogger(__name__)

class DroneCutPipeline:
    def __init__(self, prompts=None, negative_prompts=None, min_scene_duration=1.5, max_scenes=30, speed=1.5, max_duration=None, threshold=20.0, music_path=None):
        self.prompts = prompts
        self.negative_prompts = negative_prompts
        self.min_scene_duration = min_scene_duration
        self.max_scenes = max_scenes
        self.speed = speed
        self.max_duration = max_duration
        self.threshold = threshold
        self.music_path = music_path
        self.analysis_manager = AnalysisManager()

    def analyze(self, video_paths, out_dir="dronecut_output", pos_prompts=None, neg_prompts=None, music_path=None, skip_export=False):
        """
        Main entry point for the pipeline.
        """
        if isinstance(video_paths, str):
            video_paths = [video_paths]
            
        os.makedirs(out_dir, exist_ok=True)
        all_selected_scenes = []
        
        for video_index, video_path in enumerate(video_paths):
            logger.info(f"--- Processing Video: {os.path.basename(video_path)} ---")
            
            # 1. Detection
            scenes = self._stage_detection(video_path)
            
            # 2. Fast Scoring
            scored_scenes = self._stage_fast_scoring(video_path, scenes, pos_prompts, neg_prompts)
            
            # 3. VLM Funnel (Deep analysis of top candidates)
            refined_scenes = self._stage_vlm_funnel(video_path, scored_scenes)
            
            # 4. Scene Extraction
            final_scenes = self._stage_extraction(video_path, refined_scenes, out_dir, video_index)
            all_selected_scenes.extend(final_scenes)

        # 5. Final Export (Optional Montage)
        if not skip_export and all_selected_scenes:
            self._stage_export_montage(all_selected_scenes, out_dir, music_path)
            
        logger.info(f"Processing complete. Results in {out_dir}")
        return all_selected_scenes

    def _stage_detection(self, video_path):
        """
        Creates a proxy and detects scenes using PySceneDetect.
        Uses a persistent cache to avoid re-compressing the same video.
        """
        cache_dir = ".dronecut_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        proxy_path = os.path.join(cache_dir, f"proxy_{os.path.basename(video_path)}")
        
        if os.path.exists(proxy_path):
            logger.info(f"Using cached proxy: {proxy_path}")
        else:
            logger.info(f"Creating proxy for {video_path}...")
            create_proxy(video_path, proxy_path)
            
        logger.info(f"Detecting scenes...")
        scene_list = detect_scenes(proxy_path, threshold=self.threshold)
            
        valid_scenes = []
        for start, end in scene_list:
            if (end - start) >= self.min_scene_duration:
                valid_scenes.append({
                    "start": start,
                    "end": end,
                    "source": video_path
                })
        
        logger.info(f"Found {len(valid_scenes)} valid scenes (>{self.min_scene_duration}s)")
        return valid_scenes

    def _stage_fast_scoring(self, video_path, scenes, pos_prompts=None, neg_prompts=None):
        """
        Calculates Semantic (CLIP) and Aesthetic scores on a single high-quality keyframe.
        """
        logger.info(f"Scoring {len(scenes)} scenes...")
        scored_scenes = []
        
        for scene in tqdm(scenes, desc="Fast Scoring"):
            mid_time = (scene["start"] + scene["end"]) / 2
            
            # Extract keyframe from original video for best analysis
            image = self.analysis_manager.get_frame(video_path, mid_time)
            if image is None: continue
            
            # Semantic & Aesthetic Analysis
            sem_score, aes_score, _, _ = self.analysis_manager.analyze_scene(
                image, pos_prompts or self.prompts, neg_prompts or self.negative_prompts, run_vlm=False
            )
            
            # Weighted initial score
            if self.prompts:
                initial_score = (sem_score * 0.6) + (aes_score * 0.4)
            else:
                initial_score = aes_score # Purely aesthetic if no prompts
                
            scene.update({
                "semantic_score": sem_score,
                "aesthetic_score": aes_score,
                "initial_score": initial_score,
                "image": image # Cache image for VLM stage
            })
            scored_scenes.append(scene)
            
        # Sort by initial score for the funnel
        scored_scenes.sort(key=lambda x: x["initial_score"], reverse=True)
        return scored_scenes

    def _stage_vlm_funnel(self, video_path, scenes):
        """
        Runs the expensive VLM on the top subset of scenes.
        """
        # Funnel: Top 30%, max 15 scenes
        funnel_limit = min(len(scenes), max(5, int(len(scenes) * 0.3)))
        if funnel_limit > 15: funnel_limit = 15
        
        logger.info(f"Funneling top {funnel_limit} scenes to Cinematic VLM...")
        
        for i in range(len(scenes)):
            scene = scenes[i]
            if i < funnel_limit:
                # Top tier: Run Moondream2
                _, _, cin_score, _ = self.analysis_manager.analyze_scene(
                    scene["image"], [], [], run_vlm=True
                )
                scene["cinematic_score"] = cin_score
            else:
                scene["cinematic_score"] = 0.0
            
            # Final Weighted Score: 40% Semantics, 30% Aesthetics, 30% Cinematic VLM
            scene["total_score"] = (scene["semantic_score"] * 0.4) + \
                                  (scene["aesthetic_score"] * 0.3) + \
                                  (scene["cinematic_score"] * 0.3)
            
            # Clean up memory
            if "image" in scene: del scene["image"]
            
        return scenes

    def _stage_extraction(self, video_path, scenes, out_dir, video_index):
        """
        Generates final preview MP4s and assembles the metadata.
        """
        scenes.sort(key=lambda x: x["total_score"], reverse=True)
        final_count = min(len(scenes), self.max_scenes)
        
        final_results = []
        for i in range(final_count):
            scene = scenes[i]
            scene_id = f"v{video_index}_s{i}"
            preview_filename = f"scene_{scene_id}.mp4"
            preview_path = os.path.join(out_dir, preview_filename)
            
            extract_clip(video_path, preview_path, scene["start"], scene["end"], speed=self.speed)
            
            final_results.append({
                "scene_id": scene_id,
                "source_video": os.path.basename(video_path),
                "source_path": video_path, # Keep full path for export
                "start": scene["start"],
                "end": scene["end"],
                "duration": scene["end"] - scene["start"],
                "preview_path": preview_filename,
                "semantic_score": round(scene["semantic_score"], 2),
                "aesthetic_score": round(scene["aesthetic_score"], 2),
                "cinematic_score": round(scene["cinematic_score"], 2),
                "total_score": round(scene["total_score"], 2),
                "metadata": {
                    "vlm_analyzed": i < 15,
                    "rank": i + 1
                }
            })
            
        return final_results

    def _stage_export_montage(self, scenes, out_dir, music_path):
        """Stage 5: Create the final edited video (optionally synced to music)."""
        output_path = os.path.join(out_dir, "final_montage.mp4")
        logger.info(f"Creating final montage: {output_path}")
        from .video import export_final_video
        export_final_video(scenes, output_path, music_path=music_path)

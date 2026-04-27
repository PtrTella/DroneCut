import os
import logging
import tempfile
from .video import create_proxy, extract_clip, concatenate_clips, add_background_music
from .scenes import detect_scenes
from ..analysis.visual import analyze_scene_visuals
from ..analysis.semantics import SemanticAnalyzer
from ..analysis.audio import get_beat_timestamps

logger = logging.getLogger(__name__)

import numpy as np

class DroneCutPipeline:
    def __init__(self, prompts=None, negative_prompts=None, min_scene_duration=1.5, max_scenes=30, speed=1.5, max_duration=None, threshold=20.0, music_path=None):
        self.prompts = prompts or ["cinematic drone photography", "spectacular landscape", "epic mountain view", "breathtaking nature", "scenographic shot"]
        self.negative_prompts = negative_prompts or ["blur", "shaky", "bad quality", "low resolution", "distorted"]
        self.min_scene_duration = min_scene_duration
        self.max_scenes = max_scenes
        self.speed = speed # This is the base speed
        self.max_duration = max_duration
        self.threshold = threshold
        self.music_path = music_path
        self.semantic_analyzer = SemanticAnalyzer()

    def cosine_similarity(self, a, b):
        if a is None or b is None:
            return 0.0
        a = a.flatten()
        b = b.flatten()
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def analyze(self, input_videos, out_dir, save_session=False):
        """
        Phase 1: Analyzes videos, detects scenes, and generates low-res proxies for preview.
        Returns a list of scene metadata objects.
        """
        os.makedirs(out_dir, exist_ok=True)
        proxies_dir = os.path.join(out_dir, "previews")
        os.makedirs(proxies_dir, exist_ok=True)
        
        all_potential_scenes = []
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, video_path in enumerate(input_videos):
                logger.info(f"Analyzing: {video_path}")
                proxy_path = os.path.join(tmp_dir, f"proxy_{i}.mp4")
                create_proxy(video_path, proxy_path)
                
                scenes = detect_scenes(proxy_path, threshold=self.threshold)
                
                for start, end in scenes:
                    duration = end - start
                    if duration < self.min_scene_duration:
                        continue
                        
                    visual_metrics = analyze_scene_visuals(proxy_path, start, end)
                    if not visual_metrics: continue
                    
                    if visual_metrics["max_jerk"] > 12.0: continue

                    semantic_score, embedding = self.semantic_analyzer.score_scene(proxy_path, start, end, self.prompts, self.negative_prompts)
                    total_score = (semantic_score * 50) + (min(visual_metrics["avg_contrast"], 50) / 25.0)
                    
                    multiplier = max(1.0, 1.0 + (40 - visual_metrics["avg_motion"]) / 8.0)
                    adaptive_speed = min(5.0, self.speed * multiplier)

                    # Generate a unique proxy for this specific scene
                    scene_id = len(all_potential_scenes)
                    scene_proxy_name = f"scene_{scene_id:04d}_preview.mp4"
                    scene_proxy_path = os.path.join(proxies_dir, scene_proxy_name)
                    
                    # Extract a very low-res fast proxy for the web UI
                    # (we use original video for preview)
                    extract_clip(video_path, scene_proxy_path, start, end, speed=adaptive_speed)

                    all_potential_scenes.append({
                        "id": scene_id,
                        "input": video_path,
                        "start": start,
                        "end": end,
                        "score": float(total_score),
                        "clip_score": float(semantic_score),
                        "embedding": embedding,
                        "duration": duration,
                        "adaptive_speed": adaptive_speed,
                        "preview_url": scene_proxy_path
                    })

        # Sort by start time for chronological presentation
        all_potential_scenes.sort(key=lambda x: (x["input"], x["start"]))
        
        # Save metadata for session recovery (GUI only)
        if save_session:
            import json
            metadata_path = os.path.join(out_dir, "metadata.json")
            with open(metadata_path, "w") as f:
                serializable_scenes = []
                for s in all_potential_scenes:
                    s_copy = s.copy()
                    if "embedding" in s_copy: del s_copy["embedding"]
                    serializable_scenes.append(s_copy)
                json.dump(serializable_scenes, f)
            
        return all_potential_scenes

    def export(self, selected_scenes, out_dir):
        """
        Phase 2: Takes a list of scenes and produces the final high-quality video.
        """
        os.makedirs(out_dir, exist_ok=True)
        clips_dir = os.path.join(out_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        
        output_final_no_audio = os.path.join(out_dir, "final_no_audio.mp4")
        output_final = os.path.join(out_dir, "final.mp4")
        
        # Audio Beat Analysis
        beats = []
        if self.music_path:
            beats = get_beat_timestamps(self.music_path)
            beat_intervals = np.diff(beats).tolist()
        
        clip_files = []
        for j, scene in enumerate(selected_scenes):
            clip_filename = f"clip_{j+1:03d}.mp4"
            clip_path = os.path.join(clips_dir, clip_filename)
            
            if beats and j < len(beat_intervals):
                target_duration = beat_intervals[j]
                source_extract_duration = target_duration * scene["adaptive_speed"]
                extract_end = scene["start"] + source_extract_duration
                if extract_end > scene["end"]: extract_end = scene["end"]
                
                logger.info(f"Syncing clip {j+1} to beat: {target_duration:.2f}s")
                extract_clip(scene["input"], clip_path, scene["start"], extract_end, speed=scene["adaptive_speed"])
            else:
                logger.info(f"Extracting clip {j+1}: {scene['start']:.1f}-{scene['end']:.1f}")
                extract_clip(scene["input"], clip_path, scene["start"], scene["end"], speed=scene["adaptive_speed"])
            
            clip_files.append(clip_path)
            
        if clip_files:
            concatenate_clips(clip_files, output_final_no_audio)
            if self.music_path:
                add_background_music(output_final_no_audio, self.music_path, output_final)
                os.remove(output_final_no_audio)
            else:
                os.rename(output_final_no_audio, output_final)
            return output_final
        return None

    def run(self, input_videos, out_dir):
        """Standard CLI entry point"""
        # Analysis
        all_scenes = self.analyze(input_videos, out_dir)
        
        # Automatic selection (same logic as before)
        selected_scenes = []
        total_selected_duration = 0
        
        # We need a beat count if music is present
        target_count = self.max_scenes
        if self.music_path:
            # We don't want to re-analyze music here, but run() is for CLI.
            # For CLI we just use the simple logic.
            pass

        for scene in all_scenes:
            is_repetitive = False
            for selected in selected_scenes:
                similarity = self.cosine_similarity(scene["embedding"], selected["embedding"])
                if similarity > 0.94: 
                    is_repetitive = True
                    break
            if is_repetitive: continue
            
            selected_scenes.append(scene)
            if not self.music_path:
                total_selected_duration += scene["duration"] / scene["adaptive_speed"]
                if self.max_duration and total_selected_duration > self.max_duration:
                    break
            if len(selected_scenes) >= target_count:
                break
        
        selected_scenes.sort(key=lambda x: (x["input"], x["start"]))
        self.export(selected_scenes, out_dir)
        logger.info(f"Processing complete. Results in: {out_dir}")

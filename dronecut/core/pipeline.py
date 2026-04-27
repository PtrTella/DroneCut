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
    def __init__(self, prompts=None, min_scene_duration=1.5, max_scenes=30, speed=1.5, max_duration=None, threshold=20.0, music_path=None):
        self.prompts = prompts or ["cinematic drone photography", "spectacular landscape", "epic mountain view", "breathtaking nature", "scenographic shot"]
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

    def run(self, input_videos, out_dir):
        os.makedirs(out_dir, exist_ok=True)
        clips_dir = os.path.join(out_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)
        
        output_final_no_audio = os.path.join(out_dir, "final_no_audio.mp4")
        output_final = os.path.join(out_dir, "final.mp4")
        
        # 1. Audio Beat Analysis if music provided
        beats = []
        if self.music_path:
            beats = get_beat_timestamps(self.music_path)
            # We want intervals between beats
            beat_intervals = np.diff(beats).tolist()
            logger.info(f"Using {len(beat_intervals)} beat intervals for music sync.")
        
        all_potential_scenes = []
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, video_path in enumerate(input_videos):
                logger.info(f"Processing video {i+1}/{len(input_videos)}: {video_path}")
                
                proxy_path = os.path.join(tmp_dir, f"proxy_{i}.mp4")
                create_proxy(video_path, proxy_path)
                
                scenes = detect_scenes(proxy_path, threshold=self.threshold)
                logger.info(f"Detected {len(scenes)} potential scenes.")
                
                for start, end in scenes:
                    duration = end - start
                    if duration < self.min_scene_duration:
                        continue
                        
                    visual_metrics = analyze_scene_visuals(proxy_path, start, end)
                    if not visual_metrics:
                        continue
                    
                    avg_motion = visual_metrics["avg_motion"]
                    max_jerk = visual_metrics["max_jerk"]
                    
                    if max_jerk > 12.0: 
                        logger.info(f"Discarding jerky scene: {start:.1f}-{end:.1f} (jerk {max_jerk:.2f})")
                        continue

                    semantic_score, embedding = self.semantic_analyzer.score_scene(proxy_path, start, end, self.prompts)
                    total_score = (semantic_score * 50) + (min(visual_metrics["avg_contrast"], 50) / 25.0)
                    
                    # ENHANCED Adaptive Speedup:
                    # Drone motion values are often 30-50. 
                    # If motion is < 40, we start accelerating.
                    # Max total speed capped at 5x.
                    multiplier = max(1.0, 1.0 + (40 - avg_motion) / 8.0)
                    adaptive_speed = min(5.0, self.speed * multiplier)

                    logger.info(f"Scene {start:.1f}-{end:.1f} | Score: {total_score:.2f} | CLIP: {semantic_score:.4f} | Motion: {avg_motion:.2f} | Speed: {adaptive_speed:.1f}x")

                    all_potential_scenes.append({
                        "input": video_path,
                        "start": start,
                        "end": end,
                        "score": total_score,
                        "embedding": embedding,
                        "duration": duration,
                        "adaptive_speed": adaptive_speed
                    })

            # Sort by score
            all_potential_scenes.sort(key=lambda x: x["score"], reverse=True)
            
            selected_scenes = []
            total_selected_duration = 0
            
            # Decide how many scenes we need
            target_scene_count = self.max_scenes
            if beats:
                target_scene_count = len(beat_intervals)
                logger.info(f"Targeting {target_scene_count} scenes for music sync.")

            for scene in all_potential_scenes:
                # DIVERSITY
                is_repetitive = False
                for selected in selected_scenes:
                    similarity = self.cosine_similarity(scene["embedding"], selected["embedding"])
                    if similarity > 0.94: 
                        is_repetitive = True
                        break
                
                if is_repetitive:
                    logger.info(f"Discarding repetitive scene: {scene['start']:.1f}-{scene['end']:.1f}")
                    continue
                
                selected_scenes.append(scene)
                
                # Check duration limit if no music
                if not beats:
                    scene_final_duration = scene["duration"] / scene["adaptive_speed"]
                    total_selected_duration += scene_final_duration
                    if self.max_duration and total_selected_duration > self.max_duration:
                        break

                if len(selected_scenes) >= target_scene_count:
                    break

            # Sort for flow
            selected_scenes.sort(key=lambda x: (x["input"], x["start"]))

            # Extract and save
            clip_files = []
            for j, scene in enumerate(selected_scenes):
                clip_filename = f"clip_{j+1:03d}.mp4"
                clip_path = os.path.join(clips_dir, clip_filename)
                
                # If music sync is ON, the final duration must match the beat interval
                if beats and j < len(beat_intervals):
                    target_duration = beat_intervals[j]
                    # The source duration we extract is target_duration * speed
                    source_extract_duration = target_duration * scene["adaptive_speed"]
                    
                    # Adjust extraction end time to match the required duration
                    extract_end = scene["start"] + source_extract_duration
                    if extract_end > scene["end"]:
                        # If scene is too short for the beat, we might need to slow it down 
                        # or just take what we have. For now, let's just cap it.
                        extract_end = scene["end"]
                    
                    logger.info(f"Syncing clip {j+1} to beat: {target_duration:.2f}s (Speed {scene['adaptive_speed']:.1f}x)")
                    extract_clip(scene["input"], clip_path, scene["start"], extract_end, speed=scene["adaptive_speed"])
                else:
                    logger.info(f"Extracting clip {j+1}: {scene['start']:.1f}-{scene['end']:.1f} (Speed {scene['adaptive_speed']:.1f}x)")
                    extract_clip(scene["input"], clip_path, scene["start"], scene["end"], speed=scene["adaptive_speed"])
                
                clip_files.append(clip_path)
                
            if clip_files:
                concatenate_clips(clip_files, output_final_no_audio)
                
                if self.music_path:
                    logger.info("Merging music...")
                    add_background_music(output_final_no_audio, self.music_path, output_final)
                    os.remove(output_final_no_audio)
                else:
                    os.rename(output_final_no_audio, output_final)
                    
                logger.info(f"Processing complete. Results in: {out_dir}")
            else:
                logger.warning("No scenes selected!")

import cv2
import numpy as np
import logging
from .config import MIN_SCENE_DURATION, MAX_CHAOS_MAGNITUDE, MAX_JITTER_THRESHOLD

logger = logging.getLogger(__name__)

class StabilityTrimmer:
    def __init__(self, original_video_path):
        self.video_path = original_video_path
        cap = cv2.VideoCapture(original_video_path)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.total_duration = self.total_frames / self.fps if self.fps > 0 else 0
        cap.release()

    def process_scenes(self, scenes):
        """
        Stage 2: Surgical Sliding Window Audit
        Analyzes the ENTIRE duration of each scene to find the longest stable "Golden Window".
        High performance is maintained via 240p downsampling.
        """
        trimmed_scenes = []
        discarded_scenes = []
        
        cap = cv2.VideoCapture(self.video_path)
        logger.info(f"Surgical Stability Audit (Full Scan) for {len(scenes)} scenes...")
        
        for scene in scenes:
            start = scene["start_sec"]
            end = scene["end_sec"]
            
            # 1. Full Scan Optical Flow
            cap.set(cv2.CAP_PROP_POS_MSEC, start * 1000)
            
            prev_gray = None
            frame_scores = [] # (peak, jitter) for each frame pair
            
            num_frames = int((end - start) * self.fps)
            
            for _ in range(num_frames):
                ret, frame = cap.read()
                if not ret: break
                
                # Performance Hack: 240p internal resize
                frame = cv2.resize(frame, (240, 135))
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if prev_gray is not None:
                    # Calculate flow
                    flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 10, 3, 5, 1.2, 0)
                    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    
                    # Store stability metrics for this specific frame transition
                    frame_scores.append({
                        "peak": np.percentile(mag, 90),
                        "jitter": np.std(mag)
                    })
                prev_gray = gray
            
            if not frame_scores:
                scene["discard_reason"] = "Flow_Extraction_Error"
                discarded_scenes.append(scene)
                continue
            
            # 2. Sliding Window: Find Longest Stable Segment
            # Create a boolean mask of stable frame transitions
            is_stable = [
                (s["peak"] <= MAX_CHAOS_MAGNITUDE and s["jitter"] <= MAX_JITTER_THRESHOLD)
                for s in frame_scores
            ]
            
            # Find longest contiguous True sequence
            best_start_idx, best_len = self._find_longest_true_sequence(is_stable)
            stable_duration = best_len / self.fps
            
            # 3. Decision Gate
            if stable_duration < MIN_SCENE_DURATION:
                scene["discard_reason"] = f"Unstable_or_Too_Short_{stable_duration:.1f}s"
                discarded_scenes.append(scene)
            else:
                # SUCCESS: We found the Golden Window!
                trimmed_start = start + (best_start_idx / self.fps)
                trimmed_end = trimmed_start + stable_duration
                
                scene["trimmed_start"] = round(trimmed_start, 3)
                scene["trimmed_end"] = round(trimmed_end, 3)
                
                # Final score for the survivor segment
                segment_jitters = [frame_scores[i]["jitter"] for i in range(best_start_idx, best_start_idx + best_len)]
                scene["stability_score"] = round(np.mean(segment_jitters), 2)
                
                trimmed_scenes.append(scene)
                
        cap.release()
        return trimmed_scenes, discarded_scenes

    def _find_longest_true_sequence(self, bool_list):
        """
        Helper to find the start index and length of the longest contiguous True sequence.
        """
        max_len = 0
        max_start = 0
        curr_len = 0
        curr_start = 0
        
        for i, val in enumerate(bool_list):
            if val:
                if curr_len == 0:
                    curr_start = i
                curr_len += 1
                if curr_len > max_len:
                    max_len = curr_len
                    max_start = curr_start
            else:
                curr_len = 0
                
        return max_start, max_len

import cv2
import numpy as np
import logging
import os
from .config import MAX_CHAOS_MAGNITUDE, MAX_JITTER_THRESHOLD, EXPANSION_BUFFER_SEC, MIN_SCENE_DURATION, EXP_SEMANTIC_MIN, EXP_SEMANTIC_MAX

logger = logging.getLogger(__name__)

class StabilityTrimmer:
    def __init__(self, original_video_path):
        self.video_path = original_video_path
        cap = cv2.VideoCapture(original_video_path)
        self.fps = cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.total_duration = self.total_frames / self.fps if self.fps > 0 else 0
        cap.release()

    def bidirectional_expand(self, hero_timestamp, hero_features, heatmap_data, 
                             buffer_sec=EXPANSION_BUFFER_SEC, 
                             min_duration=MIN_SCENE_DURATION, 
                             semantic_max=EXP_SEMANTIC_MAX, 
                             semantic_min=EXP_SEMANTIC_MIN,
                             max_chaos=MAX_CHAOS_MAGNITUDE,
                             max_jitter=MAX_JITTER_THRESHOLD):
        """
        Stage 3: Smart Bidirectional Expansion with Parametric Dynamic Tolerance.
        Supports GUI overrides for ALL key parameters.
        """
        cap = cv2.VideoCapture(self.video_path)
        start_search = max(0, hero_timestamp - buffer_sec)
        end_search = min(self.total_duration, hero_timestamp + buffer_sec)
        
        cap.set(cv2.CAP_PROP_POS_MSEC, start_search * 1000)
        num_frames = int((end_search - start_search) * self.fps)
        
        frame_scores = []
        prev_gray = None
        
        for _ in range(num_frames):
            ret, frame = cap.read()
            if not ret: break
            frame = cv2.resize(frame, (240, 135))
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 10, 3, 5, 1.2, 0)
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                frame_scores.append({
                    "peak": np.percentile(mag, 90),
                    "jitter": np.std(mag)
                })
            prev_gray = gray
        cap.release()
        
        if not frame_scores: return None
            
        def get_semantic_sim(ts):
            closest_sample = min(heatmap_data, key=lambda x: abs(x["timestamp"] - ts))
            feat = closest_sample["features"]
            return np.dot(hero_features, feat) / (np.linalg.norm(hero_features) * np.linalg.norm(feat) + 1e-9)

        hero_idx = int((hero_timestamp - start_search) * self.fps) - 1
        hero_idx = max(0, min(len(frame_scores) - 1, hero_idx))
        
        # 4. Expand Forward (Right)
        final_end_idx = hero_idx
        for i in range(hero_idx, len(frame_scores)):
            s = frame_scores[i]
            ts = start_search + (i / self.fps)
            
            # Physical Check with dynamic params
            if s["peak"] > max_chaos or s["jitter"] > max_jitter:
                break
            
            # PARAMETRIC DYNAMIC TOLERANCE
            velocity_ratio = min(1.0, s["peak"] / max_chaos)
            dynamic_threshold = semantic_max - (velocity_ratio * (semantic_max - semantic_min))
            
            sim = get_semantic_sim(ts)
            if sim < dynamic_threshold:
                break
            final_end_idx = i
            
        # 5. Expand Backward (Left)
        final_start_idx = hero_idx
        for i in range(hero_idx, -1, -1):
            s = frame_scores[i]
            ts = start_search + (i / self.fps)
            
            if s["peak"] > max_chaos or s["jitter"] > max_jitter:
                break
                
            velocity_ratio = min(1.0, s["peak"] / max_chaos)
            dynamic_threshold = semantic_max - (velocity_ratio * (semantic_max - semantic_min))
            
            sim = get_semantic_sim(ts)
            if sim < dynamic_threshold:
                break
            final_start_idx = i
            
        trimmed_start = start_search + (final_start_idx / self.fps)
        trimmed_end = start_search + ((final_end_idx + 1) / self.fps)
        duration = trimmed_end - trimmed_start
        
        if duration < min_duration: return None
            
        avg_jitter = np.mean([frame_scores[i]["jitter"] for i in range(final_start_idx, final_end_idx + 1)])
        return {
            "start_sec": trimmed_start,
            "end_sec": trimmed_end,
            "trimmed_start": round(trimmed_start, 3),
            "trimmed_end": round(trimmed_end, 3),
            "duration": round(duration, 2),
            "stability_score": round(avg_jitter, 2)
        }

import cv2
import numpy as np
import logging
import os

logger = logging.getLogger("StabilityTrimmer")

def get_ascii_bar(progress, length=20):
    filled = int(length * progress)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {progress*100:>3.0f}%"

class StabilityTrimmer:
    def __init__(self, video_path):
        self.video_path = video_path
        self.stability_map = []

    def analyze_stability(self):
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        prev_frame = None
        stability_map = []
        
        logger.info(f"Stability analysis started: {total_frames} frames.")
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 180))
            
            if prev_frame is not None:
                flow = cv2.calcOpticalFlowFarneback(prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                stability_map.append({
                    "timestamp": frame_idx / fps,
                    "chaos": float(np.mean(mag)),
                    "jitter": float(np.std(mag))
                })
                
                if frame_idx % 20 == 0:
                    progress = frame_idx / total_frames
                    bar = get_ascii_bar(progress)
                    logger.info(f"\rStability Analysis: {bar} ({frame_idx}/{total_frames} frames)")
            
            prev_frame = gray
            frame_idx += 1
            
        cap.release()
        logger.info(f"Stability map complete. {len(stability_map)} frames analyzed.")
        self.stability_map = stability_map
        return stability_map

    def bidirectional_expand(self, hero_ts, hero_features, heatmap, buffer_sec=4.0, min_duration=2.0, 
                             semantic_max=0.85, semantic_min=0.75, max_chaos=12.0, max_jitter=3.0):
        
        if not self.stability_map:
            logger.warning("No stability map available!")
            return None

        def get_data_at(ts):
            s_data = min(self.stability_map, key=lambda x: abs(x["timestamp"] - ts))
            h_data = min(heatmap, key=lambda x: abs(x["timestamp"] - ts))
            feat = np.array(h_data["features"])
            similarity = np.dot(hero_features, feat) / (np.linalg.norm(hero_features) * np.linalg.norm(feat) + 1e-9)
            return s_data["chaos"], s_data["jitter"], similarity

        start_ts = hero_ts
        end_ts = hero_ts
        
        while end_ts < hero_ts + buffer_sec:
            next_ts = end_ts + 0.1
            if next_ts > self.stability_map[-1]["timestamp"]: break
            chaos, jitter, sim = get_data_at(next_ts)
            if sim < (semantic_max if chaos < 2.0 else semantic_min) or chaos > max_chaos or jitter > max_jitter: break
            end_ts = next_ts

        while start_ts > hero_ts - buffer_sec:
            prev_ts = start_ts - 0.1
            if prev_ts < self.stability_map[0]["timestamp"]: break
            chaos, jitter, sim = get_data_at(prev_ts)
            if sim < (semantic_max if chaos < 2.0 else semantic_min) or chaos > max_chaos or jitter > max_jitter: break
            start_ts = prev_ts

        duration = end_ts - start_ts
        if duration < min_duration:
            return None
            
        return {"trimmed_start": round(start_ts, 2), "trimmed_end": round(end_ts, 2), "duration": round(duration, 2)}

import cv2
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

class StabilityTrimmer:
    def __init__(self, video_path):
        self.video_path = video_path
        self.stability_map = [] # Cached flow data

    def analyze_stability(self, fps_target=10.0):
        """
        Analyzes the entire video for chaos and jitter once.
        Returns a map for caching.
        """
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        prev_frame = None
        stability_map = []
        
        logger.info(f"Generating Stability Map for {os.path.basename(self.video_path)}...")
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            timestamp = frame_idx / fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 180)) # Fast analysis
            
            if prev_frame is not None:
                # Optical Flow (Farneback - dense but on small res it's fast)
                flow = cv2.calcOpticalFlowFarneback(prev_frame, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                
                chaos = np.mean(mag)
                jitter = np.std(mag)
                
                stability_map.append({
                    "timestamp": timestamp,
                    "chaos": float(chaos),
                    "jitter": float(jitter)
                })
            
            prev_frame = gray
            frame_idx += 1
            
        cap.release()
        self.stability_map = stability_map
        return stability_map

    def bidirectional_expand(self, hero_ts, hero_features, heatmap, buffer_sec=4.0, min_duration=2.0, 
                             semantic_max=0.85, semantic_min=0.75, max_chaos=12.0, max_jitter=3.0):
        
        if not self.stability_map:
            logger.error("Stability map not loaded. Call analyze_stability or load cache.")
            return None

        # Find starting point in maps
        def get_data_at(ts):
            # Binary search would be better, but list is small (proxy length)
            s_data = min(self.stability_map, key=lambda x: abs(x["timestamp"] - ts))
            h_data = min(heatmap, key=lambda x: abs(x["timestamp"] - ts))
            
            # Semantic Similarity
            feat = np.array(h_data["features"])
            similarity = np.dot(hero_features, feat) / (np.linalg.norm(hero_features) * np.linalg.norm(feat) + 1e-9)
            
            return s_data["chaos"], s_data["jitter"], similarity

        start_ts = hero_ts
        end_ts = hero_ts
        
        # Expand Forward
        while end_ts < hero_ts + buffer_sec:
            next_ts = end_ts + 0.1
            if next_ts > self.stability_map[-1]["timestamp"]: break
            chaos, jitter, sim = get_data_at(next_ts)
            
            # Semantic Adaptive Gating
            dynamic_sim_threshold = semantic_max if chaos < 2.0 else semantic_min
            if sim < dynamic_sim_threshold or chaos > max_chaos or jitter > max_jitter:
                break
            end_ts = next_ts

        # Expand Backward
        while start_ts > hero_ts - buffer_sec:
            prev_ts = start_ts - 0.1
            if prev_ts < self.stability_map[0]["timestamp"]: break
            chaos, jitter, sim = get_data_at(prev_ts)
            
            dynamic_sim_threshold = semantic_max if chaos < 2.0 else semantic_min
            if sim < dynamic_sim_threshold or chaos > max_chaos or jitter > max_jitter:
                break
            start_ts = prev_ts

        if (end_ts - start_ts) < min_duration:
            return None
            
        return {
            "trimmed_start": round(start_ts, 2),
            "trimmed_end": round(end_ts, 2),
            "duration": round(end_ts - start_ts, 2)
        }

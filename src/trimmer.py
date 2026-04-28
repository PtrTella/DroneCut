import cv2
import numpy as np
import logging
from .config import STABILITY_THRESHOLD

logger = logging.getLogger(__name__)

def get_video_info(video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    cap.release()
    return fps, duration

def calculate_stability_window(video_path, start_sec, duration=2.0):
    """
    Fast sampling of a small window to find a stable cut point.
    """
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_MSEC, max(0, start_sec * 1000))
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    num_frames = int(duration * fps)
    
    prev_gray = None
    scores = []
    
    # Process only a few frames to stay fast
    for i in range(num_frames):
        ret, frame = cap.read()
        if not ret: break
            
        # Very small resize for maximum speed
        frame = cv2.resize(frame, (240, 135))
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 10, 3, 5, 1.2, 0)
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            scores.append(np.var(mag))
        prev_gray = gray
        
    cap.release()
    return scores

def trim_scene(video_path, scene, fps, total_duration):
    """
    Surgical trimming: only refines the edges of the clip.
    """
    start = scene["start_sec"]
    end = min(scene["end_sec"], total_duration)
    duration = end - start
    
    if duration < 1.0: 
        scene["discard_reason"] = f"Too_Short_Duration_{duration:.1f}"
        return {}

    # Fast Start Trim (check only first 2s)
    start_scores = calculate_stability_window(video_path, start, duration=min(duration, 2.0))
    new_start = start
    if start_scores:
        for i, score in enumerate(start_scores):
            if score < STABILITY_THRESHOLD:
                new_start = start + (i / fps)
                break

    # Fast End Trim (check only last 2s)
    check_end_start = max(new_start, end - 2.0)
    end_scores = calculate_stability_window(video_path, check_end_start, duration=end - check_end_start)
    new_end = end
    if end_scores:
        for i in range(len(end_scores)-1, -1, -1):
            if end_scores[i] < STABILITY_THRESHOLD:
                new_end = check_end_start + (i / fps)
                break
    
    new_start = max(0, new_start)
    new_end = min(total_duration, new_end)
    
    if (new_end - new_start) < 0.5: 
        scene["discard_reason"] = "Too_Short_After_Surgical_Trim"
        return {}

    return {
        **scene,
        "trimmed_start": round(new_start, 3),
        "trimmed_end": round(new_end, 3)
    }

class StabilityTrimmer:
    def __init__(self, original_video_path):
        self.video_path = original_video_path
        self.fps, self.total_duration = get_video_info(original_video_path)

    def process_scenes(self, scenes):
        trimmed_scenes = []
        discarded_scenes = []
        for scene in scenes:
            res = trim_scene(self.video_path, scene, self.fps, self.total_duration)
            if res: 
                trimmed_scenes.append(res)
            else:
                discarded_scenes.append(scene)
        return trimmed_scenes, discarded_scenes

import cv2
import numpy as np

def analyze_scene_visuals(video_path, start_time, end_time, sample_rate=1.0):
    """
    Analyzes a segment of video for brightness, contrast, and motion.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Seek to start
    cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
    
    metrics = {
        "brightness": [],
        "contrast": [],
        "motion": []
    }
    
    ret, prev_frame = cap.read()
    if not ret:
        return None
    
    prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    
    frame_count = 0
    while cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 < end_time:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        # Sample frames based on rate
        if frame_count % int(max(1, fps / sample_rate)) != 0:
            continue
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Brightness
        metrics["brightness"].append(np.mean(gray))
        
        # Contrast
        metrics["contrast"].append(np.std(gray))
        
        # Motion (pixel difference)
        diff = cv2.absdiff(prev_gray, gray)
        metrics["motion"].append(np.mean(diff))
        
        prev_gray = gray
        
    cap.release()
    
    if not metrics["brightness"]:
        return None
        
    motion_array = np.array(metrics["motion"])
    # Jerk is the absolute difference between consecutive motion values (rate of change of motion)
    jerk_array = np.abs(np.diff(motion_array)) if len(motion_array) > 1 else np.array([0.0])
    
    return {
        "avg_brightness": np.mean(metrics["brightness"]),
        "avg_contrast": np.mean(metrics["contrast"]),
        "avg_motion": np.mean(metrics["motion"]),
        "std_motion": np.std(metrics["motion"]),
        "max_jerk": np.max(jerk_array) if len(jerk_array) > 0 else 0.0,
        "avg_jerk": np.mean(jerk_array) if len(jerk_array) > 0 else 0.0
    }

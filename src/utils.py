import os
import hashlib
import cv2
import logging

logger = logging.getLogger(__name__)

def generate_video_fingerprint(video_path):
    """
    Generates a unique 'Lite' fingerprint for a video file.
    Combines file size, duration, and partial binary hashes.
    """
    if not os.path.exists(video_path):
        return None

    try:
        # 1. File size
        file_size = os.path.getsize(video_path)
        
        # 2. Duration (fast metadata check)
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        duration = frame_count / fps if fps > 0 else 0
        cap.release()

        # 3. Partial Binary Read (Head & Tail)
        # Read first 1MB and last 1MB
        chunk_size = 1024 * 1024 # 1MB
        with open(video_path, "rb") as f:
            head = f.read(chunk_size)
            if file_size > chunk_size:
                f.seek(-chunk_size, os.SEEK_END)
                tail = f.read(chunk_size)
            else:
                tail = b""

        # 4. Fusion & Hashing
        fusion_string = f"{file_size}_{duration:.3f}_{hashlib.md5(head).hexdigest()}_{hashlib.md5(tail).hexdigest()}"
        fingerprint = hashlib.sha256(fusion_string.encode()).hexdigest()
        
        logger.info(f"Fingerprint generated for {os.path.basename(video_path)}: {fingerprint[:12]}...")
        return fingerprint
        
    except Exception as e:
        logger.error(f"Failed to generate fingerprint: {e}")
        return None

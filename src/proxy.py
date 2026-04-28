import subprocess
import os
import logging
from .config import PROXY_RES, PROXY_FPS, PROXY_DIR

logger = logging.getLogger(__name__)

def generate_proxy(input_path):
    """
    Generates a low-res, low-fps proxy for fast analysis.
    Optimized for Apple Silicon (if ffmpeg supports h264_videotoolbox).
    """
    filename = os.path.basename(input_path)
    output_path = os.path.join(PROXY_DIR, f"proxy_{filename}")
    
    if os.path.exists(output_path):
        logger.info(f"Proxy already exists: {output_path}")
        return output_path

    logger.info(f"Generating proxy: {output_path} ({PROXY_RES}, {PROXY_FPS} FPS)")
    
    # Try to use hardware acceleration (videotoolbox for Mac)
    # If it fails, fallback to libx264
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-vf", f"scale={PROXY_RES},fps={PROXY_FPS}",
        "-c:v", "libx264", # libx264 is very fast for low res, and compatible
        "-preset", "ultrafast",
        "-crf", "30",
        "-an", # No audio
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg proxy generation failed: {e.stderr.decode()}")
        raise

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        generate_proxy(sys.argv[1])
    else:
        print("Usage: python -m src.proxy <input_video_path>")

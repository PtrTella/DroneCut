import subprocess
import os
import logging
from .config import PROXY_RES, STABILITY_FPS, PROXY_DIR, FFMPEG_BIN

logger = logging.getLogger(__name__)

def generate_proxy(input_path):
    """
    Generates a low-res, low-fps proxy for fast analysis.
    Uses the FFmpeg binary defined in config.
    """
    filename = os.path.basename(input_path)
    res_str = PROXY_RES.replace(":", "x")
    proxy_name = f"proxy_{res_str}_{STABILITY_FPS}fps_{filename}"
    output_path = os.path.join(PROXY_DIR, proxy_name)
    
    if os.path.exists(output_path):
        logger.info(f"Proxy already exists: {output_path}")
        return output_path

    logger.info(f"Generating proxy: {output_path} ({PROXY_RES}, {STABILITY_FPS} FPS)")
    
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", input_path,
        "-vf", f"scale={PROXY_RES},fps={STABILITY_FPS}",
        "-c:v", "libx264", 
        "-preset", "ultrafast",
        "-crf", "30",
        "-an",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg proxy generation failed: {e.stderr.decode()}")
        raise

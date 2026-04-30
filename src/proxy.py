import subprocess
import os
import logging
from .config import PROXY_RES, STABILITY_FPS, FFMPEG_BIN

logger = logging.getLogger(__name__)

def generate_proxy(input_path, output_dir=None):
    """
    Generates a low-res, low-fps proxy for fast analysis.
    If output_dir is provided, it saves it there (Project mode).
    """
    filename = os.path.basename(input_path)
    res_str = PROXY_RES.replace(":", "x")
    proxy_name = f"proxy_{res_str}_{STABILITY_FPS}fps_{filename}"
    
    if output_dir:
        output_path = os.path.join(output_dir, "proxy.mp4") # Fixed name inside project folder
    else:
        # Fallback to general cache (though we'll use projects now)
        from .config import CACHE_DIR
        output_path = os.path.join(CACHE_DIR, "Proxies", proxy_name)
    
    if os.path.exists(output_path):
        return output_path

    logger.info(f"Generating proxy: {output_path}")
    
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

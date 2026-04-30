import subprocess
import os
import logging
from .config import PROXY_RES, STABILITY_FPS, FFMPEG_BIN

logger = logging.getLogger("ProxyGenerator")

def generate_proxy(input_path, output_dir=None):
    filename = os.path.basename(input_path)
    res_str = PROXY_RES.replace(":", "x")
    proxy_name = f"proxy_{res_str}_{STABILITY_FPS}fps_{filename}"
    
    output_path = os.path.join(output_dir, "proxy.mp4") if output_dir else os.path.join(os.path.expanduser("~"), "Library", "Caches", "DroneCut", "Proxies", proxy_name)
    
    if os.path.exists(output_path):
        logger.info(f"Using cached proxy: {output_path}")
        return output_path

    logger.info(f"Generating new proxy ({res_str} @ {STABILITY_FPS}fps) for {filename}...")
    
    cmd = [
        FFMPEG_BIN, "-y", "-i", input_path,
        "-vf", f"scale={PROXY_RES},fps={STABILITY_FPS}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-an",
        output_path
    ]
    
    try:
        # Log the command for tech enthusiasts
        logger.info(f"FFmpeg command: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("✅ Proxy generation successful.")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ FFmpeg error: {e.stderr}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error during proxy gen: {e}")
        return None

import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def create_proxy(input_path, output_path, scale="640:360", fps=10):
    """
    Creates a low-res, low-fps proxy for fast analysis. 
    Using CPU ultrafast as it's often faster for small resolutions.
    """
    logger.info(f"Creating proxy for {input_path} at {output_path} (UltraFast Mode)")
    
    cmd = [
        "ffmpeg", "-y", 
        "-threads", "0",             # Use all CPU cores
        "-i", input_path,
        "-vf", f"scale={scale},fps={fps}",
        "-c:v", "libx264", 
        "-preset", "ultrafast",      # Maximum speed
        "-crf", "32",                # Lower quality for higher speed
        "-an",                       # No audio for speed
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)

def extract_clip(input_path, output_path, start_time, end_time, speed=1.0):
    """
    Extracts a clip from the input video using timestamps and applies speedup.
    Optimized for speed over quality for preview generation.
    """
    duration = end_time - start_time
    
    atempo_filters = []
    temp_speed = speed
    while temp_speed > 2.0:
        atempo_filters.append("atempo=2.0")
        temp_speed /= 2.0
    while temp_speed < 0.5:
        atempo_filters.append("atempo=0.5")
        temp_speed /= 0.5
    atempo_filters.append(f"atempo={temp_speed}")
    atempo_str = ",".join(atempo_filters)

    cmd = [
        "ffmpeg", "-y",
        "-threads", "0",
        "-ss", str(start_time),
        "-t", str(duration),
        "-i", input_path,
        "-vf", f"setpts={1.0/speed}*PTS",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-af", atempo_str,
        output_path
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)

def concatenate_clips(clip_paths, output_path):
    """
    Concatenates multiple clips using the FFmpeg concat demuxer.
    """
    list_file = "clips_list.txt"
    with open(list_file, "w") as f:
        for clip in clip_paths:
            f.write(f"file '{os.path.abspath(clip)}'\n")
    
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_file, "-c", "copy", output_path
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    finally:
        if os.path.exists(list_file):
            os.remove(list_file)

def add_background_music(video_path, audio_path, output_path):
    """
    Replaces the audio of the video with the provided music file.
    Trims the audio to match the video length.
    """
    cmd = [
        "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-shortest",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)

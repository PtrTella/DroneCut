import subprocess
import os
import logging

logger = logging.getLogger(__name__)

def create_proxy(input_path, output_path, scale="640:360", fps=10):
    """
    Creates a low-res, low-fps proxy for fast analysis.
    """
    logger.info(f"Creating proxy for {input_path} at {output_path}")
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vf", f"scale={scale},fps={fps}",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
        "-an", output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)

def extract_clip(input_path, output_path, start_time, end_time, speed=1.0):
    """
    Extracts a clip from the input video using timestamps and applies speedup.
    When speed != 1.0, we re-encode to apply filters and remove audio.
    """
    duration = end_time - start_time
    
    if speed == 1.0:
        cmd = [
            "ffmpeg", "-y", 
            "-ss", str(start_time), 
            "-t", str(duration),
            "-i", input_path,
            "-c", "copy",
            output_path
        ]
    else:
        # Re-encode to apply speedup filter
        # setpts=1/speed*PTS
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start_time),
            "-t", str(duration),
            "-i", input_path,
            "-vf", f"setpts={1/speed}*PTS",
            "-an", # Remove audio
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
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

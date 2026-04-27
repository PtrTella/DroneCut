import librosa
import numpy as np
import logging

logger = logging.getLogger(__name__)

def get_beat_timestamps(audio_path):
    """
    Analyzes an audio file and returns a list of timestamps (in seconds) for each beat.
    """
    logger.info(f"Analyzing audio beats in {audio_path}...")
    y, sr = librosa.load(audio_path)
    
    # Get tempo and beat frames
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    
    # Convert beat frames to timestamps
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    
    logger.info(f"Detected {len(beat_times)} beats. Estimated tempo: {tempo:.2f} BPM")
    return beat_times.tolist()

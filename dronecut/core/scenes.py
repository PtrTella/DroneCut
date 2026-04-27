from scenedetect import SceneManager, open_video, ContentDetector
import logging

logger = logging.getLogger(__name__)

def detect_scenes(video_path, threshold=30.0):
    """
    Detects scenes in a video using the ContentDetector.
    Returns a list of (start_time, end_time) tuples.
    """
    logger.info(f"Detecting scenes in {video_path} with threshold {threshold}")
    video = open_video(video_path)
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=threshold))
    
    scene_manager.detect_scenes(video)
    scene_list = scene_manager.get_scene_list()
    
    # Convert to seconds
    scenes = []
    for scene in scene_list:
        start = scene[0].get_seconds()
        end = scene[1].get_seconds()
        scenes.append((start, end))
        
    return scenes

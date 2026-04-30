import os
import subprocess
import logging
import json
import datetime
from .config import MOVIES_DIR, FFMPEG_BIN, CACHE_DIR

logger = logging.getLogger(__name__)

class Director:
    def __init__(self):
        self.base_output = os.path.join(MOVIES_DIR, "Exports")
        os.makedirs(self.base_output, exist_ok=True)

    def serialize_project(self, final_scenes, video_path, proxy_path=None):
        project_timeline = []
        for i, scene in enumerate(final_scenes):
            scene_id = i + 1
            item = {
                "id": scene["id"],
                "title": f"Clip {scene_id:02d}",
                "start_sec": scene["trimmed_start"],
                "end_sec": scene["trimmed_end"],
                "duration": round(scene["trimmed_end"] - scene["trimmed_start"], 2),
                "aesthetic_score": scene["aesthetic_score"],
                "proxy_path": proxy_path,
                "original_range": [scene["start_sec"], scene["end_sec"]]
            }
            project_timeline.append(item)
        return project_timeline

    def export_individual_clips(self, video_path, scenes, project_name):
        project_output = os.path.join(self.base_output, project_name)
        os.makedirs(project_output, exist_ok=True)
        
        for i, scene in enumerate(scenes):
            start, end = scene.get("trimmed_start"), scene.get("trimmed_end")
            output_path = os.path.join(project_output, f"Clip_{i+1:02d}.mp4")
            
            cmd = [
                FFMPEG_BIN, "-y", "-ss", str(start), "-t", str(end - start),
                "-i", video_path, "-c", "copy", "-avoid_negative_ts", "make_non_negative",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)
        return project_output

    def export_full_montage(self, video_path, scenes, project_name):
        project_output = os.path.join(self.base_output, project_name)
        os.makedirs(project_output, exist_ok=True)
        
        temp_dir = os.path.join(CACHE_DIR, "temp_export")
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_files = []
        for i, scene in enumerate(scenes):
            start, end = scene.get("trimmed_start"), scene.get("trimmed_end")
            temp_path = os.path.join(temp_dir, f"seg_{i:03d}.mp4")
            
            cmd = [
                FFMPEG_BIN, "-y", "-ss", str(start), "-t", str(end - start),
                "-i", video_path, "-c", "copy", "-avoid_negative_ts", "make_non_negative",
                temp_path
            ]
            subprocess.run(cmd, capture_output=True)
            temp_files.append(temp_path)
            
        if temp_files:
            list_path = os.path.join(temp_dir, "list.txt")
            montage_path = os.path.join(project_output, f"_Full_Montage_{project_name}.mp4")
            with open(list_path, "w") as f:
                for tf in temp_files: f.write(f"file '{tf}'\n")
            
            concat_cmd = [
                FFMPEG_BIN, "-y", "-f", "concat", "-safe", "0",
                "-i", list_path, "-c", "copy", montage_path
            ]
            subprocess.run(concat_cmd, capture_output=True)
            
            import shutil
            shutil.rmtree(temp_dir)
            return montage_path
        return None

    def save_debug_report(self, discarded_heroes, project_dir, filename="debug_report.json"):
        if not project_dir or not os.path.exists(project_dir): return
        report = {
            "timestamp": str(datetime.datetime.now()),
            "discarded_count": len(discarded_heroes),
            "discarded_details": discarded_heroes
        }
        with open(os.path.join(project_dir, filename), "w") as f:
            json.dump(report, f, indent=2)

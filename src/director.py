import os
import subprocess
import logging
import json
import cv2
import numpy as np
from PIL import Image
from .config import OUTPUT_DIR, PROJECT_FILE, FFMPEG_BIN, CACHE_DIR

logger = logging.getLogger(__name__)

class Director:
    def __init__(self, output_dir=OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def serialize_project(self, final_scenes, video_path, proxy_path=None):
        """
        Stage 4: Final Serialization
        Saves thumbnails, generates sequential titles, and exports the .dcproj manifest.
        Uses proxy_path for thumbnails if provided (much faster).
        """
        thumb_source = proxy_path if proxy_path else video_path
        # Thumbnails in Cache instead of Output for a cleaner export folder
        thumb_dir = os.path.join(CACHE_DIR, "thumbnails")
        os.makedirs(thumb_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(thumb_source)
        project_timeline = []
        
        for i, scene in enumerate(final_scenes):
            scene_id = i + 1
            scene_title = f"Scena_{scene_id:02d}"
            
            # Extract Thumbnail
            mid_sec = (scene["trimmed_start"] + scene["trimmed_end"]) / 2
            cap.set(cv2.CAP_PROP_POS_MSEC, mid_sec * 1000)
            ret, frame = cap.read()
            thumb_path = ""
            if ret:
                thumb_name = f"thumb_{scene_id:02d}.jpg"
                thumb_path = os.path.join(thumb_dir, thumb_name)
                cv2.imwrite(thumb_path, frame)
            
            # Build Project Item
            clip_name = f"shot_{i:03d}_id_{scene['id']}.mp4"
            clip_path = os.path.join(self.output_dir, "timeline", clip_name)

            item = {
                "id": scene["id"],
                "title": scene_title,
                "start_sec": scene["trimmed_start"],
                "end_sec": scene["trimmed_end"],
                "duration": round(scene["trimmed_end"] - scene["trimmed_start"], 2),
                "aesthetic_score": scene["aesthetic_score"],
                "thumbnail": thumb_path,
                "video_clip": clip_path,
                "original_range": [scene["start_sec"], scene["end_sec"]]
            }
            project_timeline.append(item)
            
        cap.release()
        
        # Save .dcproj (JSON)
        project_data = {
            "version": "5.2",
            "video_source": video_path,
            "total_clips": len(project_timeline),
            "timeline": project_timeline
        }
        
        with open(PROJECT_FILE, "w") as f:
            json.dump(project_data, f, indent=2)
            
        logger.info(f"Project serialized to {PROJECT_FILE}")
        return project_timeline

    def save_debug_report(self, all_discarded):
        # Debug report in Cache
        report_path = os.path.join(CACHE_DIR, "debug_report.json")
        summary = {
            "total_discarded": len(all_discarded),
            "reasons": {}
        }
        for s in all_discarded:
            reason = s.get("discard_reason", "unknown")
            summary["reasons"][reason] = summary["reasons"].get(reason, 0) + 1
            
        report = {
            "summary": summary,
            "details": [
                {
                    "id": s.get("id"),
                    "start": s.get("start_sec"),
                    "end": s.get("end_sec"),
                    "reason": s.get("discard_reason"),
                    "aesthetic_score": s.get("aesthetic_score")
                } for s in all_discarded
            ]
        }
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Debug report saved to {report_path}")

    def export_timeline(self, video_path, scenes):
        target_dir = os.path.join(self.output_dir, "timeline")
        os.makedirs(target_dir, exist_ok=True)
        for i, scene in enumerate(scenes):
            start = scene.get("trimmed_start", scene["start_sec"])
            end = scene.get("trimmed_end", scene["end_sec"])
            duration = end - start
            filename = f"shot_{i:03d}_id_{scene['id']}.mp4"
            output_path = os.path.join(target_dir, filename)
            
            cmd = [
                FFMPEG_BIN, "-y", "-ss", str(start), "-t", str(duration),
                "-i", video_path, "-c", "copy", "-avoid_negative_ts", "make_non_negative",
                output_path
            ]
            subprocess.run(cmd, capture_output=True)
        logger.info(f"Export completed. Files located in: {target_dir}")

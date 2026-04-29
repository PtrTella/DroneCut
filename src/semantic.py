import torch
import cv2
import numpy as np
import logging
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from .config import CLIP_MODEL, SEMANTIC_CUT_THRESHOLD

logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    def __init__(self, batch_size=32):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "mps" else torch.float32
        self.batch_size = batch_size
        
        logger.info(f"Initializing Chronological SemanticAnalyzer on {self.device}")
        self.model = CLIPModel.from_pretrained(CLIP_MODEL, dtype=self.dtype).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

    def detect_scenes(self, proxy_path):
        """
        Stage 1: Chronological Scene Detection
        Scans the video and detects cuts based on cosine similarity between consecutive frames.
        """
        cap = cv2.VideoCapture(proxy_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        logger.info(f"Analyzing {total_frames} frames for chronological cuts...")
        
        embeddings_list = []
        timestamps = []
        
        frame_count = 0
        frames = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_count / fps
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            frames.append(image)
            timestamps.append(timestamp)
            
            if len(frames) >= self.batch_size:
                embeddings_list.append(self._process_batch(frames))
                frames = []
                
            frame_count += 1
            
        if frames:
            embeddings_list.append(self._process_batch(frames))
            
        cap.release()
        
        if not embeddings_list:
            return []

        all_embeddings = torch.cat(embeddings_list, dim=0)
        
        scenes = []
        current_scene_start_idx = 0
        
        for i in range(1, len(all_embeddings)):
            # Compare current frame with previous frame
            sim = (all_embeddings[i] * all_embeddings[i-1]).sum().item()
            
            if sim < SEMANTIC_CUT_THRESHOLD:
                # Cut detected
                scenes.append({
                    "start_sec": round(timestamps[current_scene_start_idx], 3),
                    "end_sec": round(timestamps[i], 3),
                    "id": len(scenes) + 1
                })
                current_scene_start_idx = i
                
        # Final scene
        if current_scene_start_idx < len(all_embeddings):
            scenes.append({
                "start_sec": round(timestamps[current_scene_start_idx], 3),
                "end_sec": round(frame_count / fps, 3),
                "id": len(scenes) + 1
            })
        
        logger.info(f"Detected {len(scenes)} chronological chapters.")
        return scenes

    def _process_batch(self, images):
        inputs = self.processor(images=images, return_tensors="pt", padding=True).to(self.device)
        if self.dtype == torch.float16:
            inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)
            
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            return outputs / outputs.norm(dim=-1, keepdim=True)

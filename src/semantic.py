import torch
import cv2
import numpy as np
import logging
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from .config import CLIP_MODEL, SEMANTIC_THRESHOLD, MAX_SCENE_DURATION

logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    def __init__(self, batch_size=16):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "mps" else torch.float32
        self.batch_size = batch_size
        
        logger.info(f"Initializing SemanticAnalyzer on {self.device} (Batch Size: {self.batch_size})")
        # Use dtype for cleaner loading
        self.model = CLIPModel.from_pretrained(CLIP_MODEL, dtype=self.dtype).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(CLIP_MODEL)

    def detect_scenes(self, proxy_path):
        cap = cv2.VideoCapture(proxy_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        embeddings_list = []
        timestamps = []
        
        logger.info(f"Analyzing semantics (Batched) for: {proxy_path}")
        
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
            # Fix: Use torch.dot or proper matmul for 1D/2D consistency to avoid UserWarning
            sim = (all_embeddings[i] * all_embeddings[i-1]).sum().item()
            duration = timestamps[i] - timestamps[current_scene_start_idx]
            
            if sim < SEMANTIC_THRESHOLD or duration >= MAX_SCENE_DURATION:
                scene_embeddings = all_embeddings[current_scene_start_idx:i]
                summary_vector = torch.mean(scene_embeddings, dim=0).cpu().numpy()
                
                scenes.append({
                    "start_sec": round(timestamps[current_scene_start_idx], 3),
                    "end_sec": round(timestamps[i], 3),
                    "id": len(scenes) + 1,
                    "clip_embedding": summary_vector.tolist()
                })
                current_scene_start_idx = i
                
        # Final scene
        if current_scene_start_idx < len(all_embeddings):
            scene_embeddings = all_embeddings[current_scene_start_idx:]
            summary_vector = torch.mean(scene_embeddings, dim=0).cpu().numpy()
            scenes.append({
                "start_sec": round(timestamps[current_scene_start_idx], 3),
                "end_sec": round(frame_count / fps, 3),
                "id": len(scenes) + 1,
                "clip_embedding": summary_vector.tolist()
            })
        
        return scenes

    def _process_batch(self, images):
        inputs = self.processor(images=images, return_tensors="pt", padding=True).to(self.device)
        if self.dtype == torch.float16:
            inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)
            
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            return outputs / outputs.norm(dim=-1, keepdim=True)

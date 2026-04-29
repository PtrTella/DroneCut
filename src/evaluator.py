import torch
import torch.nn as nn
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import logging
import cv2
import numpy as np
import os
import urllib.request
from .config import HEATMAP_FPS

logger = logging.getLogger(__name__)

class LAIONAestheticPredictor(nn.Module):
    def __init__(self, input_size=768): # 768 per ViT-L/14
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_size, 1024),
            nn.Dropout(0.2),
            nn.Linear(1024, 128),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.Dropout(0.1),
            nn.Linear(64, 16),
            nn.Linear(16, 1)
        )

    def forward(self, x):
        return self.layers(x)

class SceneEvaluator:
    def __init__(self):
        self.device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        logger.info(f"Loading LAION-Aesthetics V2 (ViT-L/14) Evaluator on {self.device}...")
        
        model_id = "openai/clip-vit-large-patch14"
        self.processor = CLIPProcessor.from_pretrained(model_id, use_fast=True)
        self.clip = CLIPModel.from_pretrained(model_id).to(self.device)
        self.clip.eval()
        
        self.head = LAIONAestheticPredictor(input_size=768).to(self.device)
        self._load_local_weights()
        self.head.eval()
        logger.info("✅ Evaluator Ready.")

    def _load_local_weights(self):
        weights_path = os.path.join(os.path.dirname(__file__), "models", "aesthetic.pth")
        if os.path.exists(weights_path):
            try:
                state_dict = torch.load(weights_path, map_location=self.device)
                self.head.load_state_dict(state_dict)
                logger.info(f"✅ Pesi LAION (L14) caricati correttamente.")
            except Exception as e:
                logger.error(f"❌ Errore nel caricamento dei pesi locali: {e}")
        else:
            logger.warning(f"⚠️ Pesi estetici L14 non trovati.")

    @torch.no_grad()
    def evaluate_frame(self, frame_pil):
        inputs = self.processor(images=frame_pil, return_tensors="pt").to(self.device)
        image_features = self.clip.get_image_features(**inputs)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        score = self.head(image_features).item()
        features = image_features.cpu().numpy().flatten()
        return round(score, 3), features

    def generate_heatmap(self, video_path, heatmap_fps=2.0):
        """
        Generates heatmap by sampling the proxy at the requested HEATMAP_FPS.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) # This is STABILITY_FPS (10.0)
        
        # Calculate interval to match HEATMAP_FPS
        interval = max(1, int(fps / heatmap_fps)) if fps > 0 else 1
        
        heatmap = []
        logger.info(f"Generating Heatmap from Proxy ({fps} FPS) sampling every {interval} frames...")
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            if frame_idx % interval == 0:
                timestamp = frame_idx / fps
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                
                score, features = self.evaluate_frame(pil_img)
                heatmap.append({
                    "timestamp": timestamp, 
                    "score": score,
                    "features": features
                })
                
            frame_idx += 1
        cap.release()
        
        if heatmap:
            scores = [h["score"] for h in heatmap]
            min_s, max_s = min(scores), max(scores)
            if max_s - min_s < 1.0:
                for h in heatmap:
                    h["score"] = (h["score"] - min_s) / (max_s - min_s + 1e-6) * 5.0 + 3.0
        
        return heatmap

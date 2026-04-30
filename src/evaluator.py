import torch
import torch.nn as nn
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import logging
import cv2
import numpy as np
import os

logger = logging.getLogger("Evaluator")

def get_ascii_bar(progress, length=20):
    filled = int(length * progress)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}] {progress*100:>3.0f}%"

class LAIONAestheticPredictor(nn.Module):
    def __init__(self, input_size=768):
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
        logger.info(f"Using device: {self.device}")
        
        model_id = "openai/clip-vit-large-patch14"
        logger.info(f"Loading CLIP model: {model_id}...")
        self.processor = CLIPProcessor.from_pretrained(model_id, use_fast=True)
        self.clip = CLIPModel.from_pretrained(model_id).to(self.device)
        self.clip.eval()
        
        logger.info("Initializing LAION Aesthetic Predictor head...")
        self.head = LAIONAestheticPredictor(input_size=768).to(self.device)
        self._load_local_weights()
        self.head.eval()
        logger.info("✅ Aesthetic Evaluator fully initialized.")

    def _load_local_weights(self):
        weights_path = os.path.join(os.path.dirname(__file__), "models", "aesthetic.pth")
        if os.path.exists(weights_path):
            try:
                logger.info(f"Loading weights from {weights_path}...")
                state_dict = torch.load(weights_path, map_location=self.device)
                self.head.load_state_dict(state_dict)
                logger.info("✅ LAION weights loaded successfully.")
            except Exception as e:
                logger.error(f"❌ Error loading weights: {e}")
        else:
            logger.warning("⚠️ No local aesthetic weights found, using random initialization.")

    @torch.no_grad()
    def evaluate_frame(self, frame_pil):
        inputs = self.processor(images=frame_pil, return_tensors="pt").to(self.device)
        image_features = self.clip.get_image_features(**inputs)
        image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
        score = self.head(image_features).item()
        features = image_features.cpu().numpy().flatten()
        return round(score, 3), features

    def generate_heatmap(self, video_path, heatmap_fps=2.0):
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        interval = max(1, int(fps / heatmap_fps)) if fps > 0 else 1
        
        logger.info(f"Heatmap generation started. Target: {heatmap_fps}fps")
        
        heatmap = []
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            if frame_idx % interval == 0:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                score, features = self.evaluate_frame(Image.fromarray(frame_rgb))
                heatmap.append({"timestamp": frame_idx / fps, "score": score, "features": features})
                
                # Dynamic Progress Update
                progress = frame_idx / total_frames
                bar = get_ascii_bar(progress)
                logger.info(f"\rAesthetic Analysis: {bar} ({frame_idx}/{total_frames} frames)")
                
            frame_idx += 1
        cap.release()
        
        logger.info(f"Heatmap complete. {len(heatmap)} points generated.")
        if heatmap:
            scores = [h["score"] for h in heatmap]
            min_s, max_s = min(scores), max(scores)
            if max_s - min_s < 1.0:
                for h in heatmap:
                    h["score"] = (h["score"] - min_s) / (max_s - min_s + 1e-6) * 5.0 + 3.0
        return heatmap

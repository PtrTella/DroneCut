import torch
import torch.nn as nn
import cv2
import logging
import gc
import os
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from huggingface_hub import hf_hub_download
from .config import CLIP_MODEL, AESTHETIC_MODEL

logger = logging.getLogger(__name__)

class AestheticHead(nn.Module):
    def __init__(self, input_dim=512):
        super().__init__()
        self.layers = nn.Sequential(nn.Linear(input_dim, 1))
    def forward(self, x):
        return self.layers(x)

class SceneEvaluator:
    def __init__(self):
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.dtype = torch.float16 if self.device == "mps" else torch.float32
        
        logger.info(f"Initializing SceneEvaluator on {self.device} (Technical Engine)")
        
        # Load CLIP & Aesthetic Predictor
        self.clip_model = CLIPModel.from_pretrained(CLIP_MODEL, dtype=self.dtype).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
        self.aesthetic_head = self._load_aesthetic_head()

    def _load_aesthetic_head(self):
        try:
            head = AestheticHead().to(self.device).to(self.dtype)
            weights_path = hf_hub_download(repo_id="shunk031/aesthetics-predictor-v1-vit-base-patch32", filename="pytorch_model.bin")
            checkpoint = torch.load(weights_path, map_location=self.device)
            if "layers.0.weight" in checkpoint:
                head.layers[0].load_state_dict({"weight": checkpoint["layers.0.weight"], "bias": checkpoint["layers.0.bias"]})
            return head
        except Exception as e:
            logger.error(f"Failed to load aesthetic head: {e}")
            return None

    def evaluate_aesthetic(self, image):
        inputs = self.clip_processor(images=image, return_tensors="pt").to(self.device)
        if self.dtype == torch.float16:
            inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)
        with torch.no_grad():
            outputs = self.clip_model.get_image_features(**inputs)
            embeds = outputs / outputs.norm(dim=-1, keepdim=True)
            score = self.aesthetic_head(embeds).item() * 10.0 if self.aesthetic_head else 5.0
        return round(score, 2)

    def process_scenes_optimized(self, video_path, scenes):
        cap = cv2.VideoCapture(video_path)
        logger.info(f"Aesthetic Scoring for {len(scenes)} candidates (Multi-Frame Average)...")
        for scene in scenes:
            start = scene["trimmed_start"]
            end = scene["trimmed_end"]
            duration = end - start
            
            # Sampling strategy: 3 points (25%, 50%, 75%)
            sample_points = [start + duration * 0.25, start + duration * 0.5, start + duration * 0.75]
            scores = []
            
            for i, t in enumerate(sample_points):
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
                ret, frame = cap.read()
                if ret:
                    if i == 1: # Keep mid-frame for thumbnail
                         scene["_temp_frame"] = frame 
                    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    scores.append(self.evaluate_aesthetic(image))
            
            if scores:
                scene["aesthetic_score"] = round(sum(scores) / len(scores), 2)
            else:
                scene["aesthetic_score"] = 0.0
        cap.release()
        return scenes

    def cleanup(self):
        logger.info("Aggressive VRAM Cleanup...")
        self.clip_model = self.aesthetic_head = None
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

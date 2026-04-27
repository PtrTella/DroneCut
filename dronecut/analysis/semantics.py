import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class SemanticAnalyzer:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        if torch.cuda.is_available():
            self.device = "cuda"
        elif torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
            
        logger.info(f"Using device: {self.device}")
        
        # Load in float16 for MPS/CUDA to save memory and speed up
        dtype = torch.float16 if self.device in ["cuda", "mps"] else torch.float32
        
        self.model = CLIPModel.from_pretrained(model_name, torch_dtype=dtype).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        
    def get_keyframe(self, video_path, timestamp):
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        cap.release()
        if ret:
            # Convert BGR to RGB
            return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return None

    def score_scene(self, video_path, start_time, end_time, prompts):
        """
        Scores a scene against a list of text prompts using CLIP and returns embedding.
        Takes a keyframe from the middle of the scene.
        """
        mid_time = (start_time + end_time) / 2
        image = self.get_keyframe(video_path, mid_time)
        if image is None:
            return 0.0, None
            
        inputs = self.processor(text=prompts, images=image, return_tensors="pt", padding=True).to(self.device)
        
        # Ensure inputs match model dtype
        if self.model.dtype != torch.float32:
            inputs["pixel_values"] = inputs["pixel_values"].to(self.model.dtype)
            
        with torch.no_grad():
            outputs = self.model(**inputs)
            image_embeds = outputs.image_embeds # normalized image features
            logits_per_image = outputs.logits_per_image 
            probs = logits_per_image.softmax(dim=1) 
            
        return probs.max().item(), image_embeds.cpu().numpy()

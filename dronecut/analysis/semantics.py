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

    def score_scene(self, video_path, start_time, end_time, positive_prompts, negative_prompts=None):
        """
        Scores a scene by calculating (max positive similarity - max negative similarity).
        """
        negative_prompts = negative_prompts or []
        all_prompts = positive_prompts + negative_prompts
        
        mid_time = (start_time + end_time) / 2
        image = self.get_keyframe(video_path, mid_time)
        if image is None:
            return 0.0, None
            
        inputs = self.processor(text=all_prompts, images=image, return_tensors="pt", padding=True).to(self.device)
        
        if self.model.dtype != torch.float32:
            inputs["pixel_values"] = inputs["pixel_values"].to(self.model.dtype)
            
        with torch.no_grad():
            outputs = self.model(**inputs)
            # image_embeds are the projected visual features
            # text_embeds are the projected text features
            image_embeds = outputs.image_embeds / outputs.image_embeds.norm(dim=-1, keepdim=True)
            text_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
            
            # Cosine similarities
            similarities = (image_embeds @ text_embeds.T).squeeze(0) # [num_prompts]
            
        pos_sims = similarities[:len(positive_prompts)]
        neg_sims = similarities[len(positive_prompts):]
        
        max_pos = pos_sims.max().item() if len(pos_sims) > 0 else 0.0
        max_neg = neg_sims.max().item() if len(neg_sims) > 0 else 0.0
        
        # Final score is the difference. We use max() to avoid negative results if positive is strong
        final_score = max_pos - max_neg
        
        return float(final_score), image_embeds.cpu().numpy()

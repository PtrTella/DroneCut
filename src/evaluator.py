import torch
import torch.nn as nn
import cv2
import logging
import gc
import os
import re
from PIL import Image
from transformers import CLIPProcessor, CLIPModel, AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import hf_hub_download
from .config import CLIP_MODEL, AESTHETIC_MODEL, MOONDREAM_MODEL

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
        
        logger.info(f"Initializing SceneEvaluator on {self.device} (VLM Director Engine)")
        
        # Load CLIP & Aesthetic Predictor
        self.clip_model = CLIPModel.from_pretrained(CLIP_MODEL, torch_dtype=self.dtype).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(CLIP_MODEL)
        self.aesthetic_head = self._load_aesthetic_head()
        
        # VLM State
        self.vlm_model = None
        self.vlm_tokenizer = None

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

    def _ensure_vlm(self):
        if self.vlm_model is not None: return
        logger.info(f"Loading Moondream2 (VLM Director)...")
        try:
            self.vlm_model = AutoModelForCausalLM.from_pretrained(
                MOONDREAM_MODEL, 
                trust_remote_code=True, 
                torch_dtype=self.dtype
            ).to(self.device)
            self.vlm_tokenizer = AutoTokenizer.from_pretrained(MOONDREAM_MODEL)
        except Exception as e:
            logger.error(f"VLM load failed: {e}")

    def audit_quality(self, image):
        """
        VLM Auditor: Scarta errori macroscopici di inquadratura.
        """
        self._ensure_vlm()
        prompt = "Look at this image. Is the shot well-framed and visually interesting for a drone video? Answer strictly YES or NO."
        try:
            enc = self.vlm_model.encode_image(image)
            answer = self.vlm_model.answer_question(enc, prompt, self.vlm_tokenizer).strip().upper()
            return "YES" in answer
        except:
            return True # In case of error, we keep it

    def calculate_relevance(self, image, theme_prompt):
        """
        VLM Theme Scoring: Da 1 a 10 quanto la scena c'entra con il desiderio dell'utente.
        """
        if not theme_prompt: return 10
        self._ensure_vlm()
        prompt = f"Theme: {theme_prompt}. Look at this image. How relevant is this shot to the theme on a scale from 1 to 10? Answer with only the digit."
        try:
            enc = self.vlm_model.encode_image(image)
            answer = self.vlm_model.answer_question(enc, prompt, self.vlm_tokenizer).strip()
            # Extract first digit found
            digit = re.search(r'\d+', answer)
            return int(digit.group()) if digit else 5
        except:
            return 7

    def generate_caption(self, image):
        self._ensure_vlm()
        prompt = "Describe this aerial drone landscape photography in max 5 words, focusing on the main geographical features."
        try:
            inputs = self.vlm_model.encode_image(image)
            return self.vlm_model.answer_question(inputs, prompt, self.vlm_tokenizer)
        except:
            return "landscape shot"

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
        logger.info(f"Aesthetic Scoring for {len(scenes)} candidates...")
        for scene in scenes:
            mid_time = (scene["trimmed_start"] + scene["trimmed_end"]) / 2
            cap.set(cv2.CAP_PROP_POS_MSEC, mid_time * 1000)
            ret, frame = cap.read()
            if ret:
                scene["_temp_frame"] = frame 
                image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                scene["aesthetic_score"] = self.evaluate_aesthetic(image)
            else:
                scene["aesthetic_score"] = 0.0
        cap.release()
        return scenes

    def cleanup(self):
        logger.info("Aggressive VRAM Cleanup...")
        self.vlm_model = self.vlm_tokenizer = self.clip_model = self.aesthetic_head = None
        gc.collect()
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()

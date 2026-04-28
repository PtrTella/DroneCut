import torch
import torch.nn as nn
from PIL import Image
from transformers import CLIPProcessor, CLIPModel, AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import hf_hub_download
import logging
import re
import numpy as np

logger = logging.getLogger(__name__)

class AnalysisManager:
    """
    Centralized manager for all AI models used in DroneCut.
    Handles CLIP (Semantics + Aesthetics) and Moondream2 (Cinematics).
    """
    def __init__(self, clip_model="openai/clip-vit-base-patch32", vlm_model="vikhyatk/moondream2"):
        self.device = self._get_device()
        self.dtype = torch.float16 if self.device in ["cuda", "mps"] else torch.float32
        
        logger.info(f"Initializing AnalysisManager on {self.device} with {self.dtype}")
        
        # 1. Load CLIP
        self.clip_model = CLIPModel.from_pretrained(clip_model, dtype=self.dtype).to(self.device)
        self.clip_processor = CLIPProcessor.from_pretrained(clip_model)
        
        # 2. Load Aesthetic Head
        self.aesthetic_head = self._load_aesthetic_head()
        
        # 3. VLM Config (Lazy loaded)
        self.vlm_model_id = vlm_model
        self.vlm_model = None
        self.vlm_tokenizer = None

    def _get_device(self):
        if torch.cuda.is_available(): return "cuda"
        if torch.backends.mps.is_available(): return "mps"
        return "cpu"

    def _load_aesthetic_head(self):
        try:
            head = nn.Linear(512, 1).to(self.device).to(self.dtype)
            weights_path = hf_hub_download(repo_id="shunk031/aesthetics-predictor-v1-vit-base-patch32", filename="pytorch_model.bin")
            checkpoint = torch.load(weights_path, map_location=self.device)
            if "layers.0.weight" in checkpoint:
                head.load_state_dict({"weight": checkpoint["layers.0.weight"], "bias": checkpoint["layers.0.bias"]})
                logger.info("Aesthetic head loaded successfully.")
                return head
        except Exception as e:
            logger.error(f"Failed to load aesthetic head: {e}")
        return None

    def _ensure_vlm(self):
        if self.vlm_model is None:
            logger.info(f"Loading VLM model {self.vlm_model_id}...")
            from transformers import AutoConfig
            
            # The most stable revision for Moondream 2 is '2024-08-26'
            revision = "2024-08-26" if "moondream2" in self.vlm_model_id else "main"
            
            # 1. Load config
            config = AutoConfig.from_pretrained(self.vlm_model_id, trust_remote_code=True, revision=revision)
            if not hasattr(config, "pad_token_id"):
                config.pad_token_id = getattr(config, "eos_token_id", 0)

            # 2. Load model
            self.vlm_model = AutoModelForCausalLM.from_pretrained(
                self.vlm_model_id, 
                config=config,
                trust_remote_code=True, 
                dtype=self.dtype,
                revision=revision,
                device_map={"": self.device} if self.device != "cpu" else None
            )
            
            # 3. COMPATIBILITY PATCH (For transformers 4.50+)
            # 3. FINAL FAIL-SAFE PATCH
            from transformers.generation import GenerationMixin
            
            # Bridge 'generate' to the main model and its inner text model if needed
            for target in [self.vlm_model, getattr(self.vlm_model, "text", None)]:
                if target is not None and not hasattr(target, "generate"):
                    logger.info(f"Bridging 'generate' for {target.__class__.__name__}")
                    target.generate = GenerationMixin.generate.__get__(target, target.__class__)
                    target.can_generate = lambda: True
            
            self.vlm_tokenizer = AutoTokenizer.from_pretrained(self.vlm_model_id, revision=revision)

    def get_frame(self, video_path, timestamp):
        import cv2
        from PIL import Image
        cap = cv2.VideoCapture(video_path)
        cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
        ret, frame = cap.read()
        cap.release()
        if ret:
            return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return None

    def analyze_scene(self, image, pos_prompts, neg_prompts=None, run_vlm=False):
        """
        Complete analysis of a single frame.
        """
        if image is None: return 0.0, 0.0, 0.0, None
        
        pos_prompts = pos_prompts or []
        neg_prompts = neg_prompts or []
        
        # --- CLIP & Aesthetic ---
        semantic_score = 0.0
        aesthetic_score = 0.0
        img_embeds = None
        
        actual_texts = pos_prompts + neg_prompts
        dummy_mode = not actual_texts
        if dummy_mode: actual_texts = [""]

        inputs = self.clip_processor(text=actual_texts, images=image, return_tensors="pt", padding=True).to(self.device)
        if self.dtype == torch.float16:
            inputs["pixel_values"] = inputs["pixel_values"].to(torch.float16)
            
        with torch.no_grad():
            outputs = self.clip_model(**inputs)
            img_embeds = outputs.image_embeds 
            
            if not dummy_mode:
                img_embeds_norm = img_embeds / img_embeds.norm(dim=-1, keepdim=True)
                txt_embeds = outputs.text_embeds / outputs.text_embeds.norm(dim=-1, keepdim=True)
                similarities = (img_embeds_norm @ txt_embeds.T).squeeze(0)
                max_pos = similarities[:len(pos_prompts)].max().item() if pos_prompts else 0.0
                max_neg = similarities[len(pos_prompts):].max().item() if neg_prompts else 0.0
                semantic_score = max_pos - max_neg
            
            if self.aesthetic_head:
                img_embeds_norm = img_embeds / img_embeds.norm(dim=-1, keepdim=True)
                aesthetic_score = self.aesthetic_head(img_embeds_norm).item() / 10.0
                
        # --- VLM (Cinematic) ---
        cinematic_score = 0.0
        if run_vlm:
            self._ensure_vlm()
            try:
                with torch.no_grad():
                    # Moondream 2 encoding/answering
                    vlm_embeds = self.vlm_model.encode_image(image)
                    prompt = "Rate the cinematic composition and lighting of this drone shot from 1 to 10. Answer with ONLY the number."
                    answer = self.vlm_model.answer_question(vlm_embeds, prompt, self.vlm_tokenizer)
                    match = re.search(r"(\d+)", answer)
                    if match:
                        cinematic_score = int(match.group(1)) / 10.0
            except Exception as e:
                logger.error(f"VLM analysis error: {e}")
                
        return float(semantic_score), float(aesthetic_score), float(cinematic_score), img_embeds.cpu().numpy() if img_embeds is not None else None

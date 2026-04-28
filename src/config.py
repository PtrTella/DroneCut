import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
INPUT_DIR = os.path.join(DATA_DIR, "input")
PROXY_DIR = os.path.join(DATA_DIR, "proxy")
OUTPUT_DIR = os.path.join(DATA_DIR, "output")
DEBUG_DIR = os.path.join(DATA_DIR, "debug")

# Debug & UI
DEBUG_MODE = True 
THEME_PROMPT = None 

# Stage 1: Proxy
PROXY_RES = "854:480"
PROXY_FPS = 1 

# Stage 2: Semantic Mapping (CLIP)
CLIP_MODEL = "openai/clip-vit-base-patch32"
SEMANTIC_THRESHOLD = 0.87
MAX_SCENE_DURATION = 45.0 

# Stage 3: DBSCAN Clustering & Ambiguity
DBSCAN_EPS = 0.12 # Ultra-stretto per creare micro-cluster specifici
DBSCAN_MIN_SAMPLES = 1 # Non scartare nulla come rumore
AMBIGUITY_THRESHOLD = 0.70 # Molto permissivo: organizza in piccoli gruppi ma non buttare via niente
MIN_SCENE_DURATION = 2.0 

# Stage 4: Surgical Trimmer (OpenCV)
STABILITY_THRESHOLD = 1.5 

# Stage 5 & 6: Evaluator & VLM Director
MOONDREAM_MODEL = "vikhyatk/moondream2" 
AESTHETIC_MODEL = "shunk031/aesthetics-predictor-v1-vit-base-patch32"
AESTHETIC_THRESHOLD = 6.0 
TOP_K_PER_CLUSTER = 3 
RELEVANCE_THRESHOLD = 6 

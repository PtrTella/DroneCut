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

# Stage 1: Proxy & Chronological Detection
PROXY_RES = "854:480"
PROXY_FPS = 1 
CLIP_MODEL = "openai/clip-vit-base-patch32"
SEMANTIC_CUT_THRESHOLD = 0.85  # Sotto questo valore di similarità tra frame(t) e frame(t-1), genera un taglio.

# Stage 2: Stability Audit (OpenCV - Fast Center-Sample)
STABILITY_THRESHOLD = 1.5 
MIN_SCENE_DURATION = 2.0       # Secondi. Scarta la clip se la zona stabile è più corta di questo valore.
TARGET_CENTER_DURATION = 3.0   # Quanti secondi estrarre dal centro
LONG_SCENE_THRESHOLD = 4.0     # Soglia oltre la quale si applica il taglio centrale
MAX_CHAOS_MAGNITUDE = 12.0     # Soglia di tolleranza al mosso (picco)
MAX_JITTER_THRESHOLD = 3.0      # Soglia di tolleranza agli scatti (jitter)

# Stage 3: Aesthetic Scoring (CLIP-Aesthetic)
AESTHETIC_MODEL = "shunk031/aesthetics-predictor-v1-vit-base-patch32"
# Note: AESTHETIC_MIN_SCORE removed. We no longer discard clips automatically based on score.

# Stage 4: Project Management
PROJECT_FILE = os.path.join(OUTPUT_DIR, "project.dcproj")

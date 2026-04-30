import os

# --- Percorsi di Sistema macOS ---
USER_HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(USER_HOME, "Library", "Caches", "DroneCut")
MOVIES_DIR = os.path.join(USER_HOME, "Movies", "DroneCut")

# --- Nuova Struttura Progetti ---
PROJECTS_DIR = os.path.join(CACHE_DIR, "Projects")

# Creazione cartelle base
for d in [CACHE_DIR, MOVIES_DIR, PROJECTS_DIR]:
    os.makedirs(d, exist_ok=True)

# --- Configurazione FFmpeg ---
FFMPEG_PATHS = ["ffmpeg", "/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]
def get_ffmpeg_path():
    for p in FFMPEG_PATHS:
        if os.system(f"command -v {p} >/dev/null 2>&1") == 0: return p
    return "ffmpeg"
FFMPEG_BIN = get_ffmpeg_path()

# --- Configurazione Pipeline ---
OUTPUT_DIR = os.path.join(MOVIES_DIR, "Exports")
DEBUG_DIR = os.path.join(CACHE_DIR, "Debug")

for d in [OUTPUT_DIR, DEBUG_DIR]:
    os.makedirs(d, exist_ok=True)

# Debug & UI
DEBUG_MODE = False 

# Stage 1: Proxy & Analysis Settings
PROXY_RES = "854:480"
STABILITY_FPS = 10.0             
HEATMAP_FPS = 2.0                
MIN_HERO_SCORE = 4.5             
MIN_PEAK_DISTANCE_SEC = 5.0      
EXPANSION_BUFFER_SEC = 4.0       
MIN_SCENE_DURATION = 2.0         
SEMANTIC_MERGE_THRESHOLD = 0.88  
EXP_SEMANTIC_MAX = 0.85          
EXP_SEMANTIC_MIN = 0.75          

# --- Optical Flow Thresholds ---
MAX_CHAOS_MAGNITUDE = 12.0       
MAX_JITTER_THRESHOLD = 3.0       

# Stage 3: Aesthetic Scoring (CLIP-Aesthetic)
AESTHETIC_MODEL = "shunk031/aesthetics-predictor-v1-vit-base-patch32"

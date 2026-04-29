import os

# --- Percorsi di Sistema macOS ---
USER_HOME = os.path.expanduser("~")
APP_DATA_DIR = os.path.join(USER_HOME, "Library", "Application Support", "DroneCut")
CACHE_DIR = os.path.join(USER_HOME, "Library", "Caches", "DroneCut")
MOVIES_DIR = os.path.join(USER_HOME, "Movies", "DroneCut")

# Creazione cartelle se non esistono
for d in [APP_DATA_DIR, CACHE_DIR, MOVIES_DIR]:
    os.makedirs(d, exist_ok=True)

# --- Configurazione FFmpeg ---
# Fallback per macOS se non è nel PATH (utile per app compilate)
FFMPEG_PATHS = [
    "ffmpeg", # Se è nel PATH
    "/opt/homebrew/bin/ffmpeg", # Homebrew Apple Silicon
    "/usr/local/bin/ffmpeg",    # Homebrew Intel
]

def get_ffmpeg_path():
    for p in FFMPEG_PATHS:
        if os.system(f"command -v {p} >/dev/null 2>&1") == 0:
            return p
    return "ffmpeg" # Default fallback

FFMPEG_BIN = get_ffmpeg_path()

# --- Configurazione Pipeline ---
OUTPUT_DIR = os.path.join(MOVIES_DIR, "Exports")
DEBUG_DIR = os.path.join(CACHE_DIR, "Debug")
PROXY_DIR = os.path.join(CACHE_DIR, "Proxies")

for d in [OUTPUT_DIR, DEBUG_DIR, PROXY_DIR]:
    os.makedirs(d, exist_ok=True)

# Debug & UI
DEBUG_MODE = True 

# Stage 1: Proxy & Chronological Detection
PROXY_RES = "854:480"
# --- V5 Heatmap Peak & Expand Settings ---
STABILITY_FPS = 10.0             # FPS del proxy per l'analisi di stabilità (veloce)
HEATMAP_FPS = 2.0                # Risoluzione temporale della mappa estetica
MIN_HERO_SCORE = 4.5             # Punteggio estetico minimo per considerare un frame come "Hero"
MIN_PEAK_DISTANCE_SEC = 5.0      # Distanza minima tra due Hero Frames (Default GUI)
EXPANSION_BUFFER_SEC = 4.0       # Quanti secondi analizzare prima e dopo l'Hero Frame
MIN_SCENE_DURATION = 2.0         # Se l'espansione stabile dura meno di così, scarta la clip
SEMANTIC_MERGE_THRESHOLD = 0.88  # Soglia per unire clip sovrapposte (stesso soggetto)
EXP_SEMANTIC_MAX = 0.85          # Soglia severa (drone fermo/lento)
EXP_SEMANTIC_MIN = 0.75          # Soglia permissiva (drone in corsa/pan)

# --- Optical Flow Thresholds ---
MAX_CHAOS_MAGNITUDE = 12.0       # Stop espansione: movimento troppo rapido
MAX_JITTER_THRESHOLD = 3.0       # Stop espansione: movimento a scatti / tremolio

# Stage 3: Aesthetic Scoring (CLIP-Aesthetic)
AESTHETIC_MODEL = "shunk031/aesthetics-predictor-v1-vit-base-patch32"

# Stage 4: Project Management
PROJECT_FILE = os.path.join(APP_DATA_DIR, "last_project.dcproj")

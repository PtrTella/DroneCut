from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import shutil
import logging
import traceback
import tkinter as tk
from tkinter import filedialog
from dronecut.core.pipeline import DroneCutPipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="DroneCut API")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared state (in-memory for now)
class State:
    def __init__(self):
        self.analyzed_scenes = []
        self.pipeline_config = {}
        self.is_processing = False

state = State()

class AnalyzeRequest(BaseModel):
    video_paths: List[str]
    music_path: Optional[str] = None
    prompts: List[str] = []
    negative_prompts: List[str] = []
    speed: float = 1.5
    threshold: float = 20.0
    max_scenes: int = 40
    min_duration: float = 1.5
    max_duration: Optional[float] = None
    out_dir: str = "gui_output"

class ExportRequest(BaseModel):
    scene_ids: List[int]
    out_dir: str = "gui_output"
    music_path: Optional[str] = None

import platform
import subprocess

@app.get("/pick-files")
async def pick_files():
    if platform.system() == "Darwin":
        try:
            # Use AppleScript for better focus on macOS
            script = 'choose file with prompt "Seleziona Video" of type {"public.movie", "com.apple.quicktime-movie", "public.mpeg-4"} with multiple selections allowed'
            cmd = ["osascript", "-e", f"set theFiles to {script}", "-e", 'set out to ""', "-e", 'repeat with aFile in theFiles', "-e", 'set out to out & POSIX path of aFile & "\n"', "-e", 'end repeat', "-e", 'out']
            result = subprocess.run(cmd, capture_output=True, text=True)
            files = [f.strip() for f in result.stdout.split("\n") if f.strip()]
            return {"files": files}
        except Exception as e:
            logger.error(f"AppleScript picker error: {e}")
            return {"files": []}
    
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        files = filedialog.askopenfilenames(title="Seleziona Video", filetypes=[("Video files", "*.mp4 *.mov *.avi *.mkv")])
        root.destroy()
        return {"files": list(files)}
    except Exception as e:
        logger.error(f"File picker error: {e}")
        return {"files": []}

@app.get("/pick-file")
async def pick_file():
    if platform.system() == "Darwin":
        try:
            script = 'POSIX path of (choose file with prompt "Seleziona File")'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            file = result.stdout.strip()
            return {"file": file}
        except Exception as e:
            logger.error(f"AppleScript picker error: {e}")
            return {"file": ""}

    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        root.lift()
        root.focus_force()
        file = filedialog.askopenfilename(title="Seleziona File", filetypes=[("Audio/Video files", "*.mp4 *.mov *.mp3 *.wav")])
        root.destroy()
        return {"file": file}
    except Exception as e:
        logger.error(f"File picker error: {e}")
        return {"file": ""}

# Pre-create and mount the default previews directory at startup
os.makedirs("gui_output/previews", exist_ok=True)
app.mount("/previews", StaticFiles(directory="gui_output/previews"), name="previews")

@app.get("/session")
async def get_session(out_dir: str = "gui_output"):
    metadata_path = os.path.join(out_dir, "metadata.json")
    if os.path.exists(metadata_path):
        import json
        with open(metadata_path, "r") as f:
            scenes = json.load(f)
        
        # Force chronological sort by ID
        scenes.sort(key=lambda x: x["id"])
        
        # Re-sync in-memory state for export
        state.analyzed_scenes = scenes
        
        response_scenes = []
        for s in scenes:
            s_out = s.copy()
            # Update preview URLs to be relative to the current server
            s_out["preview_url"] = f"http://localhost:8000/previews/{os.path.basename(s['preview_url'])}"
            response_scenes.append(s_out)
        return {"scenes": response_scenes}
    return {"scenes": []}

@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    state.is_processing = True
    try:
        logger.info(f"Starting analysis for {req.video_paths}")
        pipeline = DroneCutPipeline(
            prompts=req.prompts,
            negative_prompts=req.negative_prompts,
            speed=req.speed,
            threshold=req.threshold,
            max_scenes=req.max_scenes,
            min_scene_duration=req.min_duration,
            max_duration=req.max_duration,
            music_path=req.music_path
        )
        # Store config for export
        state.pipeline_config = req.model_dump()
        
        scenes = pipeline.analyze(req.video_paths, req.out_dir, save_session=True)
        
        # Keep real paths in state, but return relative URLs to frontend
        state.analyzed_scenes = [s.copy() for s in scenes]
        
        response_scenes = []
        for s in scenes:
            s_out = s.copy()
            s_out["preview_url"] = f"http://localhost:8000/previews/{os.path.basename(s['preview_url'])}"
            if "embedding" in s_out: del s_out["embedding"]
            response_scenes.append(s_out)
            
        return {"scenes": response_scenes}
    except Exception as e:
        logger.error(f"Error during analysis: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        state.is_processing = False

@app.post("/export")
async def export(req: ExportRequest):
    if not state.analyzed_scenes:
        raise HTTPException(status_code=400, detail="No scenes analyzed yet")
        
    # Reconstruct selected scenes in order
    selected = []
    scene_map = {s["id"]: s for s in state.analyzed_scenes}
    for sid in req.scene_ids:
        if sid in scene_map:
            selected.append(scene_map[sid])
            
    try:
        pipeline = DroneCutPipeline(
            prompts=state.pipeline_config.get("prompts"),
            negative_prompts=state.pipeline_config.get("negative_prompts"),
            speed=state.pipeline_config.get("speed", 1.5),
            music_path=req.music_path or state.pipeline_config.get("music_path")
        )
        final_path = pipeline.export(selected, req.out_dir)
        return {"message": "Export complete", "path": os.path.abspath(final_path)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Serve frontend static files
app.mount("/static", StaticFiles(directory="dronecut_gui/static"), name="static")

@app.get("/")
async def read_index():
    from fastapi.responses import FileResponse
    return FileResponse("dronecut_gui/static/index.html")

# Serve preview files
@app.get("/status")
async def get_status():
    return {"is_processing": state.is_processing}

if __name__ == "__main__":
    import uvicorn
    # Make sure static directory exists
    os.makedirs("dronecut_gui/static", exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)

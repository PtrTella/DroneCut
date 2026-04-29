import os
import threading
import json
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

from src.pipeline import DroneCutPipeline
from src.ui.views.home_view import HomeView
from src.ui.views.config_view import ConfigView
from src.ui.views.loading_view import LoadingView
from src.ui.views.gallery_view import GalleryView

class DroneCutPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DroneCut Pro 🚁")
        self.geometry("1200x950")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_view = None
        self.pipeline = DroneCutPipeline(progress_callback=self.on_pipeline_progress)
        self.active_player = None 
        
        self.project_name = "Progetto Senza Titolo"
        self.video_path = None
        self.results = []
        self.gui_params = {}

        self.show_home()

    def clear_view(self):
        if self.current_view:
            self.current_view.destroy()

    def show_home(self):
        self.clear_view()
        self.current_view = HomeView(self)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_config(self, video_path):
        self.clear_view()
        self.video_path = video_path
        self.current_view = ConfigView(self, video_path)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_loading(self, gui_params):
        self.clear_view()
        self.gui_params = gui_params
        self.current_view = LoadingView(self)
        self.current_view.grid(row=0, column=0, sticky="nsew")
        
        thread = threading.Thread(target=self._run_pipeline, args=(self.video_path, self.gui_params))
        thread.daemon = True
        thread.start()

    def show_gallery(self, results):
        self.clear_view()
        self.results = sorted(results, key=lambda x: x.get("start_sec", 0))
        self.current_view = GalleryView(self, self.results)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def on_pipeline_progress(self, status, progress):
        if isinstance(self.current_view, LoadingView):
            self.after(0, self.current_view.update_progress, status, progress)

    def _run_pipeline(self, video_path, params):
        try:
            results = self.pipeline.run(video_path, gui_params=params)
            self.after(0, self.show_gallery, results)
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Errore AI", f"Si è verificato un errore: {e}"))
            self.after(0, self.show_home)

    def load_project(self, project_path):
        try:
            with open(project_path, "r") as f:
                data = json.load(f)
            self.results = data.get("timeline", [])
            self.video_path = data.get("video_path")
            self.project_name = os.path.basename(project_path).replace(".dcproj", "")
            self.show_gallery(self.results)
        except Exception as e:
            messagebox.showerror("Errore Caricamento", f"Impossibile caricare il progetto: {e}")

    def save_project(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(defaultextension=".dcproj", filetypes=[("DroneCut Project", "*.dcproj")])
        if path:
            if isinstance(self.current_view, GalleryView):
                self.results = self.current_view.get_updated_results()
            data = {
                "video_path": self.video_path,
                "timeline": self.results
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Salvataggio", "Progetto salvato con successo!")

import os
import threading
import json
import shutil
import datetime
import logging
from tkinter import messagebox, filedialog
import customtkinter as ctk

from src.pipeline import DroneCutPipeline
from src.ui.views.home_view import HomeView
from src.ui.views.config_view import ConfigView
from src.ui.views.loading_view import LoadingView
from src.ui.views.gallery_view import GalleryView
from src.config import PROJECTS_DIR
from src.utils import generate_video_fingerprint

class TkinterLogHandler(logging.Handler):
    def __init__(self, write_func):
        super().__init__()
        self.write_func = write_func

    def emit(self, record):
        try:
            msg = self.format(record)
            # If the original message had \r, ensure it stays at the very front
            if isinstance(record.msg, str) and record.msg.startswith("\r"):
                msg = "\r" + msg.replace("\r", "")
            self.write_func(msg)
        except Exception:
            self.handleError(record)

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
        
        self.video_path = None
        self.video_fingerprint = None
        self.project_dir = None
        self.project_name = None
        self.results = []
        self.gui_params = {}

        self.show_home()

    def clear_view(self):
        if self.current_view:
            self.current_view.destroy()

    def show_home(self):
        self.clear_view()
        self.video_path = None
        self.video_fingerprint = None
        self.project_dir = None
        self.project_name = None
        self.results = []
        self.current_view = HomeView(self)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def list_library_projects(self):
        if not os.path.exists(PROJECTS_DIR): return []
        projects = []
        for name in os.listdir(PROJECTS_DIR):
            path = os.path.join(PROJECTS_DIR, name)
            if os.path.isdir(path) and os.path.exists(os.path.join(path, "config.dcproj")):
                projects.append(name)
        return sorted(projects, reverse=True)

    def delete_project(self, name):
        path = os.path.join(PROJECTS_DIR, name)
        if os.path.exists(path):
            if messagebox.askyesno("Elimina Progetto", f"Eliminare definitivamente '{name}'?"):
                shutil.rmtree(path)
                self.show_home()

    def load_library_project(self, name):
        project_path = os.path.join(PROJECTS_DIR, name)
        manifest_path = os.path.join(project_path, "config.dcproj")
        
        # 🛡️ Integrity Check: verify if critical analysis files exist
        required_files = ["heatmap.json", "stability.json"]
        is_corrupted = False
        for f in required_files:
            if not os.path.exists(os.path.join(project_path, f)):
                is_corrupted = True
                break
        
        if is_corrupted:
            orig_video = "Percorso non disponibile"
            try:
                if os.path.exists(manifest_path):
                    with open(manifest_path, "r") as f:
                        data = json.load(f)
                        orig_video = data.get("video_source", "Percorso non trovato")
            except Exception: pass

            msg = (f"Il progetto '{name}' risulta incompleto o corrotto.\n\n"
                   f"Video originale associato:\n{orig_video}\n\n"
                   "Vuoi eliminarlo definitivamente dalla libreria?")
            
            if messagebox.askyesno("Progetto Corrotto", msg):
                shutil.rmtree(project_path)
                self.show_home()
            return

        self.project_dir = project_path
        self.project_name = name
        self._load_project_file(manifest_path)

    def _load_project_file(self, project_path):
        try:
            with open(project_path, "r") as f:
                data = json.load(f)
            orig_path = data.get("video_source")
            self.video_fingerprint = data.get("video_fingerprint")
            self.results = data.get("timeline", [])
            
            if not orig_path or not os.path.exists(orig_path):
                messagebox.showwarning("Media Missing", f"Seleziona file per '{self.project_name}'.")
                new_path = filedialog.askopenfilename(title="Relink Video", filetypes=[("Video", "*.mp4 *.mov *.mkv")])
                if not new_path: return
                
                # 🕵️‍♂️ Verify Fingerprint on Relink
                if self.video_fingerprint:
                    new_fp = generate_video_fingerprint(new_path)
                    if new_fp != self.video_fingerprint:
                        if not messagebox.askyesno("Mismatch", "La firma digitale del file non corrisponde all'originale.\nVuoi ricollegarlo comunque?"):
                            return
                
                orig_path = new_path
                data["video_source"] = orig_path
                with open(project_path, "w") as f: json.dump(data, f, indent=2)
            self.video_path = orig_path
            self._ensure_proxy_and_open_gallery()
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile caricare: {e}")

    def show_config(self, video_path):
        # 🕵️‍♂️ SMART MATCH: Check if this video was already analyzed
        self.video_path = video_path
        self.video_fingerprint = generate_video_fingerprint(video_path)
        
        existing_project = self._find_project_by_fingerprint(self.video_fingerprint)
        if existing_project:
            if messagebox.askyesno("Video già analizzato", 
                                   f"Questo video è già presente nella libreria nel progetto:\n'{existing_project}'\n\nVuoi aprire l'analisi esistente invece di rifarla?"):
                self.load_library_project(existing_project)
                return

        if not self.project_dir:
            default_name = os.path.basename(video_path).split(".")[0]
            dialog = ctk.CTkInputDialog(
                text=f"Inserisci il nome del progetto:\n(Default: {default_name})", 
                title="Nuovo Progetto"
            )
            input_name = dialog.get_input()
            
            if input_name is None: return # Cancelled
            
            # Use default if empty
            input_name = input_name.strip() or default_name
            
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M")
            self.project_name = f"{input_name}_{ts}"
            self.project_dir = os.path.join(PROJECTS_DIR, self.project_name)
            os.makedirs(self.project_dir, exist_ok=True)
            self._auto_save_project()
        
        self.clear_view()
        self.current_view = ConfigView(self, video_path)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def _find_project_by_fingerprint(self, fingerprint):
        """Scans the library to find a project with the same video signature.
           Ignores corrupted projects.
        """
        if not fingerprint: return None
        for p_name in self.list_library_projects():
            try:
                project_path = os.path.join(PROJECTS_DIR, p_name)
                # Quick integrity check
                if not os.path.exists(os.path.join(project_path, "heatmap.json")) or \
                   not os.path.exists(os.path.join(project_path, "stability.json")):
                    continue

                path = os.path.join(project_path, "config.dcproj")
                with open(path, "r") as f:
                    data = json.load(f)
                    if data.get("video_fingerprint") == fingerprint:
                        return p_name
            except Exception: continue
        return None

    def show_config_back(self):
        if self.video_path:
            self.clear_view()
            self.current_view = ConfigView(self, self.video_path)
            self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_loading(self, gui_params):
        self.clear_view()
        self.gui_params = gui_params
        self.current_view = LoadingView(self)
        self.current_view.grid(row=0, column=0, sticky="nsew")
        
        # Setup Log Redirect
        self.log_handler = TkinterLogHandler(lambda m: self.after(0, self.current_view.write_log, m))
        self.log_handler.setFormatter(logging.Formatter('%(name)s: %(message)s'))
        self.log_handler.setLevel(logging.INFO)
        
        # Attach to root and sub-loggers to be sure
        logging.getLogger().addHandler(self.log_handler)
        logging.getLogger("DroneCutPipeline").addHandler(self.log_handler)
        
        thread = threading.Thread(target=self._run_pipeline, args=(self.video_path, self.gui_params))
        thread.daemon = True
        thread.start()

    def _run_pipeline(self, video_path, params):
        try:
            params["export_high_res"] = False
            results = self.pipeline.run(video_path, gui_params=params, project_dir=self.project_dir)
            self.results = results
            self._auto_save_project()
            
            # Remove Log Redirect before switching view
            logging.getLogger().removeHandler(self.log_handler)
            logging.getLogger("DroneCutPipeline").removeHandler(self.log_handler)
            
            self.after(0, self.show_gallery, results)
        except Exception as e:
            if hasattr(self, 'log_handler'):
                logging.getLogger().removeHandler(self.log_handler)
                logging.getLogger("DroneCutPipeline").removeHandler(self.log_handler)
            self.after(0, lambda: messagebox.showerror("Errore AI", f"Si è verificato un errore: {e}"))
            self.after(0, self.show_home)

    def export_clips(self, selected_scenes):
        """Export individual mp4 files."""
        if not selected_scenes: return
        threading.Thread(target=self._run_export, args=("clips", selected_scenes), daemon=True).start()

    def export_montage(self, selected_scenes):
        """Export single joined mp4 file."""
        if not selected_scenes: return
        threading.Thread(target=self._run_export, args=("montage", selected_scenes), daemon=True).start()

    def _run_export(self, mode, scenes):
        try:
            from src.director import Director
            d = Director()
            if mode == "clips":
                out = d.export_individual_clips(self.video_path, scenes, self.project_name)
                self.after(0, lambda: messagebox.showinfo("Export", f"Clip esportate in:\n{out}"))
            else:
                out = d.export_full_montage(self.video_path, scenes, self.project_name)
                self.after(0, lambda: messagebox.showinfo("Export", f"Montaggio completato:\n{out}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Errore Export", str(e)))

    def _auto_save_project(self):
        if not self.project_dir: return
        path = os.path.join(self.project_dir, "config.dcproj")
        data = {
            "video_source": self.video_path, 
            "video_fingerprint": self.video_fingerprint,
            "timeline": self.results
        }
        with open(path, "w") as f: json.dump(data, f, indent=2)

    def save_project(self):
        if isinstance(self.current_view, GalleryView):
            self.results = self.current_view.get_updated_results()
        self._auto_save_project()
        messagebox.showinfo("Salvataggio", "Progetto salvato in libreria!")

    def show_gallery(self, results):
        self.clear_view()
        self.results = sorted(results, key=lambda x: x.get("start_sec", 0))
        self.current_view = GalleryView(self, self.results)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def on_pipeline_progress(self, status, progress):
        if isinstance(self.current_view, LoadingView):
            self.after(0, self.current_view.update_progress, status, progress)
            self.after(0, self.current_view.write_log, f"*** STADIO: {status.upper()} ***")

    def _ensure_proxy_and_open_gallery(self):
        from src.proxy import generate_proxy
        self.clear_view()
        loading = LoadingView(self)
        loading.grid(row=0, column=0, sticky="nsew")
        loading.update_progress("Controllo Proxy...", 0.5)
        def check_task():
            proxy_path = generate_proxy(self.video_path, output_dir=self.project_dir)
            for res in self.results: res["proxy_path"] = proxy_path
            self.after(0, self.show_gallery, self.results)
        threading.Thread(target=check_task, daemon=True).start()

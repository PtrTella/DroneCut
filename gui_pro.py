import os
import sys

# --- Stability Fixes for macOS / Threads ---
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["QT_MAC_WANTS_LAYER"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import multiprocessing
try:
    if multiprocessing.get_start_method(allow_none=True) is None:
        multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass

import matplotlib
matplotlib.use('Agg') # Force non-interactive backend to avoid GUI thread conflicts
# -------------------------------------------

import threading
import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
from src.pipeline import DroneCutPipeline
import subprocess

# Appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class DroneCutPro(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DroneCut Pro 🚁")
        self.geometry("1100x800")
        
        # Grid config
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.current_view = None
        self.pipeline = DroneCutPipeline(progress_callback=self.on_pipeline_progress)
        self.active_player = None # Store reference to current playing ClipCard
        
        # Project Data
        self.project_name = "Progetto Senza Titolo"
        self.video_path = None
        self.results = []

        self.show_home()

    def clear_view(self):
        if self.current_view:
            self.current_view.destroy()

    def show_home(self):
        self.clear_view()
        self.current_view = HomeView(self)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def show_loading(self, video_path):
        self.clear_view()
        self.video_path = video_path
        self.current_view = LoadingView(self)
        self.current_view.grid(row=0, column=0, sticky="nsew")
        
        # Start Pipeline
        thread = threading.Thread(target=self._run_pipeline, args=(video_path,))
        thread.daemon = True
        thread.start()

    def show_gallery(self, results):
        self.clear_view()
        # Ordine Cronologico (dal primo all'ultimo secondo)
        self.results = sorted(results, key=lambda x: x.get("start_sec", 0))
        self.current_view = GalleryView(self, self.results)
        self.current_view.grid(row=0, column=0, sticky="nsew")

    def on_pipeline_progress(self, status, progress):
        if isinstance(self.current_view, LoadingView):
            self.after(0, self.current_view.update_progress, status, progress)

    def _run_pipeline(self, video_path):
        try:
            results = self.pipeline.run(video_path)
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
        path = filedialog.asksaveasfilename(defaultextension=".dcproj", filetypes=[("DroneCut Project", "*.dcproj")])
        if path:
            # Sync results with checkbox states if we were in Gallery
            if isinstance(self.current_view, GalleryView):
                self.results = self.current_view.get_updated_results()

            data = {
                "video_path": self.video_path,
                "timeline": self.results
            }
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Salvataggio", "Progetto salvato con successo!")

class HomeView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        # Center container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = ctk.CTkLabel(self.container, text="DroneCut Pro", font=ctk.CTkFont(size=48, weight="bold"))
        self.title_label.pack(pady=(0, 10))

        self.subtitle = ctk.CTkLabel(self.container, text="L'intelligenza artificiale al servizio del tuo montaggio cinematografico", font=ctk.CTkFont(size=18))
        self.subtitle.pack(pady=(0, 40))

        self.new_btn = ctk.CTkButton(self.container, text="✨ Nuovo Progetto AI", font=ctk.CTkFont(size=16, weight="bold"), height=50, width=250, command=self.on_new)
        self.new_btn.pack(pady=10)

        self.load_btn = ctk.CTkButton(self.container, text="📂 Carica Progetto", font=ctk.CTkFont(size=16), height=50, width=250, fg_color="#333333", hover_color="#444444", command=self.on_load)
        self.load_btn.pack(pady=10)

    def on_new(self):
        file = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv")])
        if file:
            self.master.show_loading(file)

    def on_load(self):
        file = filedialog.askopenfilename(filetypes=[("DroneCut Project", "*.dcproj")])
        if file:
            self.master.load_project(file)

class LoadingView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")

        self.status_label = ctk.CTkLabel(self.container, text="Analisi Video in Corso...", font=ctk.CTkFont(size=24, weight="bold"))
        self.status_label.pack(pady=(0, 20))

        self.progress_bar = ctk.CTkProgressBar(self.container, width=400)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.detail_label = ctk.CTkLabel(self.container, text="Inizializzazione dei modelli AI...", font=ctk.CTkFont(size=14))
        self.detail_label.pack()

    def update_progress(self, status, progress):
        self.detail_label.configure(text=status)
        self.progress_bar.set(progress)

class GalleryView(ctk.CTkFrame):
    def __init__(self, master, results):
        super().__init__(master, fg_color="transparent")
        self.master = master
        self.cards = []
        
        # Header
        self.header = ctk.CTkFrame(self, height=80, corner_radius=0)
        self.header.pack(fill="x", side="top")
        
        self.title_label = ctk.CTkLabel(self.header, text=f"Progetto: {master.project_name}", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(side="left", padx=20)

        self.export_btn = ctk.CTkButton(self.header, text="🎬 Esporta Selezionate", fg_color="#1f538d", font=ctk.CTkFont(weight="bold"), command=self.on_export)
        self.export_btn.pack(side="right", padx=20)

        self.save_btn = ctk.CTkButton(self.header, text="💾 Salva", width=100, fg_color="#333333", command=master.save_project)
        self.save_btn.pack(side="right", padx=10)

        # Scrollable area
        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Populate
        for res in results:
            card = ClipCard(self.scroll_frame, res, master.video_path, app=master)
            card.pack(fill="x", pady=10, padx=5)
            self.cards.append(card)
            
            # Abilita scrolling su tutti i figli (Fix per macOS Two-Finger Scroll)
            self._bind_mouse_wheel(card)

    def _bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mouse_wheel)
        for child in widget.winfo_children():
            self._bind_mouse_wheel(child)

    def _on_mouse_wheel(self, event):
        self.scroll_frame._parent_canvas.yview_scroll(int(-1 * (event.delta)), "units")

    def get_updated_results(self):
        updated = []
        for card in self.cards:
            res = card.data.copy()
            res["export"] = card.export_check.get()
            updated.append(res)
        return updated

    def on_export(self):
        approved = [card.data for card in self.cards if card.export_check.get()]
        if not approved:
            messagebox.showwarning("Export", "Nessuna clip selezionata per l'esportazione!")
            return
        
        self.export_btn.configure(state="disabled", text="⏳ Esportazione...")
        threading.Thread(target=self._run_export, args=(approved,), daemon=True).start()

    def _run_export(self, clips):
        try:
            # We reuse the director's export logic but only for selected clips
            from src.director import Director
            director = Director()
            director.export_timeline(self.master.video_path, clips)
            
            output_path = os.path.abspath("data/output/timeline")
            self.after(0, lambda: messagebox.showinfo("Export Completato", f"Le clip sono state salvate in:\n{output_path}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Errore Export", str(e)))
        finally:
            self.after(0, lambda: self.export_btn.configure(state="normal", text="🎬 Esporta Selezionate"))

class ClipCard(ctk.CTkFrame):
    def __init__(self, master, data, video_path, app):
        super().__init__(master, border_width=1, border_color="#333333")
        self.data = data
        self.video_path = video_path
        self.app = app
        self.playing = False
        self.cap = None
        self._after_id = None

        # Hover effects
        self.bind("<Enter>", lambda e: self.configure(border_color="#1f538d", border_width=2))
        self.bind("<Leave>", lambda e: self.configure(border_color="#333333", border_width=1))

        # Grid layout for card
        self.grid_columnconfigure(1, weight=1)

        # Thumbnail / Player
        self.preview_label = ctk.CTkLabel(self, text="", width=320, height=180, fg_color="black", corner_radius=8)
        self.preview_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        
        self.load_thumbnail()

        # Text Area
        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, sticky="nw", padx=10, pady=10)
        
        title = data.get("title", f"Scena {data.get('id')}")
        score = data.get("aesthetic_score", 0)
        self.title_label = ctk.CTkLabel(self.info_frame, text=f"{title} (Score: {score:.2f})", font=ctk.CTkFont(size=16, weight="bold"), wraplength=400, justify="left")
        self.title_label.pack(anchor="w")

        duration = data.get('duration', data['end_sec'] - data['start_sec'])
        self.time_label = ctk.CTkLabel(self.info_frame, text=f"⏳ {duration:.1f} sec  ({data['start_sec']:.1f}s - {data['end_sec']:.1f}s)", font=ctk.CTkFont(size=12))
        self.time_label.pack(anchor="w")

        # Controls
        self.ctrl_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.ctrl_frame.grid(row=1, column=1, sticky="sw", padx=10, pady=10)

        self.play_btn = ctk.CTkButton(self.ctrl_frame, text="▶️ Play", width=100, command=self.toggle_play)
        self.play_btn.pack(side="left")

        self.export_check = ctk.CTkCheckBox(self.ctrl_frame, text="Includi nell'Export")
        self.export_check.select()
        self.export_check.pack(side="left", padx=20)

    def load_thumbnail(self):
        path = self.data.get("thumbnail")
        if path and os.path.exists(path):
            img = Image.open(path)
            img = img.resize((320, 180), Image.Resampling.LANCZOS)
            self.ctk_img = ctk.CTkImage(img, size=(320, 180))
            self.preview_label.configure(image=self.ctk_img)
        else:
            self.preview_label.configure(text="No Thumbnail")

    def toggle_play(self):
        if self.playing:
            self.stop_playback()
        else:
            # Global stop if another is playing
            if self.app.active_player:
                self.app.active_player.stop_playback()
            
            self.start_playback()

    def start_playback(self):
        self.playing = True
        self.play_btn.configure(text="⏹ Stop", fg_color="#a12c2c", hover_color="#c23b3b")
        self.app.active_player = self
        
        # OpenCV Setup
        self.cap = cv2.VideoCapture(self.video_path)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, self.data['start_sec'] * 1000)
        self._stream_frame()

    def _stream_frame(self):
        if not self.playing or not self.cap:
            return

        ret, frame = self.cap.read()
        curr_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        
        if not ret or curr_ms > (self.data['end_sec'] * 1000):
            self.stop_playback()
            return

        # Convert to TK Image
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame)
        img = img.resize((320, 180), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(img) # CTkImage is too slow for real-time video in a loop? 
                                         # Let's try CTkImage first for consistency, if slow use ImageTk
        ctk_img = ctk.CTkImage(img, size=(320, 180))
        self.preview_label.configure(image=ctk_img)
        
        self._after_id = self.after(33, self._stream_frame)

    def stop_playback(self):
        self.playing = False
        if self._after_id:
            self.after_cancel(self._after_id)
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.play_btn.configure(text="▶️ Play", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#367E96", "#145161"])
        self.load_thumbnail()
        if self.app.active_player == self:
            self.app.active_player = None

if __name__ == "__main__":
    app = DroneCutPro()
    app.mainloop()

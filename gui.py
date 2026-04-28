import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image
from src.pipeline import DroneCutPipeline
import subprocess

class DroneCutGUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("DroneCut 🚁")
        self.geometry("800x700")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1) # Scrollable frame row

        # Initialize Backend
        self.pipeline = DroneCutPipeline(progress_callback=self.update_progress_callback)
        self.selected_video = None
        self.thumbnails = [] # Keep references to avoid GC

        # --- 1. Header ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="DroneCut 🚁", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack()
        
        self.subtitle_label = ctk.CTkLabel(self.header_frame, text="AI-Powered Automated Drone Video Editor", font=ctk.CTkFont(size=14))
        self.subtitle_label.pack()

        # --- 2. Input Section ---
        self.input_frame = ctk.CTkFrame(self)
        self.input_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.select_button = ctk.CTkButton(self.input_frame, text="Seleziona Video Sorgente", command=self.select_file)
        self.select_button.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")

        self.file_label = ctk.CTkLabel(self.input_frame, text="Nessun file selezionato", font=ctk.CTkFont(slant="italic"))
        self.file_label.grid(row=1, column=0, padx=20, pady=(0, 10))

        self.theme_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Ricerca Tematica Opzionale (es. 'auto d'epoca', 'montagna scoscesa')...")
        self.theme_entry.grid(row=2, column=0, padx=20, pady=10, sticky="ew")

        self.run_button = ctk.CTkButton(self.input_frame, text="Inizia Analisi", command=self.start_analysis, state="disabled", fg_color="#1f538d")
        self.run_button.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        # --- 3. Monitoring Section ---
        self.monitor_frame = ctk.CTkFrame(self)
        # Hidden by default
        
        self.status_label = ctk.CTkLabel(self.monitor_frame, text="In attesa...", font=ctk.CTkFont(size=13))
        self.status_label.pack(pady=(10, 5))

        self.progress_bar = ctk.CTkProgressBar(self.monitor_frame)
        self.progress_bar.pack(padx=20, pady=(0, 10), fill="x")
        self.progress_bar.set(0)

        # --- 4. Results Gallery ---
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Clip Selezionate dall'AI")
        # Hidden by default

        # --- 5. Footer ---
        self.footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.footer_frame.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        
        self.export_button = ctk.CTkButton(self.footer_frame, text="Apri Cartella Output", command=self.open_output, state="disabled")
        self.export_button.pack(side="right")

    def select_file(self):
        filetypes = (
            ('Video files', '*.mp4 *.mov *.mkv'),
            ('All files', '*.*')
        )
        filename = filedialog.askopenfilename(title='Seleziona Video', filetypes=filetypes)
        if filename:
            self.selected_video = filename
            self.file_label.configure(text=os.path.basename(filename))
            self.run_button.configure(state="normal")

    def update_progress_callback(self, status_text, progress_float):
        # Thread-safe update using .after()
        self.after(0, self._update_ui_progress, status_text, progress_float)

    def _update_ui_progress(self, status_text, progress_float):
        self.status_label.configure(text=status_text)
        self.progress_bar.set(progress_float)

    def start_analysis(self):
        if not self.selected_video:
            return

        # Prepare UI
        self.run_button.configure(state="disabled")
        self.select_button.configure(state="disabled")
        self.theme_entry.configure(state="disabled")
        
        self.monitor_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        self.results_frame.grid_forget() # Hide previous results if any
        
        # Clear previous results
        for widget in self.results_frame.winfo_children():
            widget.destroy()

        # Start thread
        theme = self.theme_entry.get()
        thread = threading.Thread(target=self.run_pipeline_thread, args=(self.selected_video, theme))
        thread.daemon = True
        thread.start()

    def run_pipeline_thread(self, video_path, theme):
        try:
            results = self.pipeline.run(video_path, theme)
            self.after(0, self.display_results, results)
        except Exception as e:
            self.after(0, self.handle_error, str(e))

    def handle_error(self, error_msg):
        messagebox.showerror("Errore Pipeline", f"Si è verificato un errore durante l'elaborazione:\n\n{error_msg}")
        self.reset_ui()

    def reset_ui(self):
        self.run_button.configure(state="normal")
        self.select_button.configure(state="normal")
        self.theme_entry.configure(state="normal")
        self.monitor_frame.grid_forget()

    def display_results(self, results):
        self.reset_ui()
        
        if not results:
            messagebox.showinfo("Fine Analisi", "Nessuna clip ha superato i criteri di selezione.")
            return

        self.results_frame.grid(row=3, column=0, padx=20, pady=10, sticky="nsew")
        self.export_button.configure(state="normal")
        self.thumbnails = [] # Clear old references

        for i, res in enumerate(results):
            clip_frame = ctk.CTkFrame(self.results_frame)
            clip_frame.pack(fill="x", padx=10, pady=5)
            
            # Thumbnail
            try:
                img = Image.open(res["thumbnail_path"])
                # Resize to fit
                img.thumbnail((200, 120))
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(200, 120))
                self.thumbnails.append(ctk_img)
                
                img_label = ctk.CTkLabel(clip_frame, image=ctk_img, text="")
                img_label.pack(side="left", padx=10, pady=10)
            except Exception as e:
                print(f"Error loading thumbnail: {e}")
                placeholder = ctk.CTkLabel(clip_frame, text="IMG Error", width=200, height=120, fg_color="gray")
                placeholder.pack(side="left", padx=10, pady=10)

            # Info
            info_frame = ctk.CTkFrame(clip_frame, fg_color="transparent")
            info_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            cap_label = ctk.CTkLabel(info_frame, text=f"Clip #{i+1}: {res['caption']}", font=ctk.CTkFont(weight="bold"), wraplength=400, justify="left")
            cap_label.pack(anchor="w")
            
            time_label = ctk.CTkLabel(info_frame, text=f"Durata: {res['start']:.1f}s - {res['end']:.1f}s ({res['end']-res['start']:.1f}s)", font=ctk.CTkFont(size=12))
            time_label.pack(anchor="w")

    def open_output(self):
        output_dir = os.path.abspath("data/output/timeline")
        if os.path.exists(output_dir):
            if os.name == 'nt': # Windows
                os.startfile(output_dir)
            elif os.name == 'posix': # macOS / Linux
                subprocess.run(['open', output_dir] if os.uname().sysname == 'Darwin' else ['xdg-open', output_dir])
        else:
            messagebox.showwarning("Attenzione", "La cartella di output non esiste ancora.")

if __name__ == "__main__":
    app = DroneCutGUI()
    app.mainloop()

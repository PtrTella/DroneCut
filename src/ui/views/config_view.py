import tkinter as tk
import customtkinter as ctk
from src.ui.widgets.range_slider import RangeSlider
from src.config import MAX_CHAOS_MAGNITUDE, MAX_JITTER_THRESHOLD

class ConfigView(ctk.CTkFrame):
    def __init__(self, master, video_path):
        super().__init__(master, fg_color="transparent")
        self.video_path = video_path
        
        self.container = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=15)
        self.container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.8, relheight=0.9)
        
        ctk.CTkLabel(self.container, text="Configurazione AI Pro", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=20)
        
        self.scroll_form = ctk.CTkScrollableFrame(self.container, fg_color="transparent")
        self.scroll_form.pack(fill="both", expand=True, padx=40)
        
        # --- AESTHETICS ---
        ctk.CTkLabel(self.scroll_form, text="ESTETICA E RILEVAMENTO", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1f538d").pack(pady=(10, 5), anchor="w")
        self.add_param("Soglia Estetica (Hero Score)", "min_hero_score", 4.5, 3.0, 8.0)
        self.add_param("Distanza Minima tra Hero Frames (Sec)", "min_peak_distance", 5.0, 1.0, 15.0)
        
        # --- EXPANSION ---
        ctk.CTkLabel(self.scroll_form, text="ESPANSIONE E STABILITÀ", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1f538d").pack(pady=(20, 5), anchor="w")
        self.add_param("Expansion Buffer (Sec max per lato)", "expansion_buffer", 4.0, 1.0, 10.0)
        self.add_param("Durata Minima Clip (Sec)", "min_scene_duration", 2.0, 0.5, 5.0)
        self.add_param("Max Chaos Magnitude (Velocità)", "max_chaos", MAX_CHAOS_MAGNITUDE, 5.0, 30.0)
        self.add_param("Max Jitter Threshold (Scatti)", "max_jitter", MAX_JITTER_THRESHOLD, 1.0, 10.0)
        
        # --- SEMANTICS ---
        ctk.CTkLabel(self.scroll_form, text="SEMANTICA E FUSIONE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1f538d").pack(pady=(20, 5), anchor="w")
        self.semantic_range = RangeSlider(self.scroll_form, "Semantic Expansion Range (Motion - Hovering)", 0.50, 0.98, 0.75, 0.85)
        self.semantic_range.pack(fill="x", pady=10)
        self.add_param("Soglia di Fusione (Merging)", "merge_threshold", 0.88, 0.70, 0.98)
        
        # --- OPTIONS ---
        ctk.CTkLabel(self.scroll_form, text="OPZIONI ESPORTAZIONE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1f538d").pack(pady=(20, 5), anchor="w")
        self.export_var = tk.BooleanVar(value=True)
        self.export_check = ctk.CTkCheckBox(self.scroll_form, text="Esporta automaticamente clip Full-Res (FFmpeg)", variable=self.export_var, font=ctk.CTkFont(size=14))
        self.export_check.pack(pady=10, anchor="w")
        
        # Start Button
        self.start_btn = ctk.CTkButton(self.container, text="LANCIA PIPELINE V5.2 🚀", height=60, font=ctk.CTkFont(size=18, weight="bold"), command=self.on_start)
        self.start_btn.pack(pady=25, padx=40, fill="x")

    def add_param(self, label, key, default, min_v, max_v):
        frame = ctk.CTkFrame(self.scroll_form, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        lbl = ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=13))
        lbl.pack(side="left")
        val_lbl = ctk.CTkLabel(frame, text=str(default), font=ctk.CTkFont(size=13, weight="bold"), width=50)
        val_lbl.pack(side="right")
        slider = ctk.CTkSlider(frame, from_=min_v, to=max_v, number_of_steps=100, command=lambda v: val_lbl.configure(text=f"{v:.2f}"))
        slider.set(default)
        slider.pack(side="right", padx=15, fill="x", expand=True)
        if not hasattr(self, "param_widgets"): self.param_widgets = {}
        self.param_widgets[key] = slider

    def on_start(self):
        params = {k: w.get() for k, w in self.param_widgets.items()}
        s_min, s_max = self.semantic_range.get()
        params["exp_semantic_min"] = s_min
        params["exp_semantic_max"] = s_max
        params["export_high_res"] = self.export_var.get()
        self.master.show_loading(params)

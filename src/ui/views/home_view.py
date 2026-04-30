import os
import customtkinter as ctk
from tkinter import filedialog

class HomeView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.master = master

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header = ctk.CTkFrame(self, fg_color="transparent", height=200)
        self.header.grid(row=0, column=0, sticky="nsew", padx=40, pady=(60, 20))
        
        self.title = ctk.CTkLabel(self.header, text="DroneCut Pro", font=ctk.CTkFont(size=48, weight="bold"))
        self.title.pack()
        
        self.subtitle = ctk.CTkLabel(self.header, text="AI-Powered Cinematic Video Editor", font=ctk.CTkFont(size=18))
        self.subtitle.pack(pady=10)

        # Main Action Area
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=1, column=0, sticky="nsew", padx=40)
        self.main_area.grid_columnconfigure(0, weight=1)
        self.main_area.grid_columnconfigure(1, weight=1)

        # Left Column: New Project
        self.new_proj_frame = ctk.CTkFrame(self.main_area, corner_radius=15, border_width=2, border_color="#1f538d")
        self.new_proj_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.new_label = ctk.CTkLabel(self.new_proj_frame, text="✨ Nuovo Progetto AI", font=ctk.CTkFont(size=24, weight="bold"))
        self.new_label.pack(pady=(30, 10))
        
        self.new_desc = ctk.CTkLabel(self.new_proj_frame, text="Carica un video e lascia che l'AI trovi\ni momenti migliori per te.", font=ctk.CTkFont(size=14))
        self.new_desc.pack(pady=10)

        self.btn_new = ctk.CTkButton(self.new_proj_frame, text="Seleziona Video", 
                                   command=self.on_new, height=50, font=ctk.CTkFont(size=16, weight="bold"))
        self.btn_new.pack(pady=40, padx=40, fill="x")

        # Right Column: Project Library
        self.lib_frame = ctk.CTkFrame(self.main_area, corner_radius=15)
        self.lib_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.lib_label = ctk.CTkLabel(self.lib_frame, text="📂 Libreria Progetti", font=ctk.CTkFont(size=24, weight="bold"))
        self.lib_label.pack(pady=(30, 10))
        
        self.scroll_lib = ctk.CTkScrollableFrame(self.lib_frame, fg_color="transparent")
        self.scroll_lib.pack(expand=True, fill="both", padx=20, pady=10)

        self.refresh_library()

    def refresh_library(self):
        """Populates the library list."""
        for widget in self.scroll_lib.winfo_children():
            widget.destroy()

        projects = self.master.list_library_projects()
        if not projects:
            empty_lbl = ctk.CTkLabel(self.scroll_lib, text="Nessun progetto salvato.", font=ctk.CTkFont(slant="italic"))
            empty_lbl.pack(pady=40)
            return

        for name in projects:
            row = ctk.CTkFrame(self.scroll_lib, fg_color="#2b2b2b", corner_radius=8)
            row.pack(fill="x", pady=5, padx=5)
            
            p_name = name if len(name) < 30 else name[:27] + "..."
            lbl = ctk.CTkLabel(row, text=p_name, font=ctk.CTkFont(size=13))
            lbl.pack(side="left", padx=15, pady=10)
            
            btn_del = ctk.CTkButton(row, text="🗑", width=40, fg_color="#a12c2c", hover_color="#c23b3b",
                                  command=lambda n=name: self.master.delete_project(n))
            btn_del.pack(side="right", padx=5)

            btn_open = ctk.CTkButton(row, text="Apri", width=60, fg_color="#1f538d",
                                   command=lambda n=name: self.master.load_library_project(n))
            btn_open.pack(side="right", padx=5)

    def on_new(self):
        file = filedialog.askopenfilename(
            title="Seleziona Video Drone",
            filetypes=[("Video Files", "*.mp4 *.mov *.mkv *.avi")]
        )
        if file:
            self.master.show_config(file)

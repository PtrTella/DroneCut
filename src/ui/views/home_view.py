import customtkinter as ctk
import os

class HomeView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.master = master

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Center Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0)

        # Logo / Title
        self.title_label = ctk.CTkLabel(self.container, text="DroneCut Pro 🚁", font=ctk.CTkFont(size=32, weight="bold"))
        self.title_label.pack(pady=(0, 10))
        
        self.subtitle_label = ctk.CTkLabel(self.container, text="Editor Intelligente per footage Drone", font=ctk.CTkFont(size=14), text_color="gray")
        self.subtitle_label.pack(pady=(0, 40))

        # Main Button
        self.new_proj_btn = ctk.CTkButton(self.container, text="🚀 Nuova Analisi Video AI", height=60, width=300, font=ctk.CTkFont(size=16, weight="bold"), command=self.on_new_project)
        self.new_proj_btn.pack(pady=10)

        # Library Label
        self.lib_label = ctk.CTkLabel(self.container, text="Libreria Progetti", font=ctk.CTkFont(size=18, weight="bold"))
        self.lib_label.pack(pady=(40, 10))

        # Projects Scrollable Frame
        self.scroll_frame = ctk.CTkScrollableFrame(self.container, width=500, height=350, fg_color="#1a1a1a")
        self.scroll_frame.pack(pady=10)

        self.load_projects()

    def load_projects(self):
        projects = self.master.list_library_projects()
        
        if not projects:
            ctk.CTkLabel(self.scroll_frame, text="Nessun progetto salvato", text_color="gray").pack(pady=20)
            return

        for p_name in projects:
            self.add_project_item(p_name)

    def add_project_item(self, p_name):
        item_frame = ctk.CTkFrame(self.scroll_frame, fg_color="#2b2b2b", height=70)
        item_frame.pack(fill="x", pady=5, padx=5)
        item_frame.pack_propagate(False)

        # Parsing Name and Date (expected format: Name_YYYYMMDD_HHMM)
        display_name = p_name
        display_date = "Data non disponibile"
        
        parts = p_name.rsplit("_", 2)
        if len(parts) >= 3:
            display_name = parts[0]
            date_str = parts[1]
            time_str = parts[2]
            # Format YYYYMMDD to DD/MM/YYYY
            if len(date_str) == 8:
                display_date = f"{date_str[6:8]}/{date_str[4:6]}/{date_str[0:4]} {time_str[0:2]}:{time_str[2:4]}"

        # Text Container (Left)
        text_container = ctk.CTkFrame(item_frame, fg_color="transparent")
        text_container.pack(side="left", padx=15, pady=10)

        name_label = ctk.CTkLabel(text_container, text=display_name, font=ctk.CTkFont(size=15, weight="bold"), anchor="w")
        name_label.pack(fill="x")

        date_label = ctk.CTkLabel(text_container, text=display_date, font=ctk.CTkFont(size=11), text_color="#888888", anchor="w")
        date_label.pack(fill="x")

        # Action Buttons (Right)
        btn_container = ctk.CTkFrame(item_frame, fg_color="transparent")
        btn_container.pack(side="right", padx=10)

        open_btn = ctk.CTkButton(btn_container, text="Apri", width=60, height=28, fg_color="#1f538d", command=lambda p=p_name: self.master.load_library_project(p))
        open_btn.pack(side="left", padx=5)

        del_btn = ctk.CTkButton(btn_container, text="🗑", width=30, height=28, fg_color="#a12d2d", hover_color="#7a2222", command=lambda p=p_name: self.master.delete_project(p))
        del_btn.pack(side="left", padx=5)

    def on_new_project(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(title="Seleziona Video Drone", filetypes=[("Video", "*.mp4 *.mov *.mkv")])
        if path:
            self.master.show_config(path)

import customtkinter as ctk
from tkinter import filedialog

class HomeView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")

        self.title_label = ctk.CTkLabel(self.container, text="DroneCut Pro", font=ctk.CTkFont(size=56, weight="bold"))
        self.title_label.pack(pady=(0, 10))

        self.subtitle = ctk.CTkLabel(self.container, text="Aesthetic-First Automated Drone Editing", font=ctk.CTkFont(size=18), text_color="gray")
        self.subtitle.pack(pady=(0, 50))

        self.new_btn = ctk.CTkButton(self.container, text="✨ Nuovo Progetto AI", font=ctk.CTkFont(size=16, weight="bold"), height=55, width=300, command=self.on_new)
        self.new_btn.pack(pady=10)

        self.load_btn = ctk.CTkButton(self.container, text="📂 Carica Progetto", font=ctk.CTkFont(size=16), height=55, width=300, fg_color="#333333", hover_color="#444444", command=self.on_load)
        self.load_btn.pack(pady=10)

    def on_new(self):
        file = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mov *.mkv")])
        if file:
            self.master.show_config(file)

    def on_load(self):
        file = filedialog.askopenfilename(filetypes=[("DroneCut Project", "*.dcproj")])
        if file:
            self.master.load_project(file)

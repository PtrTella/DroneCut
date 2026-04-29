import customtkinter as ctk

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

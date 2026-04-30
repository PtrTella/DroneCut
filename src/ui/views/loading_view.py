import customtkinter as ctk

class LoadingView(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color="transparent")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Center Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0)

        self.title_label = ctk.CTkLabel(self.container, text="Analisi Video AI in corso...", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(pady=20)

        self.progress_bar = ctk.CTkProgressBar(self.container, width=500)
        self.progress_bar.pack(pady=10)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.container, text="Inizializzazione...", font=ctk.CTkFont(size=14))
        self.status_label.pack(pady=10)

        # 💻 Technical Log Console (Bottom)
        self.log_container = ctk.CTkFrame(self, height=180, fg_color="#1a1a1a", corner_radius=10)
        self.log_container.grid(row=1, column=0, sticky="ew", padx=40, pady=(0, 40))
        self.log_container.grid_propagate(False)
        
        self.console_label = ctk.CTkLabel(self.log_container, text="TECHNICAL LOGS", font=ctk.CTkFont(size=10, weight="bold"), text_color="#555555")
        self.console_label.pack(pady=(5, 0))

        self.log_box = ctk.CTkTextbox(self.log_container, fg_color="transparent", font=ctk.CTkFont(family="Courier", size=11), text_color="#aaaaaa", wrap="none")
        self.log_box.pack(expand=True, fill="both", padx=10, pady=5)
        self.log_box.configure(state="disabled")

    def update_progress(self, status, progress):
        self.status_label.configure(text=status)
        self.progress_bar.set(progress)

    def write_log(self, message):
        """Append a new log message or overwrite if it starts with \r."""
        self.log_box.configure(state="normal")
        
        if message.startswith("\r"):
            # Delete the last line before inserting new one
            # Check if there is content to delete (more than 1 line)
            current_content = self.log_box.get("1.0", "end-1c")
            if current_content.strip():
                self.log_box.delete("end-2l", "end-1l")
            message = message[1:] # Remove the \r
            prefix = "> "
        else:
            prefix = "> "

        self.log_box.insert("end", f"{prefix}{message}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

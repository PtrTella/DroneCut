import os
import cv2
import customtkinter as ctk
from PIL import Image, ImageTk

class ClipCard(ctk.CTkFrame):
    def __init__(self, master, data, video_path, app):
        super().__init__(master, border_width=1, border_color="#333333")
        self.data = data
        self.video_path = video_path
        self.app = app
        self.playing = False
        self.cap = None
        self._after_id = None

        self.bind("<Enter>", lambda e: self.configure(border_color="#1f538d", border_width=2))
        self.bind("<Leave>", lambda e: self.configure(border_color="#333333", border_width=1))

        self.grid_columnconfigure(1, weight=1)
        self.preview_label = ctk.CTkLabel(self, text="", width=320, height=180, fg_color="black", corner_radius=8)
        self.preview_label.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        self.load_thumbnail()

        self.info_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, sticky="nw", padx=10, pady=10)
        
        title = data.get("title", f"Scena {data.get('id')}")
        score = data.get("aesthetic_score", 0)
        self.title_label = ctk.CTkLabel(self.info_frame, text=f"{title} (Score: {score:.2f})", font=ctk.CTkFont(size=16, weight="bold"))
        self.title_label.pack(anchor="w")

        duration = data.get('duration', 0)
        self.time_label = ctk.CTkLabel(self.info_frame, text=f"⏳ {duration:.1f}s | {data['start_sec']:.1f}s → {data['end_sec']:.1f}s", font=ctk.CTkFont(size=12))
        self.time_label.pack(anchor="w")

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
            img = Image.open(path).resize((320, 180), Image.Resampling.LANCZOS)
            self.ctk_img = ctk.CTkImage(img, size=(320, 180))
            self.preview_label.configure(image=self.ctk_img)
        else:
            self.preview_label.configure(text="No Preview")

    def toggle_play(self):
        if self.playing: self.stop_playback()
        else:
            if self.app.active_player: self.app.active_player.stop_playback()
            self.start_playback()

    def start_playback(self):
        self.playing = True
        self.play_btn.configure(text="⏹ Stop", fg_color="#a12c2c")
        self.app.active_player = self
        self.cap = cv2.VideoCapture(self.video_path)
        self.cap.set(cv2.CAP_PROP_POS_MSEC, self.data['start_sec'] * 1000)
        self._stream_frame()

    def _stream_frame(self):
        if not self.playing or not self.cap: return
        ret, frame = self.cap.read()
        curr_ms = self.cap.get(cv2.CAP_PROP_POS_MSEC)
        if not ret or curr_ms > (self.data['end_sec'] * 1000):
            self.stop_playback()
            return
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame).resize((320, 180), Image.Resampling.LANCZOS)
        ctk_img = ctk.CTkImage(img, size=(320, 180))
        self.preview_label.configure(image=ctk_img)
        self._after_id = self.after(33, self._stream_frame)

    def stop_playback(self):
        self.playing = False
        if self._after_id: self.after_cancel(self._after_id)
        if self.cap: self.cap.release(); self.cap = None
        self.play_btn.configure(text="▶️ Play", fg_color=["#3B8ED0", "#1F6AA5"])
        self.load_thumbnail()
        if self.app.active_player == self: self.app.active_player = None

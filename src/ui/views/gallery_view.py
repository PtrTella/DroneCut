import customtkinter as ctk
import os
from src.ui.widgets.clip_card import ClipCard

class GalleryView(ctk.CTkFrame):
    def __init__(self, master, results):
        super().__init__(master, fg_color="transparent")
        self.master = master
        self.cards = []
        
        self.header = ctk.CTkFrame(self, height=80, corner_radius=0)
        self.header.pack(fill="x", side="top")
        
        self.title_label = ctk.CTkLabel(self.header, text=f"Timeline DroneCut: {len(results)} clip rilevate", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(side="left", padx=20)

        # BUTTONS AREA
        self.btn_area = ctk.CTkFrame(self.header, fg_color="transparent")
        self.btn_area.pack(side="right", padx=10)

        self.home_btn = ctk.CTkButton(self.btn_area, text="🏠 Home", width=80, fg_color="#444444", command=master.show_home)
        self.home_btn.pack(side="right", padx=5)

        self.save_btn = ctk.CTkButton(self.btn_area, text="💾 Salva", width=80, fg_color="#333333", command=master.save_project)
        self.save_btn.pack(side="right", padx=5)

        self.config_btn = ctk.CTkButton(self.btn_area, text="⚙️ Parametri", width=100, fg_color="#333333", command=master.show_config_back)
        self.config_btn.pack(side="right", padx=5)

        # THE TWO EXPORT BUTTONS
        self.export_montage_btn = ctk.CTkButton(self.btn_area, text="🎞️ Esporta Montage", fg_color="#285e3a", hover_color="#214d30", font=ctk.CTkFont(weight="bold"), command=self.on_export_montage)
        self.export_montage_btn.pack(side="right", padx=5)

        self.export_clips_btn = ctk.CTkButton(self.btn_area, text="🎬 Esporta Clip", fg_color="#1f538d", font=ctk.CTkFont(weight="bold"), command=self.on_export_clips)
        self.export_clips_btn.pack(side="right", padx=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        for res in results:
            card = ClipCard(self.scroll_frame, res, master.video_path, app=master)
            card.pack(fill="x", pady=10, padx=5)
            self.cards.append(card)
            self._bind_mouse_wheel(card)

    def get_selected_scenes(self):
        """Returns the data list of checked clips."""
        return [card.data for card in self.cards if card.export_check.get()]

    def on_export_clips(self):
        selected = self.get_selected_scenes()
        if not selected:
            tk_messagebox.showwarning("Export", "Seleziona almeno una clip!")
            return
        self.master.export_clips(selected)

    def on_export_montage(self):
        selected = self.get_selected_scenes()
        if not selected:
            return
        self.master.export_montage(selected)

    def get_updated_results(self):
        """Used for saving the project with checkboxes preserved."""
        # Note: we should probably store the checkbox state in data if we want it persistent
        return [card.data for card in self.cards]

    def _bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mousewheel)
        for child in widget.winfo_children():
            self._bind_mouse_wheel(child)

    def _on_mousewheel(self, event):
        self.scroll_frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

import os
import threading
from tkinter import messagebox
import customtkinter as ctk
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

        self.export_btn = ctk.CTkButton(self.header, text="🎬 Esporta Selezionate", fg_color="#1f538d", font=ctk.CTkFont(weight="bold"), command=self.on_export)
        self.export_btn.pack(side="right", padx=20)

        self.save_btn = ctk.CTkButton(self.header, text="💾 Salva Progetto", width=130, fg_color="#333333", command=master.save_project)
        self.save_btn.pack(side="right", padx=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        for res in results:
            card = ClipCard(self.scroll_frame, res, master.video_path, app=master)
            card.pack(fill="x", pady=10, padx=5)
            self.cards.append(card)
            self._bind_mouse_wheel(card)

    def _bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mouse_wheel)
        for child in widget.winfo_children(): self._bind_mouse_wheel(child)

    def _on_mouse_wheel(self, event):
        self.scroll_frame._parent_canvas.yview_scroll(int(-1 * (event.delta)), "units")

    def get_updated_results(self):
        return [dict(card.data, export=card.export_check.get()) for card in self.cards]

    def on_export(self):
        approved = [card.data for card in self.cards if card.export_check.get()]
        if not approved:
            messagebox.showwarning("Export", "Nessuna clip selezionata!")
            return
        self.export_btn.configure(state="disabled", text="⏳ Esportazione...")
        threading.Thread(target=self._run_export, args=(approved,), daemon=True).start()

    def _run_export(self, clips):
        try:
            from src.director import Director
            director = Director()
            director.export_timeline(self.master.video_path, clips)
            output_path = os.path.abspath("data/output/timeline")
            self.after(0, lambda: messagebox.showinfo("Export Completato", f"Clip salvate in:\n{output_path}"))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Errore Export", str(e)))
        finally:
            self.after(0, lambda: self.export_btn.configure(state="normal", text="🎬 Esporta Selezionate"))

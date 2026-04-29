import tkinter as tk
import customtkinter as ctk

class RangeSlider(ctk.CTkFrame):
    """
    Custom Premium Range Slider for dual values (Min/Max)
    """
    def __init__(self, master, label, min_val, max_val, start_min, start_max, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.min_limit = min_val
        self.max_limit = max_val
        self.current_min = start_min
        self.current_max = start_max
        
        lbl_frame = ctk.CTkFrame(self, fg_color="transparent")
        lbl_frame.pack(fill="x")
        
        ctk.CTkLabel(lbl_frame, text=label, font=ctk.CTkFont(size=13)).pack(side="left")
        self.val_label = ctk.CTkLabel(lbl_frame, text=f"{start_min:.2f} - {start_max:.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#1f538d")
        self.val_label.pack(side="right")
        
        self.canvas = tk.Canvas(self, height=20, bg="#2b2b2b", highlightthickness=0, bd=0)
        self.canvas.pack(fill="x", pady=5, padx=5)
        
        self.canvas.bind("<Configure>", self._render_canvas)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-1>", self._on_click)
        
        self.active_handle = None

    def _val_to_pos(self, val):
        width = self.canvas.winfo_width() - 20
        if width <= 0: return 10
        return 10 + (val - self.min_limit) / (self.max_limit - self.min_limit) * width

    def _pos_to_val(self, pos):
        width = self.canvas.winfo_width() - 20
        if width <= 0: return self.min_limit
        val = self.min_limit + (pos - 10) / width * (self.max_limit - self.min_limit)
        return max(self.min_limit, min(self.max_limit, val))

    def _render_canvas(self, event=None):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 0: return
        
        # Background Track
        self._create_rounded_rect_on_canvas(10, h/2-2, w-10, h/2+2, radius=2, fill="#3d3d3d", outline="")
        
        # Active Range
        x_min = self._val_to_pos(self.current_min)
        x_max = self._val_to_pos(self.current_max)
        self.canvas.create_rectangle(x_min, h/2-3, x_max, h/2+3, fill="#1f538d", outline="")
        
        # Handles
        self.canvas.create_oval(x_min-8, h/2-8, x_min+8, h/2+8, fill="#ffffff", outline="#1f538d", width=2, tags="min")
        self.canvas.create_oval(x_max-8, h/2-8, x_max+8, h/2+8, fill="#ffffff", outline="#1f538d", width=2, tags="max")

    def _create_rounded_rect_on_canvas(self, x1, y1, x2, y2, radius=5, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def _on_click(self, event):
        x_min = self._val_to_pos(self.current_min)
        x_max = self._val_to_pos(self.current_max)
        if abs(event.x - x_min) < 15: self.active_handle = "min"
        elif abs(event.x - x_max) < 15: self.active_handle = "max"
        else: self.active_handle = None

    def _on_drag(self, event):
        if not self.active_handle: return
        val = self._pos_to_val(event.x)
        if self.active_handle == "min":
            self.current_min = min(val, self.current_max - 0.01)
        else:
            self.current_max = max(val, self.current_min + 0.01)
        self.val_label.configure(text=f"{self.current_min:.2f} - {self.current_max:.2f}")
        self._render_canvas()

    def get(self):
        return self.current_min, self.current_max

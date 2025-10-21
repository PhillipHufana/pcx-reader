import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

__all__ = ["Toolbar", "SidePanel", "ImageCanvas"]

UPSCALE = False  # default upscale behavior


class Toolbar(ttk.Frame):
    def __init__(self, master, controller, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.upscale_var = tk.BooleanVar(value=UPSCALE)
        self.zoom_label = None
        self._build()

    def _build(self):
        ttk.Button(self, text="Open (Ctrl+O)", command=self.controller.open_image).pack(side="left")
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Button(self, text="Fit to Window (Ctrl+0)", command=self.controller.set_fit).pack(side="left")
        ttk.Button(self, text="100% (Ctrl+1)", command=lambda: self.controller.set_zoom(1.0)).pack(side="left")
        ttk.Button(self, text="Zoom - (Ctrl+-)", command=lambda: self.controller.bump_zoom(0.9)).pack(side="left")
        ttk.Button(self, text="Zoom + (Ctrl+=)", command=lambda: self.controller.bump_zoom(1.1)).pack(side="left")

        ttk.Checkbutton(self, text="Allow Upscale", variable=self.upscale_var, command=self._on_upscale_toggle).pack(side="left", padx=(10, 0))
        ttk.Label(self, text="").pack(side="left", expand=True)
        self.zoom_label = ttk.Label(self, text="Zoom: 100%")
        self.zoom_label.pack(side="right")

    def _on_upscale_toggle(self):
        global UPSCALE
        UPSCALE = bool(self.upscale_var.get())
        if hasattr(self.controller, "redraw"):
            try:
                self.controller.redraw()
            except Exception:
                pass

    def set_zoom_text(self, zoom_float):
        try:
            pct = int(round(zoom_float * 100))
            self.zoom_label.config(text=f"Zoom: {pct}%")
        except Exception:
            self.zoom_label.config(text="Zoom: —")


class ScrollableFrame(ttk.Frame):
    def __init__(self, master, width=300, height=600, **kwargs):
        super().__init__(master, **kwargs)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.vbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vbar.set)

        self.vbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self._inner_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.config(width=width, height=height)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel()

    def _bind_mousewheel(self):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_inner_configure(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        canvas_width = event.width
        self.canvas.itemconfigure(self._inner_id, width=canvas_width)

    def _on_mousewheel(self, event):
        delta = int(-1 * (event.delta / 120)) if event.delta else 0
        if delta:
            self.canvas.yview_scroll(delta, "units")


class SidePanel(ttk.Frame):
    """
    Side panel with fixed-size preview and a scrollable metadata/palette area.
    """

    def __init__(self, master, controller, preview_size=(240, 160), panel_width=300, **kwargs):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.preview_size = preview_size
        self.panel_width = panel_width
        self._preview_photo_ref = None
        self.palette_visible = False
        self._build()

    def _build(self):
        self.scroll_frame = ScrollableFrame(self, width=self.panel_width, height=600)
        self.scroll_frame.pack(fill="both", expand=True)
        container = self.scroll_frame.inner

        ttk.Label(container, text="Preview", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 0))
        pw, ph = self.preview_size
        self.preview_canvas = tk.Canvas(container, width=pw, height=ph, bd=1, relief="solid", bg="#1b1b1b", highlightthickness=0)
        self.preview_canvas.grid(row=1, column=0, sticky="n", padx=8, pady=(6, 8))
        self._draw_preview_placeholder()

        self.meta_label = ttk.Label(container, text="", justify="left", wraplength=self.panel_width - 24)
        self.meta_label.grid(row=2, column=0, sticky="we", padx=8, pady=(0, 10))

        ttk.Button(container, text="Import Image", command=self.controller.open_image).grid(row=3, column=0, sticky="we", padx=8, pady=(0, 6))
        ttk.Button(container, text="Close Image (Ctrl+W)", command=self.controller.close_image).grid(row=4, column=0, sticky="we", padx=8, pady=(0, 10))

        ttk.Separator(container).grid(row=5, column=0, sticky="ew", padx=8, pady=6)

        self.pcx_header_label = ttk.Label(container, text="", justify="left", wraplength=self.panel_width - 24)
        self.pcx_header_label.grid(row=6, column=0, sticky="w", padx=8, pady=(0, 6))

        # Make this button a toggle
        self.palette_button = ttk.Button(container, text="No Color Palette Found", state="disabled", command=self._on_palette_toggle)
        self.palette_button.grid(row=7, column=0, sticky="we", padx=8, pady=(0, 8))

        # Inline palette preview (hidden until enabled)
        self.palette_preview_frame = ttk.Frame(container)
        self.palette_canvas = tk.Canvas(self.palette_preview_frame, width=self.preview_size[0], height=36, highlightthickness=0)
        self.palette_canvas.pack(fill="x", expand=True, padx=4, pady=(4, 0))
        self.palette_hint = ttk.Label(self.palette_preview_frame, text="", font=("", 9), foreground="#666")
        self.palette_hint.pack(anchor="w", padx=6, pady=(4, 4))
        self.palette_preview_frame.grid_forget()

        self.color_title = ttk.Label(container, text="Color (Eyedropper)", font=("Segoe UI", 10, "bold"))
        self.color_title.grid(row=9, column=0, sticky="w", padx=8, pady=(6, 0))

        self.color_panel = ttk.Frame(container)
        self.color_panel.grid(row=10, column=0, sticky="ew", padx=8, pady=(4, 0))
        self.swatch = tk.Label(self.color_panel, width=8, relief="groove", bg="#333")
        self.swatch.grid(row=0, column=0, rowspan=3, sticky="nsw", padx=(0, 8), pady=2)
        self.rgb_label = ttk.Label(self.color_panel, text="RGB: —")
        self.hex_label = ttk.Label(self.color_panel, text="HEX: —")
        self.hsv_label = ttk.Label(self.color_panel, text="HSV: —")
        self.xy_label = ttk.Label(self.color_panel, text="Pixel: —")
        self.rgb_label.grid(row=0, column=1, sticky="w")
        self.hex_label.grid(row=1, column=1, sticky="w")
        self.hsv_label.grid(row=2, column=1, sticky="w")
        self.xy_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self.copy_row = ttk.Frame(container)
        self.copy_row.grid(row=11, column=0, sticky="w", padx=8, pady=(6, 0))
        ttk.Button(self.copy_row, text="Copy HEX", command=self.controller.copy_hex).pack(side="left")
        ttk.Button(self.copy_row, text="Copy RGB", command=self.controller.copy_rgb).pack(side="left", padx=6)

        self.tip_label = ttk.Label(container, text="\nTip: Ctrl + Mouse Wheel to zoom", foreground="#666")
        self.tip_label.grid(row=12, column=0, sticky="w", padx=8, pady=(6, 12))

        container.columnconfigure(0, weight=1)

    def _draw_preview_placeholder(self):
        self.preview_canvas.delete("all")
        pw, ph = self.preview_size
        self.preview_canvas.create_rectangle(0, 0, pw, ph, fill="#1b1b1b", outline="#444")
        self.preview_canvas.create_text(pw // 2, ph // 2, text="No Preview", fill="#999", font=("Segoe UI", 10))

    def set_preview_image_from_pil(self, pil_image, allow_upscale=False):
        """
        Always display a scaled preview of pil_image. If pil_image is None, show placeholder.
        """
        if pil_image is None:
            self._preview_photo_ref = None
            self._draw_preview_placeholder()
            return

        pw, ph = self.preview_size
        iw, ih = pil_image.size

        scale = min(pw / iw, ph / ih)
        if scale > 1.0 and not (allow_upscale or getattr(self.controller, "allow_upscale", False)):
            scale = 1.0

        new_w = max(1, int(iw * scale))
        new_h = max(1, int(ih * scale))
        resized = pil_image.resize((new_w, new_h), Image.LANCZOS)
        photo = ImageTk.PhotoImage(resized)
        self._preview_photo_ref = photo
        self.preview_canvas.delete("all")
        self.preview_canvas.create_rectangle(0, 0, pw, ph, fill="#1b1b1b", outline="#444")
        cx = (pw - new_w) // 2
        cy = (ph - new_h) // 2
        self.preview_canvas.create_image(cx, cy, anchor="nw", image=photo)
        self.scroll_frame._on_inner_configure()

    def update_pcx_info(self, header_data):
        if header_data and "Error" not in header_data:
            lines = []
            for k, v in header_data.items():
                if k not in ("File Path", "File Size", "Is Indexed"):
                    lines.append(f"{k}: {v}")
            self.pcx_header_label.config(text="\n".join(lines))
        else:
            self.pcx_header_label.config(text="")

        is_indexed = bool(header_data and header_data.get("Is Indexed", False))
        has_palette = bool(getattr(self.controller, "img_state", None) and getattr(self.controller.img_state, "pcx_palette", None))
        if is_indexed and has_palette:
            self.palette_button.config(state="normal", text="Show PCX Color Palette")
            # default hidden until user toggles
            try:
                self.palette_canvas.delete("all")
                self.palette_hint.config(text="")
            except Exception:
                pass
        else:
            self.palette_button.config(state="disabled", text="No Color Palette Found")
            try:
                self.palette_canvas.delete("all")
                self.palette_hint.config(text="")
                self.palette_preview_frame.grid_forget()
                self.palette_visible = False
            except Exception:
                pass

        self.scroll_frame._on_inner_configure()

    def _render_palette_preview(self, palette):
        self.palette_canvas.delete("all")
        if not palette:
            return
        width = int(self.palette_canvas.winfo_reqwidth()) or self.preview_size[0]
        height = int(self.palette_canvas['height'])
        count = len(palette)
        if count <= 0:
            return
        sw = max(1, width // count)
        for i, c in enumerate(palette):
            try:
                r, g, b = c[:3]
                hexcol = f"#{r:02x}{g:02x}{b:02x}"
            except Exception:
                hexcol = "#000000"
            x0 = i * sw
            x1 = x0 + sw
            self.palette_canvas.create_rectangle(x0, 0, x1, height, fill=hexcol, outline="")

    def _on_palette_toggle(self):
        """Toggle palette visibility and call controller hooks if available."""
        if self.palette_visible:
            # hide
            self.palette_preview_frame.grid_forget()
            self.palette_button.config(text="Show PCX Color Palette")
            self.palette_visible = False
            if hasattr(self.controller, "hide_palette"):
                try:
                    self.controller.hide_palette()
                except Exception:
                    pass
        else:
            # show: render palette from controller.img_state if available
            palette = None
            if getattr(self.controller, "img_state", None):
                palette = getattr(self.controller.img_state, "pcx_palette", None)
            if palette:
                self._render_palette_preview(palette)
                self.palette_preview_frame.grid(row=8, column=0, sticky="we", padx=8, pady=(0, 10))
                self.palette_button.config(text="Hide PCX Color Palette")
                self.palette_visible = True
                if hasattr(self.controller, "show_palette"):
                    try:
                        self.controller.show_palette()
                    except Exception:
                        pass
            else:
                # nothing to show
                self.palette_preview_frame.grid_forget()
                self.palette_button.config(text="No Color Palette Found", state="disabled")
                self.palette_visible = False
        self.scroll_frame._on_inner_configure()

    def set_metadata_text(self, text):
        self.meta_label.config(text=text or "")
        self.scroll_frame._on_inner_configure()

    def set_color_info(self, rgb=None, hexval=None, hsv=None, xy=None):
        if rgb is not None:
            self.rgb_label.config(text=f"RGB: {rgb}")
        else:
            self.rgb_label.config(text="RGB: —")
        if hexval is not None:
            self.hex_label.config(text=f"HEX: {hexval}")
            try:
                self.swatch.config(bg=hexval)
            except Exception:
                pass
        else:
            self.hex_label.config(text="HEX: —")
        if hsv is not None:
            self.hsv_label.config(text=f"HSV: {hsv}")
        else:
            self.hsv_label.config(text="HSV: —")
        if xy is not None:
            self.xy_label.config(text=f"Pixel: {xy}")
        else:
            self.xy_label.config(text="Pixel: —")
        self.scroll_frame._on_inner_configure()


class ImageCanvas(tk.Canvas):
    """
    Canvas that displays the full image. Clicking on the image will automatically
    update the side-panel preview 
    """

    def __init__(self, master, controller, bg="#111", **kwargs):
        super().__init__(master, bg=bg, highlightthickness=0, cursor="crosshair", **kwargs)
        self.controller = controller

        # scrollbars remain children of the canvas's master (matching earlier layout)
        self.hbar = ttk.Scrollbar(master, orient="horizontal", command=self.xview)
        self.vbar = ttk.Scrollbar(master, orient="vertical", command=self.yview)
        self.configure(xscrollcommand=self.hbar.set, yscrollcommand=self.vbar.set)

        self.grid(row=0, column=0, sticky="nsew")
        self.vbar.grid(row=0, column=1, sticky="ns")
        self.hbar.grid(row=1, column=0, sticky="ew")
        master.rowconfigure(0, weight=1)
        master.columnconfigure(0, weight=1)

        self._photo_ref = None
        self._image_id = None
        self._pil_image = None  # store last PIL image shown

        # bind click on canvas to notify controller / side panel
        self.bind("<Button-1>", self._on_click)

    def set_image_from_pil(self, pil_image):
        """Display the PIL image at natural size (no scaling). If None, clear."""
        self._pil_image = pil_image
        if pil_image is None:
            try:
                self.delete("all")
            except Exception:
                pass
            self._photo_ref = None
            self.configure(scrollregion=(0, 0, 0, 0))
            return

        photo = ImageTk.PhotoImage(pil_image)
        self._photo_ref = photo

        if self._image_id:
            try:
                self.delete(self._image_id)
            except Exception:
                pass

        self._image_id = self.create_image(0, 0, anchor="nw", image=photo)
        self.configure(scrollregion=(0, 0, pil_image.width, pil_image.height))
        try:
            self.xview_moveto(0)
            self.yview_moveto(0)
        except Exception:
            pass

    def _on_click(self, event):
        x = int(self.canvasx(event.x))
        y = int(self.canvasy(event.y))

        handled = False
        if hasattr(self.controller, "on_image_click"):
            try:
                # controller may choose to accept x,y and update preview or other logic
                self.controller.on_image_click(x, y)
                handled = True
            except Exception:
                handled = False

        if not handled and getattr(self.controller, "side_panel", None) is not None:
            try:
                if self._pil_image is not None:
                    self.controller.side_panel.set_preview_image_from_pil(self._pil_image)
            except Exception:
                pass

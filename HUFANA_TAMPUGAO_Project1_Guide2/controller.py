import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk

from model import ImageState
from utils import rgb_to_hex, rgb_to_hsv_str
from ui_components import Toolbar, SidePanel, ImageCanvas
from pcx_reader import read_pcx_header, read_pcx_256_palette  # New import
from channel_panel import ChannelPanel
try:
    RESAMPLE = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE = Image.LANCZOS


# ---------------------- Controller (Main App) ----------------------
class ImageApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.img_state = ImageState()
        self.title("CMSC 162 - Image Viewer")

        # Try to maximize window
        try:
            if sys.platform.startswith("win"):
                self.state("zoomed")
            else:
                try:
                    self.attributes("-zoomed", True)
                except Exception:
                    pass
        except Exception:
            pass


        # --- Layout ---
        toolbar = Toolbar(self, self)
        toolbar.pack(side="top", fill="x", padx=8, pady=6)
        self.toolbar = toolbar

        # Create horizontal frame for image + sidebar
        hframe = ttk.Frame(self)
        hframe.pack(side="top", fill="both", expand=True)

        # --- Left area: image + bottom histograms ---
        vsplit = tk.PanedWindow(hframe, orient="vertical")
        vsplit.pack(side="left", fill="both", expand=True)

        # Top image area
        top_area = ttk.Frame(vsplit)
        self.canvas = ImageCanvas(top_area, self)
        vsplit.add(top_area, minsize=200)

        # Bottom histogram/channel panel
        self.channel_panel = ChannelPanel(vsplit, self)
        vsplit.add(self.channel_panel, minsize=200)

        # --- Right side panel (metadata, preview, etc.) ---
        self.side_panel = SidePanel(hframe, self)
        self.side_panel.pack(side="right", fill="y", padx=(4, 8), pady=8)


        # --- Status bar ---
        self.status = ttk.Label(self, text="Load an image to get started.")
        self.status.pack(side="bottom", fill="x")

        # Init key bindings
        self._init_bindings()

    # ------------------ Public Commands ------------------

    # open image file
    def open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.jpg *.jpeg *.png *.bmp *.tif *.tiff *.webp *.pcx"),
                ("PCX files", "*.pcx")
            ]
        )
        if not path:
            return

        # Reset file / PCX state before loading a new image
        self.img_state.pcx_header = None
        self.img_state.pcx_palette = None
        self.img_state.file_path = None
        self.img_state.file_format = None
        self.img_state.jpeg_exif = None
        self.side_panel.update_pcx_info(None)

        # Open image once to capture format & EXIF, then convert to RGB for display
        try:
            im0 = Image.open(path)
            # store basic file info
            self.img_state.file_path = path
            # PIL's .format may be None for some in-memory images; for files it's usually set
            self.img_state.file_format = im0.format

            # Try to extract EXIF for JPEGs (defensive)
            self.img_state.jpeg_exif = None
            try:
                if (self.img_state.file_format or "").upper() == "JPEG":
                    exif = im0.getexif()
                    if exif:
                        # map numeric tags to human-readable names
                        from PIL import ExifTags
                        tagmap = {ExifTags.TAGS.get(k, k): v for k, v in exif.items()}
                        self.img_state.jpeg_exif = tagmap
            except Exception:
                # keep jpeg_exif as None if extraction fails
                self.img_state.jpeg_exif = None

            # Convert to RGB for consistent display / eyedropper behavior
            img = im0.convert("RGB")

        except Exception as e:
            messagebox.showerror("Open Image", f"Failed to open image:\n{e}")
            return

        # --- PCX Specific Header & Palette Reading ---
        if path.lower().endswith('.pcx'):
            print(f"DEBUG: Reading PCX file: {path}")

            # Read and store header
            header_data = read_pcx_header(path)
            self.img_state.pcx_header = header_data

            # Read and store palette 
            palette_data = read_pcx_256_palette(path)
            self.img_state.pcx_palette = palette_data

            print(f"DEBUG: PCX Header Result: {header_data.get('Error', 'Success') if header_data else 'No Header'}")
            print(f"DEBUG: PCX Palette Found: {self.img_state.pcx_palette is not None}")

            # Update side panel with PCX header/palette availability
            self.side_panel.update_pcx_info(self.img_state.pcx_header)

            # Show the inline palette automatically if a palette is present
            if self.img_state.pcx_palette:
                
                try:
                    self.after(10, self.show_palette)
                except Exception:
                    self.show_palette()
        else:
            # Clear any previous PCX info if a non-PCX file is loaded
            self.side_panel.update_pcx_info(None)

        # Finalize state + UI updates
        self.img_state.img = img
        # also keep PIL image stored so ImageCanvas.set_image_from_pil can use it
        self.img_state.tk_img = None
        self.title(f"CMSC 162 - {path}")
        self.img_state.fit_to_window = True
        self.img_state.scale = 1.0

        # Ensure the main canvas gets the image and side-preview updates immediately
        try:
            self.canvas.set_image_from_pil(self.img_state.img)
        except Exception:
          
            pass

        self.update_preview()
        self.update_meta()  # Updates general metadata (size, mode, format, EXIF)
        self.redraw()

        self.channel_panel.show_channels(img)

        self.status.config(text=f"Loaded: {path}")

    def close_image(self):
        """Close current image and clear image + metadata state."""
        # Clear display image state
        self.img_state.img = None
        self.img_state.tk_img = None
        self.img_state.img_item = None
        self.img_state.disp_size = (0, 0)
        self.img_state.offset = (0, 0)
        self.img_state.pan_anchor = None
        self.img_state.scale = 1.0
        self.img_state.fit_to_window = True

        # Clear file & pcx metadata
        self.img_state.pcx_header = None
        self.img_state.pcx_palette = None
        self.img_state.file_path = None
        self.img_state.file_format = None
        self.img_state.jpeg_exif = None

        # Clear canvas and scrollregion
        try:
            self.canvas.delete("all")
            self.canvas.configure(scrollregion=(0, 0, 0, 0))
        except Exception:
            pass

        # Always clear inline palette 
        try:
            if hasattr(self.side_panel, "palette_canvas"):
                self.side_panel.palette_canvas.delete("all")
            if hasattr(self.side_panel, "palette_hint"):
                self.side_panel.palette_hint.config(text="")
            # hide palette frame if visible
            try:
                self.side_panel.palette_preview_frame.grid_forget()
                self.side_panel.palette_visible = False
                self.side_panel.palette_button.config(text="No Color Palette Found", state="disabled")
            except Exception:
                pass
        except Exception:
            pass

        # Reset preview & metadata panel
        try:
            # new SidePanel API
            self.side_panel.set_preview_image_from_pil(None)
        except Exception:
            pass
        try:
            self.side_panel.set_metadata_text("No image loaded.")
            self.side_panel.update_pcx_info(None)
        except Exception:
            pass

        # Reset toolbar/status
        try:
            self.toolbar.zoom_label.config(text="")
        except Exception:
            pass
        self.status.config(text="Closed image.")

    def show_palette(self):
        # Guard
        if not self.img_state.pcx_palette:
            messagebox.showinfo("Palette", "The loaded image does not have an external 256-color PCX palette.")
            return

        canvas = self.side_panel.palette_canvas
        canvas.delete("all")

        # Layout parameters
        cols = 16
        rows = 16
        # use the canvas width; fallback if 0
        pw = canvas.winfo_width() or int(canvas['width']) or 240
        pad = 2
        sw = max(6, (pw - pad * (cols + 1)) // cols)  # swatch size (min 6 px)
        needed_h = pad + rows * (sw + pad)
        canvas.config(height=needed_h)

        # Draw swatches and bind each tag to click
        for i, (r, g, b) in enumerate(self.img_state.pcx_palette[:256]):
            row = i // cols
            col = i % cols
            x = pad + col * (sw + pad)
            y = pad + row * (sw + pad)
            hex_color = rgb_to_hex(r, g, b)
            tag = f"sw{i}"
            # create rectangle and give it a unique tag
            canvas.create_rectangle(x, y, x + sw, y + sw, fill=hex_color, outline="#000", tags=(tag,))
            # bind click on tag to handler (capture index via default arg)
            canvas.tag_bind(tag, "<Button-1>", lambda e, idx=i: self._palette_clicked(idx))

        try:
            self.side_panel.palette_preview_frame.grid(row=8, column=0, sticky="we", padx=8, pady=(0, 10))
            self.side_panel.palette_visible = True
            self.side_panel.palette_button.config(text="Hide PCX Color Palette", state="normal")
            # update side layout
            try:
                self.side_panel.scroll_frame._on_inner_configure()
            except Exception:
                pass
        except Exception:
            pass

    def _palette_clicked(self, idx: int):
        """User clicked palette swatch index idx — apply and copy the color."""
        if not self.img_state.pcx_palette or idx < 0 or idx >= len(self.img_state.pcx_palette):
            return
        r, g, b = self.img_state.pcx_palette[idx]
        hex_color = rgb_to_hex(r, g, b)

        # Copy HEX to clipboard and update status
        try:
            self.clipboard_clear()
            self.clipboard_append(hex_color)
        except Exception:
            pass
        self.status.config(text=f"Copied {hex_color} to clipboard")

        # Update the eyedropper UI to match clicking on the image
        self._apply_color_readout(hex_color, r, g, b)

    def _apply_color_readout(self, hex_color: str, r: int, g: int, b: int):
        """Update sidebar eyedropper readout with this color."""
        try:
            # swatch square
            self.side_panel.swatch.config(bg=hex_color)
            # labels
            self.side_panel.rgb_label.config(text=f"RGB: ({r}, {g}, {b})")
            self.side_panel.hex_label.config(text=f"HEX: {hex_color}")
            self.side_panel.hsv_label.config(text=f"HSV: {rgb_to_hsv_str(r, g, b)}")
            # clear pixel co-ords since this came from the palette
            self.side_panel.xy_label.config(text="Pixel: —")
        except Exception:
            pass

    # fit image to window
    def set_fit(self):
        self.img_state.fit_to_window = True
        self.redraw()

    # set zoom to specific level
    def set_zoom(self, z: float):
        if not self.img_state.has_image:
            return
        self.img_state.fit_to_window = False
        self.img_state.scale = max(0.05, min(40.0, z))
        self.redraw()

    # change zoom by a factor
    def bump_zoom(self, factor: float):
        if self.img_state.has_image:
            self.set_zoom(self.img_state.scale * factor)

    # update the preview panel
    def update_preview(self):
        if not self.img_state.has_image:
            try:
                self.side_panel.set_preview_image_from_pil(None)
            except Exception:
                pass
            return

        # Use SidePanel API to set preview from PIL image directly
        try:
            self.side_panel.set_preview_image_from_pil(self.img_state.img, allow_upscale=self.toolbar.upscale_var.get())
        except Exception:
            # fallback to making a thumbnail and using whatever older API exists
            try:
                pw, ph = self.side_panel.preview_size
                thumb = self.img_state.img.copy()
                thumb.thumbnail((pw, ph), RESAMPLE)
                self.side_panel.set_preview_image_from_pil(thumb, allow_upscale=False)
            except Exception:
                pass

    # update image metadata
    def update_meta(self):
        if not self.img_state.has_image:
            try:
                self.side_panel.set_metadata_text("No image loaded.")
            except Exception:
                pass
            return

        iw, ih = self.img_state.img.size

        # Determine file format for display
        fmt = self.img_state.file_format or ("PCX" if self.img_state.pcx_header else None)
        fmt_text = f"Format: {fmt} | " if fmt else ""

        # Base metadata lines
        lines = [
            f"Size: {iw} × {ih} px",
            f"{fmt_text}Mode: {self.img_state.img.mode}",
        ]

        # If PCX header is present, indicate that detailed header is available
        if self.img_state.pcx_header:
            lines.append("PCX header parsed ✓ (see details below).")

        # If JPEG EXIF is present, show a concise selection of common tags
        if self.img_state.jpeg_exif:
            wanted = [
                'DateTime', 'Model', 'Make', 'LensModel', 'FNumber', 'ExposureTime',
                'ISOSpeedRatings', 'PhotographicSensitivity', 'FocalLength', 'Orientation'
            ]
            ex = self.img_state.jpeg_exif
            shown = {k: ex[k] for k in wanted if k in ex}
            if shown:
                lines.append("EXIF:")
                for k, v in shown.items():
                    lines.append(f"  • {k}: {v}")

        # Render to the side panel via its API
        try:
            self.side_panel.set_metadata_text("\n".join(lines))
        except Exception:
            # fallback
            try:
                self.side_panel.meta_label.config(text="\n".join(lines))
            except Exception:
                pass

    # copy HEX color to clipboard
    def copy_hex(self):
        txt = self.side_panel.hex_label.cget("text").replace("HEX: ", "")
        if txt and txt != "—":
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.status.config(text=f"Copied {txt} to clipboard")

    # copy RGB color to clipboard
    def copy_rgb(self):
        txt = self.side_panel.rgb_label.cget("text").replace("RGB: ", "")
        if txt and txt != "—":
            self.clipboard_clear()
            self.clipboard_append(txt)
            self.status.config(text=f"Copied {txt} to clipboard")

    # ------------------ Rendering ------------------

    # redraw the canvas
    def redraw(self):
        c = self.canvas
        c.delete("all")
        if not self.img_state.has_image:
            c.configure(scrollregion=(0, 0, 0, 0))
            try:
                self.toolbar.zoom_label.config(text="")
            except Exception:
                pass
            return

        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        iw, ih = self.img_state.img.size

        if self.img_state.fit_to_window:
            sx, sy = cw / iw, ch / ih
            allow_up = self.toolbar.upscale_var.get()
            self.img_state.scale = min(sx, sy) if allow_up else min(sx, sy, 1.0)

        dw, dh = max(1, int(iw * self.img_state.scale)), max(1, int(ih * self.img_state.scale))
        self.img_state.disp_size = (dw, dh)

        disp_img = self.img_state.img if self.img_state.scale == 1.0 else self.img_state.img.resize((dw, dh), RESAMPLE)
        # keep a tk PhotoImage reference in state
        self.img_state.tk_img = ImageTk.PhotoImage(disp_img)
        img_item = c.create_image(0, 0, image=self.img_state.tk_img, anchor="nw")

        c.configure(scrollregion=(0, 0, dw, dh))
        x0 = max(0, (cw - dw) // 2)
        y0 = max(0, (ch - dh) // 2)
        self.img_state.offset = (x0, y0)
        # position the image item
        try:
            c.coords(img_item, x0, y0)
        except Exception:
            try:
                c.moveto(img_item, x0, y0)
            except Exception:
                pass

        try:
            self.toolbar.zoom_label.config(text=f"Zoom: {int(self.img_state.scale * 100)}%")
        except Exception:
            pass
        self.status.config(text=f"Image: {iw}×{ih}px  |  Display: {dw}×{dh}px")

    # ------------------ Interaction ------------------

    # controller hook called by ImageCanvas when a click happens on the main image.
    # Returns True when the controller handles the click (so ImageCanvas won't fallback).
    def on_image_click(self, x_img, y_img):
        """Called by ImageCanvas when user clicks on the image (image coordinates)."""
        # Update preview to the current image (always)
        try:
            if self.img_state.img is not None:
                self.side_panel.set_preview_image_from_pil(self.img_state.img)
        except Exception:
            pass

        # If click is within image bounds, update eyedropper readout as if user picked that pixel
        try:
            iw, ih = self.img_state.img.size
            if 0 <= x_img < iw and 0 <= y_img < ih:
                pixel = self.img_state.img.getpixel((x_img, y_img))
                if isinstance(pixel, (tuple, list)):
                    r, g, b = pixel[:3]
                else:
                    r = g = b = pixel
                hex_color = rgb_to_hex(r, g, b)
                self._apply_color_readout(hex_color, r, g, b)
                # show coords
                try:
                    self.side_panel.xy_label.config(text=f"Pixel: ({x_img}, {y_img})")
                except Exception:
                    pass
        except Exception:
            pass

  
        return True

    # convert canvas coords to image coords
    def _canvas_to_image_xy(self, cx, cy):
        if not self.img_state.has_image:
            return None
        x_disp = cx - self.img_state.offset[0]
        y_disp = cy - self.img_state.offset[1]
        if not (0 <= x_disp < self.img_state.disp_size[0] and 0 <= y_disp < self.img_state.disp_size[1]):
            return None
        if self.img_state.scale == 0:
            return None
        x, y = int(x_disp / self.img_state.scale), int(y_disp / self.img_state.scale)
        iw, ih = self.img_state.img.size
        if 0 <= x < iw and 0 <= y < ih:
            return (x, y)
        return None

    # pick color from image at canvas coords (legacy binding; kept for compatibility)
    def _pick_color(self, event):
        xy = self._canvas_to_image_xy(event.x, event.y)
        if not xy:
            return
        x, y = xy

        # Get pixel and handle different image modes
        pixel = self.img_state.img.getpixel((x, y))
        if isinstance(pixel, (tuple, list)):
            r, g, b = pixel[:3]
        else:
            # Assume grayscale or single-channel, treat as R=G=B
            r = g = b = pixel

        hex_color = rgb_to_hex(r, g, b)
        # Use shared helper so both palette clicks and image picks update UI the same
        self._apply_color_readout(hex_color, r, g, b)
        # And show coordinates for pixel picks
        try:
            self.side_panel.xy_label.config(text=f"Pixel: ({x}, {y})")
        except Exception:
            pass

    # ------------------ Bindings ------------------

    # initialize key and mouse bindings
    def _init_bindings(self):
        c = self.canvas
        # redraw when canvas is resized
        c.bind("<Configure>", lambda e: self.redraw())

        # Keep legacy pick-color binding (in case you rely on it)
        c.bind("<Button-1>", self._pick_color)

        # Mouse wheel zoom
        self.bind_all("<Control-MouseWheel>", self._on_zoom_wheel)
        self.bind_all("<Control-Button-4>", lambda e: self._on_zoom_wheel(e, linux_up=True))
        self.bind_all("<Control-Button-5>", lambda e: self._on_zoom_wheel(e, linux_up=False))

        # Scroll
        self.bind_all("<MouseWheel>", self._on_scroll)
        self.bind_all("<Button-4>", lambda e: self._on_scroll(e, linux_up=True))
        self.bind_all("<Button-5>", lambda e: self._on_scroll(e, linux_up=False))

        # Shortcuts
        self.bind_all("<Control-o>", lambda e: self.open_image())
        self.bind_all("<Control-Key-0>", lambda e: self.set_fit())
        self.bind_all("<Control-Key-1>", lambda e: self.set_zoom(1.0))
        self.bind_all("<Control-minus>", lambda e: self.bump_zoom(0.9))
        self.bind_all("<Control-equal>", lambda e: self.bump_zoom(1.1))

        self.bind_all("<Control-w>", lambda e: self.close_image())

    # mouse wheel zoom handler
    def _on_zoom_wheel(self, event, linux_up=None):
        """Zoom (Ctrl + wheel) keeping the cursor point fixed on the image.
        Works correctly even when bound via bind_all by converting pointer coords to canvas coords.
        """
        if not self.img_state.has_image:
            return

        # Figure out direction / factor
        if linux_up is None:
            # On Windows/macOS event.delta is non-zero; on some systems positive -> up
            delta = getattr(event, "delta", 0)
            factor = 1.1 if delta > 0 else 1 / 1.1
        else:
            factor = 1.1 if linux_up else 1 / 1.1

        # Convert global pointer to canvas coords to avoid jumpiness when bind_all is used
        try:
            # Get global pointer position in screen coords
            px, py = self.winfo_pointerxy()
            # Convert screen to canvas coords
            cx = self.canvas.canvasx(px - self.canvas.winfo_rootx())
            cy = self.canvas.canvasy(py - self.canvas.winfo_rooty())
        except Exception:
            # Fallback to event coordinates if conversion fails
            cx, cy = event.x, event.y

        img_xy_before = self._canvas_to_image_xy(int(cx), int(cy))
        self.bump_zoom(factor)
        # Keep the same image pixel under the pointer after zoom
        self._keep_point_under_cursor(img_xy_before, int(cx), int(cy))

    # keep the point under cursor fixed during zoom
    def _keep_point_under_cursor(self, img_xy, cx, cy):
        """After zoom, move view so that the image pixel (img_xy) remains under canvas coords (cx,cy)."""
        if not img_xy:
            return
        x, y = img_xy

        # Pixel's display coordinates at the current scale
        x_disp = int(x * self.img_state.scale)
        y_disp = int(y * self.img_state.scale)

        # Target absolute canvas coords where that pixel should appear
        target_x = x_disp + self.img_state.offset[0]
        target_y = y_disp + self.img_state.offset[1]

        dw, dh = self.img_state.disp_size

        # Compute fraction positions for xview/yview
        if dw > 0:
            frac_x = (target_x - cx) / dw
            frac_x = max(0.0, min(1.0, frac_x))
            self.canvas.xview_moveto(frac_x)
        if dh > 0:
            frac_y = (target_y - cy) / dh
            frac_y = max(0.0, min(1.0, frac_y))
            self.canvas.yview_moveto(frac_y)

    # mouse wheel scroll handler
    def _on_scroll(self, event, linux_up=None):
        if linux_up is None:
            delta = getattr(event, "delta", 0)
            if getattr(event, "state", 0) & 0x0001:  # Shift
                self.canvas.xview_scroll(-1 if delta > 0 else 1, "units")
            else:
                self.canvas.yview_scroll(-1 if delta > 0 else 1, "units")
        else:
            if getattr(event, "state", 0) & 0x0001:
                self.canvas.xview_scroll(-1 if linux_up else 1, "units")
            else:
                self.canvas.yview_scroll(-1 if linux_up else 1, "units")


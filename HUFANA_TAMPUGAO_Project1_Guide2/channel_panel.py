# channel_panel.py
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from point_processing_panel import PointProcessingPanel
from image_enhancement_panel import ImageEnhancementPanel

def split_channels(img):
    r, g, b = img.split()
    return r, g, b

def to_grayscale(img):
    arr = np.array(img)
    gray = np.mean(arr, axis=2).astype(np.uint8)
    return Image.fromarray(gray, mode='L')

def compute_histogram(img):
    arr = np.array(img)
    if arr.ndim == 3:
        arr = arr.mean(axis=2).astype(np.uint8)
    hist, _ = np.histogram(arr.flatten(), bins=256, range=(0, 255))
    return hist

class ChannelPanel(ttk.Frame):
    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tabs = ttk.Notebook(scrollable_frame)
        self.tabs.pack(fill="both", expand=True)
        self.frames = {}

        for name in ["Channels", "Histograms", "Grayscale", "Point Processing", "Image Enhancement"]:
            f = ttk.Frame(self.tabs)
            self.tabs.add(f, text=name)
            self.frames[name] = f

        self.point_panel = PointProcessingPanel(self.frames["Point Processing"], controller=self.controller)
        self.point_panel.pack(fill="both", expand=True)
        
        
        self.enhancement_panel = ImageEnhancementPanel(self.frames["Image Enhancement"], controller=self.controller)
        self.enhancement_panel.pack(fill="both", expand=True)

    def show_channels(self, img):
    # When closing image
        if img is None:
            # Clear only channel-related visuals
            for name, frame in self.frames.items():
                if name in ["Channels", "Histograms", "Grayscale"]:
                    for child in frame.winfo_children():
                        child.destroy()

            # Reset Point Processing and Enhancement panels (without destroying them)
            if hasattr(self, 'point_panel'):
                try:
                    self.point_panel.reset_panel()
                except Exception as e:
                    print("Warning: point panel reset failed:", e)

            if hasattr(self, 'enhancement_panel'):
                try:
                    self.enhancement_panel.reset_panel()
                except Exception as e:
                    print("Warning: enhancement panel reset failed:", e)

            return

        # --- Normal display when an image is loaded ---
        for child in self.frames["Channels"].winfo_children():
            child.destroy()

        r, g, b = split_channels(img)
        imgs = [r, g, b]
        names = ["Red", "Green", "Blue"]

        for i, (sub, name) in enumerate(zip(imgs, names)):
            photo = ImageTk.PhotoImage(sub.resize((300, 300)))
            lbl = ttk.Label(self.frames["Channels"], text=name)
            lbl.grid(row=0, column=i, padx=10)
            canv = tk.Label(self.frames["Channels"], image=photo)
            canv.image = photo
            canv.grid(row=1, column=i, padx=10, pady=5)

        # Update other tabs
        self._show_histograms(r, g, b)
        self._show_grayscale(img)

        # 🧩 Also refresh Point Processing panel to use current image
        if hasattr(self, 'point_panel'):
            try:
                self.point_panel._update_display_image(img)
            except Exception:
                pass

        # 🧩 Also refresh Image Enhancement panel to use current image
        if hasattr(self, 'enhancement_panel'):
            try:
                # method name may differ: use the same method used in point panel (here _update_display_image)
                # adjust if your enhancement panel defines a different public method like display_image()
                self.enhancement_panel._update_display_image(img)
            except Exception:
                pass


    def _show_histograms(self, r, g, b):
        for child in self.frames["Histograms"].winfo_children():
            child.destroy()

        sub_tabs = ttk.Notebook(self.frames["Histograms"])
        sub_tabs.pack(fill="both", expand=True)

        tabs_info = [
            ("Combined RGB", [("Red", r, 'red'), ("Green", g, 'green'), ("Blue", b, 'blue')]),
            ("Red Only", [("Red", r, 'red')]),
            ("Green Only", [("Green", g, 'green')]),
            ("Blue Only", [("Blue", b, 'blue')]),
        ]

        for tab_name, channels in tabs_info:
            frame = ttk.Frame(sub_tabs)
            sub_tabs.add(frame, text=tab_name)

            fig = Figure(figsize=(5, 3))
            ax = fig.add_subplot(111)

            for ch_name, ch_img, color in channels:
                hist = compute_histogram(ch_img)
                ax.plot(hist, color=color, label=ch_name)

            ax.set_xlim(0, 255)
            ax.set_xlabel("Intensity")
            ax.set_ylabel("Frequency")
            ax.set_title(f"{tab_name} Histogram")

            if len(channels) > 1:
                ax.legend()

            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            canvas.draw()

    def _show_grayscale(self, img):
        for child in self.frames["Grayscale"].winfo_children():
            child.destroy()

        sub_tabs = ttk.Notebook(self.frames["Grayscale"])
        sub_tabs.pack(fill="both", expand=True)

        gray_img_frame = ttk.Frame(sub_tabs)
        gray_hist_frame = ttk.Frame(sub_tabs)
        sub_tabs.add(gray_img_frame, text="Grayscale Image")
        sub_tabs.add(gray_hist_frame, text="Grayscale Histogram")

        gray = to_grayscale(img)
        gray_photo = ImageTk.PhotoImage(gray.resize((300, 300)))

        lbl = ttk.Label(gray_img_frame, text="Grayscale Image")
        lbl.pack(pady=5)
        img_label = tk.Label(gray_img_frame, image=gray_photo)
        img_label.image = gray_photo
        img_label.pack(pady=5)

        hist = compute_histogram(gray)
        fig = Figure(figsize=(5, 3))
        ax = fig.add_subplot(111)
        ax.plot(hist, color='black')
        ax.set_title("Grayscale Histogram")
        ax.set_xlim(0, 255)
        ax.set_xlabel("Intensity")
        ax.set_ylabel("Count")

        canvas = FigureCanvasTkAgg(fig, master=gray_hist_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()

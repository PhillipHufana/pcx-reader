# ==========================
# File: channel_panel.py
# ==========================
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

def split_channels(img):
    """Return individual R, G, B images."""
    r, g, b = img.split()
    return r, g, b

def to_grayscale(img):
    """Return grayscale using (R+G+B)/3."""
    arr = np.array(img)
    gray = np.mean(arr, axis=2).astype(np.uint8)
    return Image.fromarray(gray, mode='L')

def compute_histogram(img):
    """Compute histogram (0–255 counts)."""
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
        # Make panel scrollable for large content
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Replace 'self' with scrollable_frame as parent of tabs
        self.tabs = ttk.Notebook(scrollable_frame)
        self.tabs.pack(fill="both", expand=True)
        self.frames = {}

        for name in ["Channels", "Histograms", "Grayscale"]:
            f = ttk.Frame(self.tabs)
            self.tabs.add(f, text=name)
            self.frames[name] = f

    def show_channels(self, img):
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

        self._show_histograms(r, g, b)
        self._show_grayscale(img)

    def _show_histograms(self, r, g, b):
        """Display combined and individual RGB histograms in sub-tabs."""
        for child in self.frames["Histograms"].winfo_children():
            child.destroy()

        # Create sub-tabs
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
        # Clear the "Grayscale" tab
        for child in self.frames["Grayscale"].winfo_children():
            child.destroy()

        # --- Create sub-tabs inside "Grayscale" tab ---
        sub_tabs = ttk.Notebook(self.frames["Grayscale"])
        sub_tabs.pack(fill="both", expand=True)

        gray_img_frame = ttk.Frame(sub_tabs)
        gray_hist_frame = ttk.Frame(sub_tabs)
        sub_tabs.add(gray_img_frame, text="Grayscale Image")
        sub_tabs.add(gray_hist_frame, text="Grayscale Histogram")

        # --- Grayscale Image ---
        gray = to_grayscale(img)
        gray_photo = ImageTk.PhotoImage(gray.resize((300, 300)))

        lbl = ttk.Label(gray_img_frame, text="Grayscale Image")
        lbl.pack(pady=5)
        img_label = tk.Label(gray_img_frame, image=gray_photo)
        img_label.image = gray_photo
        img_label.pack(pady=5)

        # --- Grayscale Histogram ---
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

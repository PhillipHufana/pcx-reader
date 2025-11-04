import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from point_processing_panel import PointProcessingPanel
from image_enhancement_panel import ImageEnhancementPanel

# ===========================================================
#  BASIC IMAGE UTILITIES
# ===========================================================

def split_channels(img):
    """Split RGB image into individual Red, Green, and Blue channel images."""
    r, g, b = img.split()
    return r, g, b

def to_grayscale(img):
    """Convert RGB image to grayscale by averaging RGB values per pixel."""
    arr = np.array(img)
    gray = np.mean(arr, axis=2).astype(np.uint8)
    return Image.fromarray(gray, mode='L')

def compute_histogram(img):
    """
    Compute histogram of an image.
    - Converts to grayscale if image has 3 channels.
    - Uses NumPy to count pixel frequency for intensity values (0–255).
    Returns an array of 256 bins representing pixel counts.
    """
    arr = np.array(img)
    if arr.ndim == 3:  # If colored image, average the RGB channels
        arr = arr.mean(axis=2).astype(np.uint8)
    hist, _ = np.histogram(arr.flatten(), bins=256, range=(0, 255))
    return hist

# ===========================================================
#  CHANNEL PANEL — HANDLES IMAGE DISPLAY AND ANALYSIS
# ===========================================================

class ChannelPanel(ttk.Frame):
    """
    The ChannelPanel manages the right-side tabbed interface containing:
    - RGB channel separation
    - Histograms (RGB + Grayscale)
    - Grayscale display
    - Point Processing operations
    - Image Enhancement operations
    """

    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self._build_ui()

    # -------------------------------------------------------
    # BUILD UI: Creates tab structure for all visual panels
    # -------------------------------------------------------
    def _build_ui(self):
        # Canvas and scrollbar allow for scrollable area
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Automatically resize the scroll region based on content
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Create main notebook tabs
        self.tabs = ttk.Notebook(scrollable_frame)
        self.tabs.pack(fill="both", expand=True)
        self.frames = {}

        # Create tabs for various functions
        for name in ["Channels", "Histograms", "Grayscale", "Point Processing", "Image Enhancement"]:
            f = ttk.Frame(self.tabs)
            self.tabs.add(f, text=name)
            self.frames[name] = f

        # Integrate sub-panels for image processing and enhancement
        self.point_panel = PointProcessingPanel(self.frames["Point Processing"], controller=self.controller)
        self.point_panel.pack(fill="both", expand=True)
        
        self.enhancement_panel = ImageEnhancementPanel(self.frames["Image Enhancement"], controller=self.controller)
        self.enhancement_panel.pack(fill="both", expand=True)

    # -------------------------------------------------------
    # SHOW CHANNELS: Display RGB channels and update other tabs
    # -------------------------------------------------------
    def show_channels(self, img):
        """
        Displays the individual R, G, and B channels as separate images,
        and triggers histogram and grayscale visualizations.
        Also updates other functional panels (point & enhancement).
        """
        # 🧩 Handle case when image is closed or cleared
        if img is None:
            # Clear previous visual content (images + histograms)
            for name, frame in self.frames.items():
                if name in ["Channels", "Histograms", "Grayscale"]:
                    for child in frame.winfo_children():
                        child.destroy()

            # Reset sub-panels safely
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

        # 🔹 Normal display when image is available
        for child in self.frames["Channels"].winfo_children():
            child.destroy()

        # Split image into separate color channels
        r, g, b = split_channels(img)
        imgs = [r, g, b]
        names = ["Red", "Green", "Blue"]

        # Display each channel as separate image thumbnail
        for i, (sub, name) in enumerate(zip(imgs, names)):
            photo = ImageTk.PhotoImage(sub.resize((300, 300)))
            lbl = ttk.Label(self.frames["Channels"], text=name)
            lbl.grid(row=0, column=i, padx=10)
            canv = tk.Label(self.frames["Channels"], image=photo)
            canv.image = photo
            canv.grid(row=1, column=i, padx=10, pady=5)

        # Trigger histogram and grayscale updates
        self._show_histograms(r, g, b)
        self._show_grayscale(img)

        # Update panels to reflect current image
        if hasattr(self, 'point_panel'):
            try:
                self.point_panel._update_display_image(img)
            except Exception:
                pass

        if hasattr(self, 'enhancement_panel'):
            try:
                self.enhancement_panel._update_display_image(img)
            except Exception:
                pass

    # -------------------------------------------------------
    # HISTOGRAM DISPLAY FOR RGB CHANNELS
    # -------------------------------------------------------
    def _show_histograms(self, r, g, b):
        """
        Computes and displays histograms for R, G, and B channels using Matplotlib.
        - Combined RGB histogram (3 color overlays)
        - Individual Red, Green, and Blue histograms
        Embedded directly in Tkinter via FigureCanvasTkAgg.
        """
        # Clear any existing histograms from the tab
        for child in self.frames["Histograms"].winfo_children():
            child.destroy()

        sub_tabs = ttk.Notebook(self.frames["Histograms"])
        sub_tabs.pack(fill="both", expand=True)

        # Define which histograms to show
        tabs_info = [
            ("Combined RGB", [("Red", r, 'red'), ("Green", g, 'green'), ("Blue", b, 'blue')]),
            ("Red Only", [("Red", r, 'red')]),
            ("Green Only", [("Green", g, 'green')]),
            ("Blue Only", [("Blue", b, 'blue')]),
        ]

        # Create a separate plot for each tab
        for tab_name, channels in tabs_info:
            frame = ttk.Frame(sub_tabs)
            sub_tabs.add(frame, text=tab_name)

            fig = Figure(figsize=(5, 3))
            ax = fig.add_subplot(111)

            # Plot histogram for each selected channel
            for ch_name, ch_img, color in channels:
                hist = compute_histogram(ch_img)
                ax.plot(hist, color=color, label=ch_name)

            ax.set_xlim(0, 255)
            ax.set_xlabel("Intensity")
            ax.set_ylabel("Frequency")
            ax.set_title(f"{tab_name} Histogram")

            if len(channels) > 1:
                ax.legend()

            # Embed the plot inside the Tkinter frame
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.get_tk_widget().pack(fill="both", expand=True)
            canvas.draw()

    # -------------------------------------------------------
    # GRAYSCALE DISPLAY AND HISTOGRAM
    # -------------------------------------------------------
    def _show_grayscale(self, img):
        """
        Displays:
        1. Grayscale version of the image.
        2. Its corresponding intensity histogram.
        Both displayed in sub-tabs under 'Grayscale' tab.
        """
        for child in self.frames["Grayscale"].winfo_children():
            child.destroy()

        sub_tabs = ttk.Notebook(self.frames["Grayscale"])
        sub_tabs.pack(fill="both", expand=True)

        gray_img_frame = ttk.Frame(sub_tabs)
        gray_hist_frame = ttk.Frame(sub_tabs)
        sub_tabs.add(gray_img_frame, text="Grayscale Image")
        sub_tabs.add(gray_hist_frame, text="Grayscale Histogram")

        # Convert image to grayscale for uniform intensity analysis
        gray = to_grayscale(img)
        gray_photo = ImageTk.PhotoImage(gray.resize((300, 300)))

        # Display grayscale image
        lbl = ttk.Label(gray_img_frame, text="Grayscale Image")
        lbl.pack(pady=5)
        img_label = tk.Label(gray_img_frame, image=gray_photo)
        img_label.image = gray_photo
        img_label.pack(pady=5)

        # Compute histogram of grayscale image
        hist = compute_histogram(gray)
        fig = Figure(figsize=(5, 3))
        ax = fig.add_subplot(111)
        ax.plot(hist, color='black')
        ax.set_title("Grayscale Histogram")
        ax.set_xlim(0, 255)
        ax.set_xlabel("Intensity")
        ax.set_ylabel("Count")

        # Embed histogram under grayscale tab
        canvas = FigureCanvasTkAgg(fig, master=gray_hist_frame)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.draw()

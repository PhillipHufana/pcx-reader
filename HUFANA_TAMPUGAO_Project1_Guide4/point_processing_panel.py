import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageOps
import numpy as np
import matplotlib.pyplot as plt

class PointProcessingPanel(ttk.Frame):
    """
    Point Processing Panel
    -----------------------------------
    Each operation here modifies pixel values directly
    without considering neighbors (unlike spatial filters).
    Algorithms implemented:
    - Grayscale Conversion
    - Negative Transformation
    - Histogram Equalization
    - Thresholding (binary)
    - Gamma Correction
    """

    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller  # Reference to the main controller that manages current_image
        self.pack(fill="both", expand=True, padx=10, pady=10)

        # ===== HEADER =====
        ttk.Label(
            self,
            text="🎨 Point Processing Methods",
            font=("Arial", 16, "bold"),
            foreground="#2B547E"
        ).pack(pady=10)

        # ===== BUTTON PANEL =====
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Grayscale", command=self.apply_grayscale).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Negative", command=self.apply_negative).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Histogram Equalizaaation", command=self.apply_hist_eq).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_image).grid(row=0, column=3, padx=5, pady=5)

        # ===== SLIDER CONTROLS =====
        ttk.Label(self, text="Threshold (0–255)").pack(pady=(10, 0))
        self.threshold_var = tk.IntVar(value=128)
        self.threshold_slider = ttk.Scale(self, from_=0, to=255, orient="horizontal",
                                          variable=self.threshold_var, command=self._apply_threshold)
        self.threshold_slider.pack(fill="x", padx=20)

        ttk.Label(self, text="Gamma Correction (0.1–5.0)").pack(pady=(10, 0))
        self.gamma_var = tk.DoubleVar(value=1.0)
        self.gamma_slider = ttk.Scale(self, from_=0.1, to=5.0, orient="horizontal",
                                      variable=self.gamma_var, command=self._apply_gamma)
        self.gamma_slider.pack(fill="x", padx=20)

        # ===== IMAGE PREVIEW AND HISTOGRAM =====
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=10)

        self.hist_frame = ttk.Frame(self)  # Frame for histogram display
        self.hist_frame.pack(fill="both", expand=True, pady=(5, 10))

        self.info_label = ttk.Label(self, text="", font=("Arial", 10))
        self.info_label.pack(pady=(5, 10))

        self._update_display_image()

    # --------------------------------------------------
    # IMAGE DISPLAY HANDLING
    # --------------------------------------------------
    def _update_display_image(self, img=None):
        """Display the current image in the GUI panel."""
        if img is None:
            img = getattr(self.controller, "current_image", None)
        if img is None:
            self.image_label.configure(image='')
            self.image_label.image = None
            return
        img_copy = img.copy()
        img_copy.thumbnail((400, 400))
        tk_img = ImageTk.PhotoImage(img_copy)
        self.image_label.configure(image=tk_img)
        self.image_label.image = tk_img

    def ensure_image_loaded(self):
        """Ensure that an image is loaded before applying transformations."""
        if hasattr(self.controller, "current_image") and self.controller.current_image is not None:
            return True
        messagebox.showerror("Error", "No image found. Please load one in the main window.")
        return False

    # --------------------------------------------------
    # POINT PROCESSING FILTERS
    # --------------------------------------------------

    def apply_grayscale(self):
        """
        Grayscale Conversion
        -------------------------------
        Algorithm:
        - Converts RGB to grayscale by averaging color channels.
          gray = (R + G + B) / 3
        - Simplifies intensity representation into a single channel.
        Effect:
        - Reduces image complexity and prepares it for further processing 
          (e.g., thresholding, histogram equalization).
        """
        if not self.ensure_image_loaded(): return
        img = self.controller.current_image
        arr = np.array(img)
        gray = np.mean(arr, axis=2).astype(np.uint8)   # Average RGB values per pixel
        gray_img = Image.fromarray(gray)

        self.controller.current_image = gray_img
        self._update_display_image(gray_img)
        self._refresh_controller()
        self.info_label.config(text="Applied Grayscale Transformation.")

    def apply_negative(self):
        """
        Negative Transformation
        -------------------------------
        Algorithm:
        - Inverts each pixel intensity.
          new_pixel = 255 - old_pixel
        Effect:
        - Produces a photographic negative.
        - Enhances light details in dark regions and vice versa.
        """
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        neg = 255 - img   # Pixel inversion
        neg_img = Image.fromarray(neg.astype(np.uint8))

        self.controller.current_image = neg_img
        self._update_display_image(neg_img)
        self._refresh_controller()
        self.info_label.config(text="Applied Negative Transformation.")
            
    def apply_hist_eq(self):
        """
        Histogram Equalization
        -------------------------------
        Algorithm:
        - Enhances contrast by redistributing intensity values.
        - Steps:
            1. Compute histogram and probability density (PDF)
            2. Compute cumulative distribution function (CDF)
            3. Map old intensities to new ones using:
               new_pixel = floor(255 * CDF(old_pixel))
        Effect:
        - Makes dark areas brighter and bright areas darker 
          (improves global contrast).
        """
        if not self.ensure_image_loaded(): return

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        img = np.array(self.controller.current_image.convert("L"))  # Convert to grayscale
        hist, _ = np.histogram(img.flatten(), bins=256, range=[0, 256])

        # Compute probability and cumulative distributions
        pdf = hist / np.sum(hist)
        cdf = np.cumsum(pdf)

        # Equalize using mapping function
        equalized = np.floor(255 * cdf[img]).astype(np.uint8)
        eq_img = Image.fromarray(equalized)

        # Compute new histogram for visualization
        hist_eq, _ = np.histogram(equalized.flatten(), bins=256, range=[0, 256])

        # Display updated image
        self.controller.current_image = eq_img
        self._update_display_image(eq_img)
        self._refresh_controller()
        self.info_label.config(text="Applied Histogram Equalization (contrast enhanced).")

        # Display original vs. equalized histogram for analysis
        for widget in self.hist_frame.winfo_children():
            widget.destroy()

        fig = Figure(figsize=(6, 2.5))
        axs = fig.subplots(1, 2)

        axs[0].plot(hist, color='gray')
        axs[0].set_title("Original Histogram")
        axs[0].set_xlabel("Intensity")
        axs[0].set_ylabel("Frequency")

        axs[1].plot(hist_eq, color='black')
        axs[1].set_title("Equalized Histogram")
        axs[1].set_xlabel("Intensity")
        axs[1].set_ylabel("Frequency")

        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.hist_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(pady=5)

    def _apply_threshold(self, val):
        """
        Thresholding (Binary Conversion)
        -------------------------------
        Algorithm:
        - Converts grayscale image to binary form:
          if pixel > T → 255 (white)
          else → 0 (black)
        - T is controlled by the threshold slider (0–255).
        Effect:
        - Separates foreground and background objects.
        """
        if not self.ensure_image_loaded(): return
        try:
            base_img = self.controller.img_state.original_img
            if base_img is None: return
            img_gray = np.array(base_img.convert("L"))
            thresh = int(float(val))
            binary = np.where(img_gray > thresh, 255, 0).astype(np.uint8)
            bw_img = Image.fromarray(binary)
            self.controller.current_image = bw_img
            self._update_display_image(bw_img)
            self._refresh_controller()
            self.info_label.config(text=f"Threshold applied: {thresh}")
        except Exception:
            pass

    def _apply_gamma(self, val):
        """
        Gamma Correction
        -------------------------------
        Algorithm:
        - Performs power-law transformation:
          new_pixel = 255 * (old_pixel / 255)^γ
        - γ (gamma) is controlled by slider (0.1–5.0)
        Effect:
        - γ < 1 → Brightens the image
        - γ > 1 → Darkens the image
        - Used to adjust image luminance and improve visibility.
        """
        if not self.ensure_image_loaded(): return
        try:
            base_img = self.controller.img_state.original_img
            if base_img is None: return
            img_gray = np.array(base_img.convert("L"), dtype=np.float32) / 255.0
            gamma = float(val)
            corrected = np.power(img_gray, gamma)    # Apply gamma correction formula
            gamma_img = Image.fromarray((corrected * 255).astype(np.uint8))
            self.controller.current_image = gamma_img
            self._update_display_image(gamma_img)
            self._refresh_controller()
            self.info_label.config(text=f"Gamma Correction Applied (γ={gamma:.2f})")
        except Exception:
            pass

    # --------------------------------------------------
    # RESET HANDLER
    # --------------------------------------------------
    def reset_image(self):
        """Restore the original image and reset all sliders."""
        if hasattr(self.controller.img_state, "original_img") and self.controller.img_state.original_img:
            self.controller.current_image = self.controller.img_state.original_img.copy()
            self.threshold_var.set(128)
            self.gamma_var.set(1.0)
            self._update_display_image(self.controller.current_image)
            self._refresh_controller()
            self.info_label.config(text="Image reset to original.")
        else:
            self.info_label.config(text="No original image to reset.")

    # --------------------------------------------------
    # SYNC MAIN CONTROLLER PANELS
    # --------------------------------------------------
    def _refresh_controller(self):
        """Refresh other panels such as channel views and histograms."""
        try:
            self.controller.update_preview()
            self.controller.channel_panel.show_channels(self.controller.current_image)
            self.controller.redraw()
        except Exception:
            pass

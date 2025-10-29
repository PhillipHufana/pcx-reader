import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageOps
import numpy as np
import matplotlib.pyplot as plt
class PointProcessingPanel(ttk.Frame):
    """
    Integrated Point Processing Panel for main controller:
    - Grayscale
    - Negative
    - Histogram Equalization
    - Threshold (slider inside UI)
    - Gamma Correction (slider inside UI)
    - Reset
    """

    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller  # reference to main controller
        self.pack(fill="both", expand=True, padx=10, pady=10)

        #- HEADER-
        ttk.Label(
            self,
            text="🎨 Point Processing Methods",
            font=("Arial", 16, "bold"),
            foreground="#2B547E"
        ).pack(pady=10)

        #- BUTTON FRAME-
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Grayscale", command=self.apply_grayscale).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Negative", command=self.apply_negative).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Histogram Equalization", command=self.apply_hist_eq).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_image).grid(row=0, column=3, padx=5, pady=5)

        #- SLIDERS-
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

        #  IMAGE DISPLAY 
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=10)

        #  HISTOGRAM FRAME 
        # This frame will hold the histogram plots under the image
        self.hist_frame = ttk.Frame(self)
        self.hist_frame.pack(fill="both", expand=True, pady=(5, 10))

        #  INFO LABEL 
        self.info_label = ttk.Label(self, text="", font=("Arial", 10))
        self.info_label.pack(pady=(5, 10))

        self._update_display_image()

    # IMAGE HANDLING
    def _update_display_image(self, img=None):
        """Display image on GUI; default to controller's current_image"""
        if img is None:
            img = getattr(self.controller, "current_image", None)
        if img is None:
            # Clear the image label
            self.image_label.configure(image='')
            self.image_label.image = None
            return
        img_copy = img.copy()
        img_copy.thumbnail((400, 400))
        tk_img = ImageTk.PhotoImage(img_copy)
        self.image_label.configure(image=tk_img)
        self.image_label.image = tk_img
    
    def reset_panel(self):
        """Clear the displayed image and reset controls."""
        try:
            if hasattr(self, "canvas"):
                self.canvas.delete("all")
            if hasattr(self, "image_label"):
                self.image_label.config(image='', text="No image loaded.")
            if hasattr(self, "photo"):
                self.photo = None
            if hasattr(self, "current_image"):
                self.current_image = None
            if hasattr(self, "display_img"):
                self.display_img = None
            if hasattr(self, "info_label"):
                self.info_label.config(text="No image loaded.")
            # Reset sliders
            if hasattr(self, "threshold_var"):
                self.threshold_var.set(128)
            if hasattr(self, "gamma_var"):
                self.gamma_var.set(1.0)
        except Exception as e:
            print("Warning: reset_panel failed:", e)


    def ensure_image_loaded(self):
        """Check if main controller has a loaded image"""
        if hasattr(self.controller, "current_image") and self.controller.current_image is not None:
            return True
        messagebox.showerror("Error", "No image found. Please load one in the main window.")
        return False

    # POINT PROCESSING METHODS
    def apply_grayscale(self):
        if not self.ensure_image_loaded():
            return
        img = self.controller.current_image
        arr = np.array(img)
        gray = np.mean(arr, axis=2).astype(np.uint8)
        gray_img = Image.fromarray(gray)

        self.controller.current_image = gray_img
        self._update_display_image(gray_img)
        self._refresh_controller()
        self.info_label.config(text="Applied Grayscale Transformation.")

    def apply_negative(self):
        if not self.ensure_image_loaded():
            return
        img = np.array(self.controller.current_image)
        neg = 255 - img
        neg_img = Image.fromarray(neg.astype(np.uint8))
        self.controller.current_image = neg_img
        self._update_display_image(neg_img)
        self._refresh_controller()
        self.info_label.config(text="Applied Negative Transformation.")
            
    def apply_hist_eq(self):
        if not self.ensure_image_loaded():
            return

        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        import numpy as np
        from PIL import Image

        #  Convert to grayscale array 
        img = np.array(self.controller.current_image.convert("L"))

        #  Compute original histogram manually 
        hist, _ = np.histogram(img.flatten(), bins=256, range=[0, 256])

        # Compute PDF, CDF, and equalize manually 
        pdf = hist / np.sum(hist)
        cdf = np.cumsum(pdf)
        equalized = np.floor(255 * cdf[img]).astype(np.uint8)
        eq_img = Image.fromarray(equalized)

        #  Compute histogram after equalization 
        hist_eq, _ = np.histogram(equalized.flatten(), bins=256, range=[0, 256])

        #  Update GUI image 
        self.controller.current_image = eq_img
        self._update_display_image(eq_img)
        self._refresh_controller()
        self.info_label.config(text="Applied Histogram Equalization (with histograms below).")

        #  Clear old histograms from frame 
        for widget in self.hist_frame.winfo_children():
            widget.destroy()

        # Create a matplotlib Figure 
        fig = Figure(figsize=(6, 2.5))
        axs = fig.subplots(1, 2)

        # Original histogram
        axs[0].plot(hist, color='gray')
        axs[0].set_title("Original Histogram")
        axs[0].set_xlabel("Intensity")
        axs[0].set_ylabel("Frequency")

        # Equalized histogram
        axs[1].plot(hist_eq, color='black')
        axs[1].set_title("Equalized Histogram")
        axs[1].set_xlabel("Intensity")
        axs[1].set_ylabel("Frequency")

        fig.tight_layout()

        #Embed the figure under the image 
        canvas = FigureCanvasTkAgg(fig, master=self.hist_frame)
        canvas.draw()
        widget = canvas.get_tk_widget()
        widget.pack(pady=5)
        widget.update_idletasks()  


    # SLIDER HANDLERS
    def _apply_threshold(self, val):
        if not self.ensure_image_loaded():
            return
        try:
            base_img = self.controller.img_state.original_img
            if base_img is None:
                return
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
        if not self.ensure_image_loaded():
            return
        try:
            base_img = self.controller.img_state.original_img
            if base_img is None:
                return
            img_gray = np.array(base_img.convert("L"), dtype=np.float32) / 255.0
            gamma = float(val)
            corrected = np.power(img_gray, gamma)
            gamma_img = Image.fromarray((corrected * 255).astype(np.uint8))
            self.controller.current_image = gamma_img
            self._update_display_image(gamma_img)
            self._refresh_controller()
            self.info_label.config(text=f"Gamma: {gamma:.2f}")
        except Exception:
            pass

    # RESET
    def reset_image(self):
        if hasattr(self.controller.img_state, "original_img") and self.controller.img_state.original_img:
            self.controller.current_image = self.controller.img_state.original_img.copy()
            self.threshold_var.set(128)
            self.gamma_var.set(1.0)
            self._update_display_image(self.controller.current_image)
            self._refresh_controller()
            self.info_label.config(text="Image reset to original.")
        else:
            self.info_label.config(text="No original image to reset.")

    # REFRESH MAIN CONTROLLER
    def _refresh_controller(self):
        try:
            self.controller.update_preview()
            self.controller.channel_panel.show_channels(self.controller.current_image)
            self.controller.redraw()
        except Exception:
            pass

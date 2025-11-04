import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageFilter, ImageOps
import numpy as np
import cv2 

class ImageEnhancementPanel(ttk.Frame):
    """
    Image Enhancement in Spatial Domain Panel
    This class provides various spatial filtering operations to improve or modify
    image appearance and extract useful features.
    
    Spatial domain filtering modifies pixel intensity values directly using kernels 
    or masks. It’s widely used for smoothing (noise reduction) and sharpening (edge enhancement).
    
    Filters implemented:
    - Averaging (mean) filter
    - Median filter
    - Laplacian (highpass) filter
    - Unsharp masking
    - Highboost filter
    - Sobel gradient (edge detector)
    """

    def __init__(self, master, controller):
        super().__init__(master)
        self.controller = controller
        self.pack(fill="both", expand=True, padx=10, pady=10)

        ttk.Label(
            self,
            text="🧠 Image Enhancement in Spatial Domain",
            font=("Arial", 16, "bold"),
            foreground="#2B547E"
        ).pack(pady=10)

        # Button panel for selecting filters
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        # Filter buttons
        ttk.Button(btn_frame, text="Averaging Filter", command=self.apply_averaging).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Median Filter", command=self.apply_median).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Laplacian Highpass", command=self.apply_laplacian).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Unsharp Masking", command=self.apply_unsharp).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Sobel Gradient", command=self.apply_sobel).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_image).grid(row=1, column=2, padx=5, pady=5)

        # Highboost filtering slider control
        ttk.Label(self, text="Highboost Amplification (1.0–5.0)").pack(pady=(10, 0))
        self.boost_var = tk.DoubleVar(value=1.5)
        self.boost_slider = ttk.Scale(self, from_=1.0, to=5.0, orient="horizontal", variable=self.boost_var, command=self._apply_highboost)
        self.boost_slider.pack(fill="x", padx=20)

        # Image preview
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=10)

        self.info_label = ttk.Label(self, text="", foreground="gray")
        self.info_label.pack()

        self._update_display_image()

    # ===============================
    # DISPLAY UTILITIES
    # ===============================
    def _update_display_image(self, img=None):
        """Display the current processed image in the panel."""
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
        """Ensure an image is loaded before applying filters."""
        if hasattr(self.controller, "current_image") and self.controller.current_image is not None:
            return True
        messagebox.showerror("Error", "No image found. Please load one first.")
        return False

    # ===============================
    # FILTER IMPLEMENTATIONS
    # ===============================

    def apply_averaging(self):
        """
        Averaging (Mean) Filter
        - A low-pass filter that smooths the image by replacing each pixel value 
          with the average of its neighborhood.
        - Useful for reducing random noise.
        - Formula: g(x,y) = (1/N) * Σ f(s,t), where N = kernel size.
        """
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        kernel = np.ones((5,5), np.float32) / 25   # 5x5 kernel with equal weights
        avg = cv2.filter2D(img, -1, kernel)        # Convolution with the averaging kernel
        img_out = Image.fromarray(avg.astype(np.uint8))
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Averaging Filter (Smoothing).")
        self._refresh_controller()

    def apply_median(self):
        """
        Median Filter
        - Non-linear filter that replaces each pixel with the median of its neighborhood.
        - Extremely effective against salt-and-pepper (impulse) noise.
        - Preserves edges better than averaging filters.
        """
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        med = cv2.medianBlur(img, 5)   # 5x5 median kernel
        img_out = Image.fromarray(med)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Median Filter (Noise Reduction).")
        self._refresh_controller()

    def apply_laplacian(self):
        """
        Laplacian Highpass Filter
        - Second-order derivative operator that enhances edges and fine details.
        - Detects areas of rapid intensity change (edges).
        - Formula: ∇²f(x,y) = ∂²f/∂x² + ∂²f/∂y²
        """
        if not self.ensure_image_loaded(): return
        gray = cv2.cvtColor(np.array(self.controller.current_image), cv2.COLOR_RGB2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)  # Apply Laplacian operator using 3*3 kernel 4 neighnbor used
        lap = np.clip(lap, 0, 255).astype(np.uint8)
        img_out = Image.fromarray(lap)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Laplacian Highpass Filter (Edge Detection).")
        self._refresh_controller()

    def apply_unsharp(self):
        """
        Unsharp Masking
        - Sharpens an image by subtracting a blurred version from the original.
        - Formula: g(x,y) = f(x,y) + k * (f(x,y) - f_blur(x,y))
        - Enhances edges and details without amplifying noise excessively.
        """
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        blurred = cv2.GaussianBlur(img, (5,5), 1)
        unsharp = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)  # weighted combination
        img_out = Image.fromarray(unsharp)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Unsharp Masking (Edge Enhancement).")
        self._refresh_controller()

    def _apply_highboost(self, val):
        """
        Highboost Filtering
        - Generalized form of unsharp masking.
        - Formula: g(x,y) = A*f(x,y) - f_blur(x,y) = f(x,y) + (A-1)*(f(x,y)-f_blur(x,y))
        - The parameter A (>1) controls the amplification of high-frequency components.
        - When A=1 → Unsharp Mask; A>1 → Highboost.
        """
        if not self.ensure_image_loaded(): return
        try:
            A = float(val) # Amplification factor from slider (1-5)
            img = np.array(self.controller.img_state.original_img)
            blurred = cv2.GaussianBlur(img, (5,5), 1)
            mask = img - blurred                   # Extract high-frequency details
            highboost = np.clip(img + (A - 1) * mask, 0, 255)
            img_out = Image.fromarray(highboost.astype(np.uint8))
            self.controller.current_image = img_out
            self._update_display_image(img_out)
            self.info_label.config(text=f"Applied Highboost Filter (A={A:.2f}).")
            self._refresh_controller()
        except Exception:
            pass

    def apply_sobel(self):
        """
        Sobel Gradient Filter
        - First-order derivative operator used to detect edges in x and y directions.
        - Combines horizontal (Gx) and vertical (Gy) gradients:
          Gradient magnitude = sqrt(Gx² + Gy²)
        - Produces a strong response at object boundaries.
        """
        if not self.ensure_image_loaded(): return
        gray = cv2.cvtColor(np.array(self.controller.current_image), cv2.COLOR_RGB2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad = np.sqrt(sobelx**2 + sobely**2)
        grad = np.clip(grad, 0, 255).astype(np.uint8)
        img_out = Image.fromarray(grad)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Sobel Gradient (Edge Detection).")
        self._refresh_controller()

    # ===============================
    # RESET METHODS
    # ===============================

    def reset_image(self):
        """Restore the original unfiltered image."""
        if hasattr(self.controller.img_state, "original_img") and self.controller.img_state.original_img:
            self.controller.current_image = self.controller.img_state.original_img.copy()
            self.boost_var.set(1.5)
            self._update_display_image(self.controller.current_image)
            self.info_label.config(text="Reset to original image.")
            self._refresh_controller()
        else:
            self.info_label.config(text="No original image to reset.")

    def _refresh_controller(self):
        """Refresh other panels (e.g., channel preview, histogram) after filtering."""
        try:
            self.controller.update_preview()
            self.controller.channel_panel.show_channels(self.controller.current_image)
            self.controller.redraw()
        except Exception:
            pass

    def reset_panel(self):
        """Clear only the displayed image — don’t destroy the whole tab."""
        try:
            if hasattr(self, "image_label"):
                self.image_label.configure(image='', text="No image loaded.")
                self.image_label.image = None
            if hasattr(self, "photo"):
                self.photo = None
            if hasattr(self, "slider_var"):
                self.slider_var.set(1.0)
        except Exception as e:
            print("Warning: reset_panel failed in ImageEnhancementPanel:", e)

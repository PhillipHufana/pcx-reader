# image_enhancement_panel.py
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageFilter, ImageOps
import numpy as np
import cv2  # for Sobel and Laplacian

class ImageEnhancementPanel(ttk.Frame):
    """
    Image Enhancement in Spatial Domain Panel
    Features:
    - Averaging Filter
    - Median Filter
    - Highpass (Laplacian)
    - Unsharp Masking
    - Highboost Filtering
    - Gradient (Sobel)
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

        # --- BUTTON FRAME ---
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Averaging Filter", command=self.apply_averaging).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Median Filter", command=self.apply_median).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Laplacian Highpass", command=self.apply_laplacian).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Unsharp Masking", command=self.apply_unsharp).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Sobel Gradient", command=self.apply_sobel).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Reset", command=self.reset_image).grid(row=1, column=2, padx=5, pady=5)

        # --- Highboost Filter Slider ---
        ttk.Label(self, text="Highboost Amplification (1.0–5.0)").pack(pady=(10, 0))
        self.boost_var = tk.DoubleVar(value=1.5)
        self.boost_slider = ttk.Scale(self, from_=1.0, to=5.0, orient="horizontal", variable=self.boost_var, command=self._apply_highboost)
        self.boost_slider.pack(fill="x", padx=20)

        # --- IMAGE DISPLAY ---
        self.image_label = ttk.Label(self)
        self.image_label.pack(pady=10)

        # --- INFO LABEL ---
        self.info_label = ttk.Label(self, text="", foreground="gray")
        self.info_label.pack()

        self._update_display_image()

    # =========================================================
    # IMAGE DISPLAY UTILITIES
    # =========================================================
    def _update_display_image(self, img=None):
        """Display current or provided image"""
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
        if hasattr(self.controller, "current_image") and self.controller.current_image is not None:
            return True
        messagebox.showerror("Error", "No image found. Please load one first.")
        return False

    def reset_panel(self):
        """Reset display and slider"""
        self.image_label.config(image='', text="No image loaded.")
        self.boost_var.set(1.5)
        self.info_label.config(text="Panel reset.")

    # =========================================================
    # FILTER METHODS
    # =========================================================
    def apply_averaging(self):
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        kernel = np.ones((5,5), np.float32) / 25
        avg = cv2.filter2D(img, -1, kernel)
        img_out = Image.fromarray(avg.astype(np.uint8))
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Averaging Filter.")
        self._refresh_controller()

    def apply_median(self):
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        med = cv2.medianBlur(img, 5)
        img_out = Image.fromarray(med)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Median Filter.")
        self._refresh_controller()

    def apply_laplacian(self):
        if not self.ensure_image_loaded(): return
        gray = cv2.cvtColor(np.array(self.controller.current_image), cv2.COLOR_RGB2GRAY)
        lap = cv2.Laplacian(gray, cv2.CV_64F)
        lap = np.clip(lap, 0, 255).astype(np.uint8)
        img_out = Image.fromarray(lap)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Laplacian Highpass Filter.")
        self._refresh_controller()

    def apply_unsharp(self):
        if not self.ensure_image_loaded(): return
        img = np.array(self.controller.current_image)
        blurred = cv2.GaussianBlur(img, (5,5), 1)
        unsharp = cv2.addWeighted(img, 1.5, blurred, -0.5, 0)
        img_out = Image.fromarray(unsharp)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Unsharp Masking.")
        self._refresh_controller()

    def _apply_highboost(self, val):
        if not self.ensure_image_loaded(): return
        try:
            A = float(val)
            img = np.array(self.controller.img_state.original_img)
            blurred = cv2.GaussianBlur(img, (5,5), 1)
            mask = img - blurred
            highboost = np.clip(img + (A - 1) * mask, 0, 255)
            img_out = Image.fromarray(highboost.astype(np.uint8))
            self.controller.current_image = img_out
            self._update_display_image(img_out)
            self.info_label.config(text=f"Applied Highboost (A={A:.2f})")
            self._refresh_controller()
        except Exception:
            pass

    def apply_sobel(self):
        if not self.ensure_image_loaded(): return
        gray = cv2.cvtColor(np.array(self.controller.current_image), cv2.COLOR_RGB2GRAY)
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        grad = np.sqrt(sobelx**2 + sobely**2)
        grad = np.clip(grad, 0, 255).astype(np.uint8)
        img_out = Image.fromarray(grad)
        self.controller.current_image = img_out
        self._update_display_image(img_out)
        self.info_label.config(text="Applied Sobel Gradient.")
        self._refresh_controller()

    # =========================================================
    # RESET
    # =========================================================
    def reset_image(self):
        if hasattr(self.controller.img_state, "original_img") and self.controller.img_state.original_img:
            self.controller.current_image = self.controller.img_state.original_img.copy()
            self.boost_var.set(1.5)
            self._update_display_image(self.controller.current_image)
            self.info_label.config(text="Reset to original image.")
            self._refresh_controller()
        else:
            self.info_label.config(text="No original image to reset.")

    def _refresh_controller(self):
        try:
            self.controller.update_preview()
            self.controller.channel_panel.show_channels(self.controller.current_image)
            self.controller.redraw()
        except Exception:
            pass
        
    def reset_panel(self):
        """Clear only the displayed image — don't destroy the whole tab."""
        try:
            if hasattr(self, "image_label"):
                self.image_label.configure(image='', text="No image loaded.")
                self.image_label.image = None
            if hasattr(self, "photo"):
                self.photo = None
            # If you have sliders or entries, reset them here too:
            if hasattr(self, "slider_var"):
                self.slider_var.set(1.0)
        except Exception as e:
            print("Warning: reset_panel failed in ImageEnhancementPanel:", e)

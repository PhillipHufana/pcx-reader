import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class PointProcessingPanel(ttk.Frame):
    def __init__(self, master, controller=None):
        super().__init__(master)
        self.controller = controller
        self.img = None  # Will hold the input image
        self._build_ui()

    def _build_ui(self):
        """Build layout with controls on the left and output area on the right."""
        # Main layout: controls | preview
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="y", padx=10, pady=5)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        # === Control Buttons ===
        ttk.Label(left_frame, text="Point Processing Methods", font=("Arial", 11, "bold")).pack(pady=5)

        ttk.Button(left_frame, text="1️⃣ Grayscale", command=self.apply_grayscale).pack(fill="x", pady=3)
        ttk.Button(left_frame, text="2️⃣ Negative", command=self.apply_negative).pack(fill="x", pady=3)

        # --- Manual Threshold ---
        ttk.Label(left_frame, text="3️⃣ Manual Thresholding").pack(pady=(10, 0))
        self.threshold_var = tk.IntVar(value=128)
        ttk.Scale(left_frame, from_=0, to=255, orient="horizontal", variable=self.threshold_var).pack(fill="x")
        ttk.Button(left_frame, text="Apply Threshold", command=self.apply_threshold).pack(fill="x", pady=3)

        # --- Power-Law (Gamma) ---
        ttk.Label(left_frame, text="4️⃣ Power-Law (Gamma)").pack(pady=(10, 0))
        self.gamma_var = tk.DoubleVar(value=1.0)
        ttk.Scale(left_frame, from_=0.1, to=5.0, orient="horizontal", variable=self.gamma_var, length=150).pack(fill="x")
        ttk.Button(left_frame, text="Apply Gamma", command=self.apply_gamma).pack(fill="x", pady=3)

        # --- Histogram Equalization ---
        ttk.Button(left_frame, text="5️⃣ Histogram Equalization", command=self.apply_hist_eq).pack(fill="x", pady=(10, 3))

        # --- Reset ---
        ttk.Button(left_frame, text="🔄 Reset Image", command=self.reset_image).pack(fill="x", pady=(20, 3))

        # === Output Area ===
        self.output_label = ttk.Label(right_frame, text="Processed Image", font=("Arial", 10, "bold"))
        self.output_label.pack(pady=5)

        self.image_canvas = tk.Label(right_frame)
        self.image_canvas.pack(pady=5)

        # Histogram figure
        self.fig = Figure(figsize=(5, 3))
        self.ax = self.fig.add_subplot(111)
        self.hist_canvas = FigureCanvasTkAgg(self.fig, master=right_frame)
        self.hist_canvas.get_tk_widget().pack(fill="both", expand=True)

    # ---------------- IMAGE DISPLAY UTILS ----------------
    def set_image(self, img):
        """Set the working image (PIL)."""
        self.original_img = img.copy()
        self.img = img.copy()
        self.display_image_and_histogram(img)

    def display_image_and_histogram(self, img):
        """Update preview and histogram."""
        # Show image
        preview = img.resize((300, 300))
        photo = ImageTk.PhotoImage(preview)
        self.image_canvas.configure(image=photo)
        self.image_canvas.image = photo

        # Show histogram
        arr = np.array(img.convert("L")).flatten()
        self.ax.clear()
        self.ax.hist(arr, bins=256, color="gray")
        self.ax.set_xlim(0, 255)
        self.ax.set_title("Histogram")
        self.ax.set_xlabel("Intensity")
        self.ax.set_ylabel("Frequency")
        self.hist_canvas.draw()

    def reset_image(self):
        """Restore the original image."""
        if self.original_img is not None:
            self.img = self.original_img.copy()
            self.display_image_and_histogram(self.img)

# ---------------- POINT PROCESSING METHODS ----------------
    def apply_grayscale(self):
        gray = self.img.convert("L")
        self.display_image_and_histogram(gray)

    def apply_negative(self):
        arr = 255 - np.array(self.img)
        neg = Image.fromarray(arr.astype(np.uint8))
        self.display_image_and_histogram(neg)

    def apply_threshold(self):
        threshold = self.threshold_var.get()
        gray = self.img.convert("L")
        arr = np.array(gray)
        binary = np.where(arr >= threshold, 255, 0).astype(np.uint8)
        bw = Image.fromarray(binary, mode='L')
        self.display_image_and_histogram(bw)

    def apply_gamma(self):
        gamma = self.gamma_var.get()
        arr = np.array(self.img.convert("L")) / 255.0
        gamma_corrected = np.power(arr, gamma) * 255
        gamma_img = Image.fromarray(np.clip(gamma_corrected, 0, 255).astype(np.uint8))
        self.display_image_and_histogram(gamma_img)

    def apply_hist_eq(self):
        """Manual histogram equalization (step-by-step)."""
        gray = np.array(self.img.convert("L"))
        hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 255))
        pdf = hist / hist.sum()  # Step 3
        cdf = np.cumsum(pdf)  # Step 4
        eq_vals = np.floor(255 * cdf).astype(np.uint8)  # Step 5–6
        equalized = eq_vals[gray]
        eq_img = Image.fromarray(equalized)
        self.display_image_and_histogram(eq_img)
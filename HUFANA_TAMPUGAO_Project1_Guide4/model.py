from typing import Optional, Tuple, List, Dict, Any
from PIL.Image import Image as PILImage

class ImageState:
    """Holds the current image and UI-related state.
    """
    def __init__(self):
        # Core image objects
        self.img: Optional[PILImage] = None       
        self.tk_img: Optional[Any] = None       
        self.scale: float = 1.0
        self.img_item: Optional[int] = None
        self.disp_size: Tuple[int, int] = (0, 0)
        self.offset: Tuple[int, int] = (0, 0)
        self.fit_to_window: bool = True
        self.pan_anchor: Optional[Tuple[int, int]] = None
        self.allow_upscale: bool = False

        # File / metadata fields
        self.file_path: Optional[str] = None
        self.file_format: Optional[str] = None
        self.jpeg_exif: Optional[Dict[str, Any]] = None

        # PCX-specific fields
        self.pcx_header: Optional[Dict[str, Any]] = None
        self.pcx_palette: Optional[List[Tuple[int, int, int]]] = None

    @property
    def has_image(self) -> bool:
        """Return True when a PIL image is currently loaded."""
        return self.img is not None

    @property
    def has_pcx_palette(self) -> bool:
        """Return True when a 256-color PCX palette is available."""
        return bool(self.pcx_palette)

    def clear_image(self) -> None:
        """Clear image and display-related state (used by close_image)."""
        self.img = None
        self.tk_img = None
        self.img_item = None
        self.disp_size = (0, 0)
        self.offset = (0, 0)
        self.pan_anchor = None
        self.scale = 1.0
        self.fit_to_window = True

    def clear_metadata(self) -> None:
        """Clear file and PCX metadata (used by close_image)."""
        self.file_path = None
        self.file_format = None
        self.jpeg_exif = None
        self.pcx_header = None
        self.pcx_palette = None

    def clear_all(self) -> None:
        """Clear everything (image + metadata)."""
        self.clear_image()
        self.clear_metadata()

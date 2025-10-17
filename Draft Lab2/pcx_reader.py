
import struct
import os
import colorsys
from typing import Optional, List, Tuple, Dict, Any

try:
    from PIL import Image
except Exception:
    Image = None

PCX_HEADER_SIZE = 128
PCX_PALETTE_SIZE = 768
PCX_PALETTE_SIGNATURE_SIZE = 1
PCX_TAIL_SIZE = PCX_PALETTE_SIGNATURE_SIZE + PCX_PALETTE_SIZE  # 769


def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f'#{r:02x}{g:02x}{b:02x}'


def rgb_to_hsv(r: int, g: int, b: int):
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_n, g_n, b_n)
    return (round(h * 360), round(s * 100), round(v * 100))


def read_pcx_header(file_path: str) -> Dict[str, Any]:
    # Read the 128-byte PCX header and return a dictionary (
    header_data: Dict[str, Any] = {"File Path": file_path, "Error": "Unknown error"}
    try:
        with open(file_path, 'rb') as f:
            hdr = f.read(PCX_HEADER_SIZE)
            if len(hdr) < PCX_HEADER_SIZE:
                header_data["Error"] = "File too short to read full 128-byte header."
                return header_data

            unpacked = struct.unpack('<BBBB 4H 2H 48B B B H H 2H 54B', hdr)

            manufacturer = unpacked[0]
            version = unpacked[1]
            encoding = unpacked[2]
            bits_per_pixel = unpacked[3]
            xmin, ymin, xmax, ymax = unpacked[4], unpacked[5], unpacked[6], unpacked[7]
            h_dpi = unpacked[8]; v_dpi = unpacked[9]
            num_color_planes = unpacked[59]
            bytes_per_line = unpacked[60]
            palette_type = unpacked[61]
            h_screen_size = unpacked[62]; v_screen_size = unpacked[63]

            width = xmax - xmin + 1
            height = ymax - ymin + 1

            is_indexed = (num_color_planes == 1 and bits_per_pixel == 8)
            if is_indexed:
                palette_info = "256-Color (External)"
            elif bits_per_pixel <= 4 and num_color_planes == 1:
                palette_info = "16-Color (Internal)"
            elif bits_per_pixel == 8 and num_color_planes == 3:
                palette_info = "24-bit True Color"
            else:
                palette_info = "Custom/Unknown"

            header_data = {
                "Manufacturer": manufacturer,
                "Version": version,
                "Encoding": encoding,
                "Bits/Pixel": bits_per_pixel,
                "Dimensions": f"{width} x {height}",
                "Width": width,
                "Height": height,
                "H/V DPI": f"{h_dpi} / {v_dpi}",
                "Planes": num_color_planes,
                "Bytes/Line": bytes_per_line,
                "Palette Type": palette_type,
                "Palette Info": palette_info,
                "H Screen Size": h_screen_size,
                "V Screen Size": v_screen_size,
                "Is Indexed": is_indexed,
            }
    except struct.error as e:
        header_data["Error"] = f"Failed to unpack header: {e}"
    except Exception as e:
        header_data["Error"] = f"Unexpected error reading header: {e}"
    return header_data


def read_pcx_256_palette(file_path: str) -> Optional[List[Tuple[int, int, int]]]:
    # Read 256-color palette at end of file
    
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return None

    if size < PCX_HEADER_SIZE + PCX_TAIL_SIZE:
        return None

    # Read last 769 bytes sequentially 
    try:
        with open(file_path, 'rb') as f:
            f.seek(max(0, size - PCX_TAIL_SIZE))
            tail = f.read(PCX_TAIL_SIZE)
    except Exception:
        return None

    if len(tail) < PCX_PALETTE_SIZE + PCX_PALETTE_SIGNATURE_SIZE:
        return None

    sig = tail[0]
    palette_block = tail[1:1 + PCX_PALETTE_SIZE]

    # Strict case: signature present
    if sig == 0x0C:
        try:
            bytes_trip = struct.unpack('<768B', palette_block)
            return [(bytes_trip[i], bytes_trip[i + 1], bytes_trip[i + 2]) for i in range(0, 768, 3)]
        except struct.error:
            return None

    # Fallback heuristics: not all zeros and some variation
    if any(b != 0 for b in palette_block) and len(set(palette_block)) > 3:
        try:
            bytes_trip = struct.unpack('<768B', palette_block)
            return [(bytes_trip[i], bytes_trip[i + 1], bytes_trip[i + 2]) for i in range(0, 768, 3)]
        except struct.error:
            return None

    return None


def pcx_rle_decode(data: bytes) -> bytes:
    # Decode PCX RLE data. Returns decoded bytes
    out = bytearray()
    i = 0
    L = len(data)
    while i < L:
        b = data[i]
        if b >= 0xC0:
            count = b & 0x3F
            i += 1
            if i >= L:
                break
            val = data[i]
            out.extend([val] * count)
        else:
            out.append(b)
        i += 1
    return bytes(out)


def read_pcx(file_path: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {"header": None, "palette": None, "raw_pixels": None, "image": None}
    header = read_pcx_header(file_path)
    result["header"] = header
    if "Error" in header:
        return result

    try:
        size = os.path.getsize(file_path)
    except OSError:
        return result

    # Determine how many bytes are image data
    if size < PCX_HEADER_SIZE + PCX_TAIL_SIZE:
        return result

    image_data_size = size - PCX_HEADER_SIZE - PCX_TAIL_SIZE
    if image_data_size <= 0:
        return result

    # Read compressed image data sequentially 
    try:
        with open(file_path, 'rb') as f:
            # skip header
            f.read(PCX_HEADER_SIZE)
            remaining = image_data_size
            blocks = []
            block_size = 8192
            while remaining > 0:
                to_read = block_size if remaining >= block_size else remaining
                chunk = f.read(to_read)
                if not chunk:
                    break
                blocks.append(chunk)
                remaining -= len(chunk)
            compressed = b''.join(blocks)
    except Exception:
        return result

    if not compressed:
        return result

    decoded = pcx_rle_decode(compressed)
    result["raw_pixels"] = decoded
    # try to build palette & image when header indicates 8bpp, 1 plane
    palette = read_pcx_256_palette(file_path)
    result["palette"] = palette

    bits = header.get("Bits/Pixel")
    planes = header.get("Planes")
    bpl = header.get("Bytes/Line")
    width = header.get("Width")
    height = header.get("Height")

    if bits == 8 and planes == 1 and width and height and bpl:
        expected_len = bpl * height
        if len(decoded) >= expected_len:
            # Reconstruct pixel indices row-by-row using first `width` bytes of each scanline
            pixels = []
            off = 0
            for row in range(height):
                row_bytes = decoded[off: off + bpl]
                if len(row_bytes) < bpl:
                    break
                pixels.extend(row_bytes[:width])
                off += bpl

            if Image is not None:
                img = Image.new('P', (width, height))
                img.putdata(pixels)
                # attach palette if present
                if palette:
                    pal_flat = []
                    for (r, g, b) in palette:
                        pal_flat.extend((r, g, b))
                    if len(pal_flat) < 768:
                        pal_flat += [0] * (768 - len(pal_flat))
                    img.putpalette(pal_flat[:768])
                # Convert to RGB 
                try:
                    img_rgb = img.convert("RGB")
                except Exception:
                    img_rgb = None
                result["image"] = img_rgb
            else:
                # PIL not present; leave image None but raw_pixels + palette are available
                result["image"] = None

    # For non-standard formats (multi-plane, 24-bit, etc.) return header + raw_pixels + palette
    return result


import struct
import os
import colorsys
from typing import Optional, List, Tuple, Dict, Any

# optional dependency for building PIL images when requested
try:
    from PIL import Image
except Exception:
    Image = None  

PCX_HEADER_SIZE = 128
PCX_PALETTE_SIZE = 768
PCX_PALETTE_SIGNATURE_SIZE = 1
PCX_TAIL_SIZE = PCX_PALETTE_SIGNATURE_SIZE + PCX_PALETTE_SIZE  # 769


def rgb_to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'


def rgb_to_hsv(r, g, b):
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    return (round(h * 360), round(s * 100), round(v * 100))


def read_pcx_header(file_path: str) -> Dict[str, Any]:
    header_data = {"File Path": file_path, "Error": "Unknown error"}
    try:
        with open(file_path, 'rb') as f:
            header_bytes = f.read(PCX_HEADER_SIZE)
            if len(header_bytes) < PCX_HEADER_SIZE:
                header_data["Error"] = "File too short to read full 128-byte header."
                return header_data

            unpacked = struct.unpack('<BBBB 4H 2H 48B B B H H 2H 54B', header_bytes)
            manufacturer = unpacked[0]
            version = unpacked[1]
            encoding = unpacked[2]
            bits_per_pixel = unpacked[3]
            xmin = unpacked[4]
            ymin = unpacked[5]
            xmax = unpacked[6]
            ymax = unpacked[7]
            h_dpi = unpacked[8]
            v_dpi = unpacked[9]

            num_color_planes = unpacked[59]
            bytes_per_line = unpacked[60]
            palette_type = unpacked[61]
            h_screen_size = unpacked[62]
            v_screen_size = unpacked[63]

            width = xmax - xmin + 1
            height = ymax - ymin + 1

            is_indexed = num_color_planes == 1 and bits_per_pixel == 8

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
                "H/V DPI": f"{h_dpi} / {v_dpi}",
                "Planes": num_color_planes,
                "Bytes/Line": bytes_per_line,
                "Palette Type": palette_type,
                "Palette Info": palette_info,
                "H Screen Size": h_screen_size,
                "V Screen Size": v_screen_size,
                "Is Indexed": is_indexed,
                "Width": width,
                "Height": height,
            }

            if "Error" in header_data:
                del header_data["Error"]

    except struct.error as e:
        header_data["Error"] = f"Failed to unpack header structure: {e}"
    except Exception as e:
        header_data["Error"] = f"An unexpected error occurred during header read: {e}"

    return header_data


def read_pcx_256_palette(file_path: str) -> Optional[List[Tuple[int, int, int]]]:
   #Returns list of (r,g,b) tuples or None.
   
    required_tail = PCX_TAIL_SIZE  # 769
    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        return None

    if file_size < PCX_HEADER_SIZE + required_tail:
        return None

    tail = b''
    try:
        with open(file_path, 'rb') as f:
            chunk_size = 4096
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                if len(tail) + len(chunk) <= required_tail:
                    tail = tail + chunk
                else:
                    combined = tail + chunk
                    tail = combined[-required_tail:]

        if len(tail) < required_tail:
            return None

        signature = tail[0]
        if signature != 12:
            return None

        palette_bytes = tail[1:1 + PCX_PALETTE_SIZE]
        if len(palette_bytes) < PCX_PALETTE_SIZE:
            return None

        rgb_bytes = struct.unpack('<768B', palette_bytes)
        palette = []
        for i in range(0, PCX_PALETTE_SIZE, 3):
            palette.append((rgb_bytes[i], rgb_bytes[i + 1], rgb_bytes[i + 2]))

        return palette

    except Exception:
        return None


def pcx_rle_decode(data: bytes) -> bytes:

    # Decodes PCX RLE-compressed image data.

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
    try:
        file_size = os.path.getsize(file_path)
    except OSError:
        return result

    if "Error" in header:
        return result

    # compute how many bytes are image data 
    if file_size < PCX_HEADER_SIZE + PCX_TAIL_SIZE:
        return result

    image_data_size = file_size - PCX_HEADER_SIZE - PCX_TAIL_SIZE
    if image_data_size <= 0:
        return result

   
    try:
        with open(file_path, 'rb') as f:
            # consume header bytes
            _ = f.read(PCX_HEADER_SIZE)
            remaining = image_data_size
            chunks = []
            read_block = 8192
            while remaining > 0:
                to_read = read_block if remaining >= read_block else remaining
                chunk = f.read(to_read)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)

            compressed = b''.join(chunks)
            if len(compressed) == 0:
                return result

            decoded = pcx_rle_decode(compressed)
            result["raw_pixels"] = decoded

            # try to build PIL image for common cases
            bits_per_pixel = header.get("Bits/Pixel")
            planes = header.get("Planes")
            width = header.get("Width")
            height = header.get("Height")
            bytes_per_line = header.get("Bytes/Line")

            # read palette 
            palette = read_pcx_256_palette(file_path)
            result["palette"] = palette

            if bits_per_pixel == 8 and planes == 1 and width and height and bytes_per_line:
                # decoded should contain bytes_per_line * height bytes (per-plane)
                expected = bytes_per_line * height
                if len(decoded) < expected:
                   
                    return result

                # build pixel indices row by row 
                pixel_list = []
                offset = 0
                for row in range(height):
                    row_bytes = decoded[offset: offset + bytes_per_line]
                    if len(row_bytes) < bytes_per_line:
                    
                        break
                    pixel_list.extend(row_bytes[:width])
                    offset += bytes_per_line

                # create PIL image if PIL is available
                if Image is not None:
                    img = Image.new('P', (width, height))
                    img.putdata(pixel_list)
                    if palette:
                        # PIL expects flat list [r,g,b, r,g,b, ...]
                        pal_flat = []
                        for (r, g, b) in palette:
                            pal_flat.extend((r, g, b))
                        # ensure 768 length
                        if len(pal_flat) >= 768:
                            img.putpalette(pal_flat[:768])
                        else:
                            # pad with zeros if shorter for safety
                            img.putpalette(pal_flat + [0] * (768 - len(pal_flat)))
                    result["image"] = img
                else:
                    # PIL not available; user can use raw_pixels and palette
                    result["image"] = None

            # For other formats (e.g., 24-bit RGB interleaved planes), we return raw decoded bytes
            return result

    except Exception:
        return result

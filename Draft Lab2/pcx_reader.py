# file: pcx_utils.py
import struct
import os
import colorsys

PCX_HEADER_SIZE = 128
PCX_PALETTE_SIZE = 768
PCX_PALETTE_SIGNATURE_SIZE = 1

def rgb_to_hex(r, g, b):
    return f'#{r:02x}{g:02x}{b:02x}'

def rgb_to_hsv(r, g, b):
    r_norm, g_norm, b_norm = r / 255.0, g / 255.0, b / 255.0
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    return (round(h * 360), round(s * 100), round(v * 100))

def read_pcx_header(file_path):
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
            }

            if "Error" in header_data:
                del header_data["Error"]

    except struct.error as e:
        header_data["Error"] = f"Failed to unpack header structure: {e}"
        print(f"DEBUG: PCX Header Result: Failed to unpack header structure: {e}")
    except Exception as e:
        header_data["Error"] = f"An unexpected error occurred during header read: {e}"
        print(f"DEBUG: PCX Header Result: An unexpected error occurred: {e}")

    return header_data

def read_pcx_256_palette(file_path):
    """
    Read the 256-color palette (768 bytes) found at the end of the file
    without using file.seek(). This uses a rolling buffer to keep only the
    last 769 bytes (1 signature + 768 palette bytes).
    Returns a list of (R, G, B) tuples if found, otherwise None.
    """
    required_tail = PCX_PALETTE_SIZE + PCX_PALETTE_SIGNATURE_SIZE  # 769 bytes
    try:
        # quick file size check to short-circuit tiny files
        file_size = os.path.getsize(file_path)
    except OSError:
        return None

    if file_size < PCX_HEADER_SIZE + required_tail:
        # Not large enough to contain header + signature + palette
        return None

    # Stream through file, keeping only last `required_tail` bytes.
    tail = b''
    try:
        with open(file_path, 'rb') as f:
            chunk_size = 4096
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                # keep only the last `required_tail` bytes
                if len(tail) + len(chunk) <= required_tail:
                    tail = tail + chunk
                else:
                    # concatenate and slice to keep just the last required_tail bytes
                    combined = tail + chunk
                    tail = combined[-required_tail:]

        if len(tail) < required_tail:
            return None

        # signature is the first byte of the tail chunk (since tail holds last 769 bytes)
        signature = tail[0]
        if signature != 12:
            return None

        palette_bytes = tail[1:1 + PCX_PALETTE_SIZE]
        if len(palette_bytes) < PCX_PALETTE_SIZE:
            return None

        rgb_bytes = struct.unpack('<768B', palette_bytes)
        palette = []
        for i in range(0, PCX_PALETTE_SIZE, 3):
            palette.append((rgb_bytes[i], rgb_bytes[i+1], rgb_bytes[i+2]))

        return palette

    except struct.error as e:
        print(f"ERROR reading palette bytes: {e}")
        return None
    except Exception as e:
        print(f"ERROR during PCX palette read: {e}")
        return None

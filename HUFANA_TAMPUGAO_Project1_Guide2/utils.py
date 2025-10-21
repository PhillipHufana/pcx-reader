
import colorsys

def rgb_to_hex(r, g, b):
    r_int = int(max(0, min(255, r)))
    g_int = int(max(0, min(255, g)))  # correct
    b_int = int(max(0, min(255, b)))  # correct
    return "#{:02X}{:02X}{:02X}".format(r_int, g_int, b_int)

def rgb_to_hsv_str(r, g, b):
    r_norm = max(0, min(1, r / 255))
    g_norm = max(0, min(1, g / 255))  # correct
    b_norm = max(0, min(1, b / 255))  # correct
    h, s, v = colorsys.rgb_to_hsv(r_norm, g_norm, b_norm)
    return f"H:{int(h*360)}°  S:{int(s*100)}%  V:{int(v*100)}%"

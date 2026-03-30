"""Generate AMANDLA app icons for all platforms.

Creates a recognizable icon with two stylized hands forming a bridge/arc
motif — representing the communication bridge between hearing and deaf users.
Uses an accessible high-contrast colour palette.

Outputs:
  assets/icons/icon.png  — 512×512  (Linux + source)
  assets/icons/icon.ico  — multi-size 16–256 px  (Windows)
  assets/icons/icon.icns — multi-size  (macOS — best-effort, may need macOS)

Requirements:
  pip install Pillow

Usage:
  python scripts/generate_icons.py
"""

import math
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("ERROR: Pillow is required.  Install with:  pip install Pillow>=10.0")
    sys.exit(1)

# ── Colour palette (accessible, high contrast) ───────────────────────────
BG_DARK = (26, 35, 126)       # Deep indigo  #1A237E
BG_LIGHT = (40, 53, 147)      # Lighter indigo for gradient
HAND_COLOUR = (255, 214, 0)   # Gold/amber  #FFD600
ARC_COLOUR = (255, 255, 255)  # White
TEXT_COLOUR = (255, 255, 255)  # White

# ── Canvas size ──────────────────────────────────────────────────────────
SIZE = 512
CENTRE = SIZE // 2
MARGIN = 40


def _draw_gradient_circle(draw, size, colour_top, colour_bottom):
    """Draw a circular background with a vertical gradient.

    Args:
        draw:          ImageDraw instance.
        size:          Canvas width/height in pixels.
        colour_top:    RGB tuple for the top of the gradient.
        colour_bottom: RGB tuple for the bottom of the gradient.
    """
    centre = size // 2
    radius = centre - 4  # small padding from edge
    for y in range(size):
        # Interpolate between top and bottom colour based on y position
        blend = y / size
        r = int(colour_top[0] + (colour_bottom[0] - colour_top[0]) * blend)
        g = int(colour_top[1] + (colour_bottom[1] - colour_top[1]) * blend)
        b = int(colour_top[2] + (colour_bottom[2] - colour_top[2]) * blend)
        # Draw a horizontal line clipped to the circle
        dx = math.sqrt(max(0, radius * radius - (y - centre) ** 2))
        x0 = int(centre - dx)
        x1 = int(centre + dx)
        if x1 > x0:
            draw.line([(x0, y), (x1, y)], fill=(r, g, b))


def _draw_hand(draw, cx, cy, scale, mirror=False):
    """Draw a simplified open-hand silhouette.

    The hand is built from ellipses: one palm and five fingers.
    When mirror=True the hand is flipped horizontally.

    Args:
        draw:   ImageDraw instance.
        cx, cy: Centre position of the palm.
        scale:  Scaling factor (1.0 ≈ fits a 512px canvas).
        mirror: If True, flip the hand horizontally.
    """
    direction = -1 if mirror else 1

    # Palm (wide ellipse)
    palm_w = int(55 * scale)
    palm_h = int(65 * scale)
    draw.ellipse(
        [cx - palm_w, cy - palm_h, cx + palm_w, cy + palm_h],
        fill=HAND_COLOUR
    )

    # Finger definitions: (offset_x, offset_y, width, height) relative to palm centre
    # Thumb is wider and angled outward; other fingers point upward
    fingers = [
        (45 * direction,  -20, 18, 45),   # thumb (angled out)
        (25 * direction,  -75, 14, 50),   # index
        (5 * direction,   -85, 14, 52),   # middle (longest)
        (-15 * direction, -75, 13, 48),   # ring
        (-33 * direction, -60, 12, 40),   # pinky
    ]

    for (fx, fy, fw, fh) in fingers:
        sx = int(fx * scale)
        sy = int(fy * scale)
        sw = int(fw * scale)
        sh = int(fh * scale)
        draw.ellipse(
            [cx + sx - sw, cy + sy - sh, cx + sx + sw, cy + sy + sh],
            fill=HAND_COLOUR
        )


def _draw_arc(draw, size, scale):
    """Draw a connecting arc/bridge between the two hands.

    The arc is a thick curved line connecting the two palm positions,
    representing the communication bridge.

    Args:
        draw:  ImageDraw instance.
        size:  Canvas width/height in pixels.
        scale: Scaling factor.
    """
    centre = size // 2
    arc_width = int(6 * scale)
    arc_radius = int(120 * scale)
    y_offset = int(40 * scale)

    # Draw the arc as a series of points forming a smooth curve
    points = []
    for angle_deg in range(160, 381):
        angle = math.radians(angle_deg)
        x = centre + int(arc_radius * math.cos(angle))
        y = centre + y_offset + int(arc_radius * 0.6 * math.sin(angle))
        points.append((x, y))

    if len(points) >= 2:
        draw.line(points, fill=ARC_COLOUR, width=arc_width)


def _draw_text(draw, size, text, scale):
    """Draw the app name at the bottom of the icon.

    Args:
        draw:  ImageDraw instance.
        size:  Canvas width/height in pixels.
        text:  Text string to render.
        scale: Scaling factor.
    """
    font_size = int(36 * scale)
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2
    y = size - MARGIN - text_h
    draw.text((x, y), text, fill=TEXT_COLOUR, font=font)


def generate_icon(size=SIZE):
    """Generate the AMANDLA icon at the given size.

    Args:
        size: Width and height of the output image in pixels.

    Returns:
        PIL.Image.Image — the rendered icon.
    """
    scale = size / 512.0
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Background circle with gradient
    _draw_gradient_circle(draw, size, BG_LIGHT, BG_DARK)

    # Two open hands — left and right — reaching toward each other
    hand_y = int(size * 0.42)
    left_x = int(size * 0.32)
    right_x = int(size * 0.68)

    _draw_hand(draw, left_x, hand_y, scale, mirror=False)
    _draw_hand(draw, right_x, hand_y, scale, mirror=True)

    # Connecting arc/bridge between hands
    _draw_arc(draw, size, scale)

    # App name
    _draw_text(draw, size, "AMANDLA", scale)

    return img


def main():
    """Generate all icon formats and save to assets/icons/."""
    out_dir = os.path.join(os.path.dirname(__file__), "..", "assets", "icons")
    os.makedirs(out_dir, exist_ok=True)

    # ── 512×512 PNG (Linux + master source) ───────────────────────────
    icon_512 = generate_icon(512)
    png_path = os.path.join(out_dir, "icon.png")
    icon_512.save(png_path, "PNG")
    print(f"✓ Saved {png_path}  (512×512)")

    # ── Windows .ico (multi-size: 16, 32, 48, 64, 128, 256) ──────────
    ico_sizes = [16, 32, 48, 64, 128, 256]
    ico_images = [generate_icon(s).resize((s, s), Image.LANCZOS) for s in ico_sizes]
    ico_path = os.path.join(out_dir, "icon.ico")
    ico_images[0].save(
        ico_path, format="ICO",
        sizes=[(s, s) for s in ico_sizes],
        append_images=ico_images[1:]
    )
    print(f"✓ Saved {ico_path}  (sizes: {ico_sizes})")

    # ── macOS .icns (best-effort — Pillow may not support on Windows) ─
    icns_path = os.path.join(out_dir, "icon.icns")
    try:
        icon_512.save(icns_path, format="ICNS")
        print(f"✓ Saved {icns_path}  (macOS)")
    except Exception as exc:
        # Pillow on Windows cannot write ICNS — create a placeholder note
        print(f"⚠ Could not generate .icns ({exc})")
        print(f"  On macOS, run: iconutil -c icns icon.iconset")
        print(f"  Or use the .png file for macOS builds.")
        # Save a copy as fallback — electron-builder can use .png on macOS
        fallback_path = os.path.join(out_dir, "icon_macos.png")
        icon_512.save(fallback_path, "PNG")
        print(f"  Saved {fallback_path} as macOS fallback")

    # ── 1024×1024 for macOS iconset (optional) ────────────────────────
    icon_1024 = generate_icon(1024)
    large_path = os.path.join(out_dir, "icon_1024.png")
    icon_1024.save(large_path, "PNG")
    print(f"✓ Saved {large_path}  (1024×1024 for macOS iconset)")

    # ── Tray icon 32×32 ──────────────────────────────────────────────
    tray = generate_icon(32)
    tray_path = os.path.join(out_dir, "tray.png")
    tray.save(tray_path, "PNG")
    print(f"✓ Saved {tray_path}  (32×32 tray icon)")

    print(f"\nAll icons generated in {os.path.abspath(out_dir)}")


if __name__ == "__main__":
    main()


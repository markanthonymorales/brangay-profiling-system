"""
Davao City Barangay Profiling System logo/icon manager.
Uses the official Davao City seal (assets/davao_seal.png) if available,
otherwise generates a placeholder programmatically.
"""
import os
from PIL import Image, ImageDraw, ImageFont
from config import BASE_DIR

LOGO_DIR = os.path.join(BASE_DIR, "assets")
LOGO_PATH = os.path.join(LOGO_DIR, "logo.png")
ICON_PATH = os.path.join(LOGO_DIR, "icon.ico")
LOGO_SMALL_PATH = os.path.join(LOGO_DIR, "logo_small.png")
SEAL_SOURCE_PATH = os.path.join(LOGO_DIR, "davao_seal.png")


def generate_logo(size=256):
    """Generate logo files from the official Davao City seal, or create a placeholder."""
    os.makedirs(LOGO_DIR, exist_ok=True)

    if os.path.exists(SEAL_SOURCE_PATH):
        _generate_from_seal(size)
    else:
        _generate_placeholder(size)

    return LOGO_PATH, LOGO_SMALL_PATH, ICON_PATH


def _generate_from_seal(size=256):
    """Use the official Davao City seal image to create all logo variants."""
    seal = Image.open(SEAL_SOURCE_PATH).convert("RGBA")

    # Main logo (256x256)
    logo = seal.resize((size, size), Image.LANCZOS)
    logo.save(LOGO_PATH, "PNG")

    # Small logo for sidebar (48x48)
    logo_small = seal.resize((48, 48), Image.LANCZOS)
    logo_small.save(LOGO_SMALL_PATH, "PNG")

    # ICO for window icon (multiple sizes)
    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)]
    ico_images = []
    for s in ico_sizes:
        ico_img = seal.resize(s, Image.LANCZOS).convert("RGBA")
        ico_images.append(ico_img)

    ico_images[0].save(ICON_PATH, format="ICO", sizes=ico_sizes, append_images=ico_images[1:])


def _generate_placeholder(size=256):
    """Generate a placeholder seal if no official image is available."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    margin = 4

    # Outer ring (brown, like the real seal)
    draw.ellipse([margin, margin, size - margin, size - margin],
                 fill="#5C3317", outline="#DAA520", width=3)

    # Inner ring
    inner = margin + 14
    draw.ellipse([inner, inner, size - inner, size - inner],
                 fill="#003366", outline="#DAA520", width=2)

    # Center circle
    center_r = size // 2 - 42
    draw.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r],
                 fill="#87CEEB", outline="#DAA520", width=1)

    try:
        font_large = ImageFont.truetype("segoeuib.ttf", size // 7)
        font_small = ImageFont.truetype("segoeui.ttf", size // 11)
        font_tiny = ImageFont.truetype("segoeui.ttf", size // 15)
    except (OSError, IOError):
        try:
            font_large = ImageFont.truetype("arial.ttf", size // 7)
            font_small = ImageFont.truetype("arial.ttf", size // 11)
            font_tiny = ImageFont.truetype("arial.ttf", size // 15)
        except (OSError, IOError):
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()

    # Text
    draw.text((cx, inner + 10), "LUNGSOD NG", fill="#FFFFFF", font=font_tiny, anchor="mt")
    draw.text((cx, cy - 5), "DABAW", fill="#DAA520", font=font_large, anchor="mm")
    draw.text((cx, cy + size // 6), "SAGISAG", fill="#FFFFFF", font=font_small, anchor="mm")
    draw.text((cx, size - inner - 10), "DAVAO CITY", fill="#FFFFFF", font=font_tiny, anchor="mb")

    img.save(LOGO_PATH, "PNG")

    img_small = img.resize((48, 48), Image.LANCZOS)
    img_small.save(LOGO_SMALL_PATH, "PNG")

    ico_sizes = [(16, 16), (32, 32), (48, 48), (64, 64)]
    ico_images = [img.resize(s, Image.LANCZOS) for s in ico_sizes]
    ico_images[0].save(ICON_PATH, format="ICO", sizes=ico_sizes, append_images=ico_images[1:])


def get_logo_path():
    if not os.path.exists(LOGO_PATH):
        generate_logo()
    return LOGO_PATH


def get_logo_small_path():
    if not os.path.exists(LOGO_SMALL_PATH):
        generate_logo()
    return LOGO_SMALL_PATH


def get_icon_path():
    if not os.path.exists(ICON_PATH):
        generate_logo()
    return ICON_PATH


def update_from_image(image_path: str):
    """Update all logo files from a new source image."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found: {image_path}")

    os.makedirs(LOGO_DIR, exist_ok=True)

    # Copy as the seal source
    img = Image.open(image_path).convert("RGBA")
    img.save(SEAL_SOURCE_PATH, "PNG")

    # Regenerate all variants
    _generate_from_seal()
    print(f"Logo updated from: {image_path}")
    print(f"  Logo: {LOGO_PATH}")
    print(f"  Small: {LOGO_SMALL_PATH}")
    print(f"  Icon: {ICON_PATH}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        update_from_image(sys.argv[1])
    else:
        generate_logo()
        print(f"Logo generated at: {LOGO_PATH}")

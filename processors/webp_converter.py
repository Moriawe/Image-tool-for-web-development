"""
WebP Conversion Functions
"""
import re
from pathlib import Path
from PIL import Image, ImageOps


def sanitize_filename(name: str) -> str:
    """Clean and sanitize filename"""
    name = Path(name).stem
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    return name or "image"


def save_as_webp(file_storage, out_dir: Path, quality: int, lossless: bool):
    """Convert and save image as WebP format"""
    filename = sanitize_filename(file_storage.filename) + ".webp"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        
        # Convert appropriately for WebP
        if lossless:
            # Keep alpha if present
            if im.mode not in ("RGBA", "LA"):
                im = im.convert("RGBA")
            im.save(out_path, format="WEBP", lossless=True, method=6)
        else:
            # For lossy, WebP supports alpha if RGBA
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "A" in im.getbands() else "RGB")
            im.save(out_path, format="WEBP", quality=quality, method=6)

    return out_path.name, out_path.stat().st_size

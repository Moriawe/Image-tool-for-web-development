"""
Universal Image Format Converter for Web Development
Supports PNG, JPEG, WebP, and AVIF formats
"""
import re
from pathlib import Path
from PIL import Image, ImageOps
from .utils import sanitize_filename, get_file_extension, BYTES_PER_KB, WHITE_RGB


# Supported output formats for web
WEB_FORMATS = {
    "webp": {"ext": ".webp", "name": "WebP", "supports_lossless": True, "supports_alpha": True},
    "jpeg": {"ext": ".jpg", "name": "JPEG", "supports_lossless": False, "supports_alpha": False},
    "png": {"ext": ".png", "name": "PNG", "supports_lossless": True, "supports_alpha": True},
    "avif": {"ext": ".avif", "name": "AVIF", "supports_lossless": True, "supports_alpha": True}
}


def save_as_webp(file_storage, out_dir: Path, quality: int, lossless: bool):
    """Convert a single image to WebP format (legacy function for compatibility)"""
    result = convert_image_format(file_storage, out_dir, "webp", quality, lossless)
    return result["filename"], result["size_bytes"]


def convert_image_format(file_storage, out_dir: Path, output_format: str, quality: int = 85, lossless: bool = False):
    """Convert image to specified web format with optimization"""
    if output_format not in WEB_FORMATS:
        raise ValueError(f"Unsupported format: {output_format}")
    
    format_info = WEB_FORMATS[output_format]
    base_filename = sanitize_filename(file_storage.filename)
    filename = f"{base_filename}{format_info['ext']}"
    
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / filename

    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        original_size = im.size
        
        # Convert image based on output format
        converted_image = _convert_for_format(im, output_format, quality, lossless)
        
        # Save the image
        _save_image(converted_image, out_path, output_format, quality, lossless)
        
        # Calculate compression ratio
        file_size = out_path.stat().st_size
        
        return {
            "filename": filename,
            "size_bytes": file_size,
            "size_kb": round(file_size / BYTES_PER_KB, 1),
            "format": format_info["name"],
            "dimensions": f"{original_size[0]}x{original_size[1]}",
            "quality": quality if not lossless else "lossless",
            "has_alpha": _has_alpha_channel(converted_image)
        }


def _convert_for_format(image: Image.Image, output_format: str, quality: int, lossless: bool) -> Image.Image:
    """Convert image color mode based on target format requirements"""
    format_info = WEB_FORMATS[output_format]
    
    if output_format == "jpeg":
        # JPEG doesn't support transparency, convert to RGB with white background
        if image.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", image.size, WHITE_RGB)
            if image.mode == "P":
                image = image.convert("RGBA")
            background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
            return background
        elif image.mode != "RGB":
            return image.convert("RGB")
        return image
    
    elif output_format == "png":
        # PNG supports all modes, but optimize based on content
        if lossless or image.mode in ("RGBA", "LA", "P"):
            # Keep transparency for PNG
            if image.mode not in ("RGBA", "RGB", "L", "P"):
                return image.convert("RGBA")
            return image
        else:
            # For lossy PNG (though PNG is inherently lossless, we can optimize palette)
            if image.mode == "RGBA" and not _has_alpha_channel(image):
                return image.convert("RGB")
            return image
    
    elif output_format in ("webp", "avif"):
        # WebP and AVIF support both RGB and RGBA
        if lossless:
            # For lossless, preserve alpha if present
            if image.mode not in ("RGBA", "RGB", "L"):
                return image.convert("RGBA" if _has_alpha_channel(image) else "RGB")
            return image
        else:
            # For lossy, optimize mode
            if image.mode not in ("RGB", "RGBA"):
                return image.convert("RGBA" if _has_alpha_channel(image) else "RGB")
            return image
    
    return image


def _save_image(image: Image.Image, out_path: Path, output_format: str, quality: int, lossless: bool):
    """Save image with format-specific optimizations"""
    save_kwargs = {}
    
    if output_format == "webp":
        save_kwargs.update({
            "format": "WEBP",
            "method": 6,  # Best compression method
            "lossless": lossless
        })
        if not lossless:
            save_kwargs["quality"] = quality
    
    elif output_format == "jpeg":
        save_kwargs.update({
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
            "progressive": True  # Progressive JPEG for web
        })
    
    elif output_format == "png":
        save_kwargs.update({
            "format": "PNG",
            "optimize": True
        })
        if not lossless:
            # PNG is inherently lossless, but we can reduce colors for smaller size
            if image.mode == "RGB":
                save_kwargs["compress_level"] = 9  # Maximum compression
    
    elif output_format == "avif":
        try:
            save_kwargs.update({
                "format": "AVIF",
                "lossless": lossless
            })
            if not lossless:
                save_kwargs["quality"] = quality
        except Exception:
            # Fallback to WebP if AVIF not supported
            save_kwargs.update({
                "format": "WEBP",
                "method": 6,
                "lossless": lossless
            })
            if not lossless:
                save_kwargs["quality"] = quality
            # Update filename
            new_path = out_path.with_suffix(".webp")
            out_path.unlink(missing_ok=True)
            out_path = new_path
    
    image.save(out_path, **save_kwargs)


def _has_alpha_channel(image: Image.Image) -> bool:
    """Check if image has meaningful alpha channel"""
    return (
        image.mode in ("RGBA", "LA") and 
        (image.mode == "RGBA" or image.mode == "LA")
    )


def batch_convert_images(file_list, out_dir: Path, output_format: str, quality: int = 85, lossless: bool = False):
    """Convert multiple images to specified format"""
    results = []
    errors = []
    
    for file_storage in file_list:
        try:
            result = convert_image_format(file_storage, out_dir, output_format, quality, lossless)
            results.append(result)
        except Exception as e:
            errors.append({
                "filename": file_storage.filename,
                "error": str(e)
            })
    
    return results, errors


def get_format_comparison(file_storage, out_dir: Path, quality: int = 85):
    """Generate the same image in all formats for size comparison"""
    comparisons = {}
    
    for format_key, format_info in WEB_FORMATS.items():
        try:
            # Reset file stream position
            file_storage.stream.seek(0)
            result = convert_image_format(file_storage, out_dir, format_key, quality, False)
            comparisons[format_key] = result
        except Exception as e:
            comparisons[format_key] = {"error": str(e)}
    
    return comparisons

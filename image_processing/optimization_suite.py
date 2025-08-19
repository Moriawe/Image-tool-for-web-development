"""
Image Optimization Suite for Web Performance
Advanced optimization tools for reducing file sizes and improving web performance
"""
from pathlib import Path
from PIL import Image, ImageOps
from PIL.ExifTags import TAGS
import io
from .webp_converter import sanitize_filename, WEB_FORMATS, _convert_for_format, _save_image


# Optimization preset configurations
OPTIMIZATION_PRESETS = {
    "web_basic": {
        "name": "Web Basic",
        "description": "Standard web optimization",
        "max_width": 1920,
        "max_height": 1080,
        "quality": 85,
        "strip_metadata": True,
        "progressive": True,
        "optimize": True
    },
    "web_aggressive": {
        "name": "Web Aggressive",
        "description": "Maximum compression for fast loading",
        "max_width": 1600,
        "max_height": 900,
        "quality": 75,
        "strip_metadata": True,
        "progressive": True,
        "optimize": True
    },
    "social_media": {
        "name": "Social Media",
        "description": "Optimized for social platforms",
        "max_width": 1200,
        "max_height": 1200,
        "quality": 80,
        "strip_metadata": True,
        "progressive": True,
        "optimize": True
    },
    "email_friendly": {
        "name": "Email Friendly",
        "description": "Small files for email attachments",
        "max_width": 800,
        "max_height": 600,
        "quality": 70,
        "strip_metadata": True,
        "progressive": False,
        "optimize": True
    },
    "high_quality": {
        "name": "High Quality",
        "description": "Minimal compression, preserve quality",
        "max_width": 2560,
        "max_height": 1440,
        "quality": 95,
        "strip_metadata": False,
        "progressive": True,
        "optimize": True
    }
}


def optimize_image(file_storage, out_dir: Path, preset: str, output_format: str = "auto", 
                  custom_quality: int = None, custom_max_size: tuple = None):
    """
    Optimize image using predefined presets or custom settings
    """
    if preset not in OPTIMIZATION_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")
    
    preset_config = OPTIMIZATION_PRESETS[preset].copy()
    base_filename = sanitize_filename(file_storage.filename)
    
    # Override with custom settings if provided
    if custom_quality is not None:
        preset_config["quality"] = custom_quality
    if custom_max_size is not None:
        preset_config["max_width"], preset_config["max_height"] = custom_max_size
    
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        original_size = im.size
        original_mode = im.mode
        
        # Extract metadata before potential stripping
        metadata = extract_image_metadata(im) if not preset_config["strip_metadata"] else {}
        
        # Calculate size reduction if needed
        optimized_image = _resize_if_needed(im, preset_config["max_width"], preset_config["max_height"])
        
        # Determine output format
        if output_format == "auto":
            output_format = _determine_optimal_format(optimized_image, file_storage.filename)
        
        # Ensure format is supported
        if output_format not in WEB_FORMATS:
            output_format = "webp"  # Fallback to WebP
        
        format_info = WEB_FORMATS[output_format]
        filename = f"{base_filename}_optimized{format_info['ext']}"
        out_path = out_dir / filename
        
        # Convert for target format
        converted_image = _convert_for_format(optimized_image, output_format, preset_config["quality"], False)
        
        # Save with optimization settings
        _save_optimized_image(converted_image, out_path, output_format, preset_config)
        
        # Calculate compression statistics
        file_size = out_path.stat().st_size
        original_estimated_size = _estimate_original_size(im)
        compression_ratio = (1 - file_size / original_estimated_size) * 100 if original_estimated_size > 0 else 0
        
        return {
            "filename": filename,
            "size_bytes": file_size,
            "size_kb": round(file_size / 1024, 1),
            "format": format_info["name"],
            "original_dimensions": f"{original_size[0]}x{original_size[1]}",
            "optimized_dimensions": f"{converted_image.size[0]}x{converted_image.size[1]}",
            "original_mode": original_mode,
            "optimized_mode": converted_image.mode,
            "quality": preset_config["quality"],
            "preset": preset_config["name"],
            "compression_ratio": round(compression_ratio, 1),
            "metadata_stripped": preset_config["strip_metadata"],
            "progressive": preset_config.get("progressive", False),
            "metadata": metadata
        }


def batch_optimize_images(file_list, out_dir: Path, preset: str, output_format: str = "auto"):
    """
    Optimize multiple images with the same settings
    """
    results = []
    errors = []
    total_original_size = 0
    total_optimized_size = 0
    
    for file_storage in file_list:
        try:
            # Calculate original size for statistics
            original_size = len(file_storage.stream.read())
            file_storage.stream.seek(0)  # Reset stream
            total_original_size += original_size
            
            result = optimize_image(file_storage, out_dir, preset, output_format)
            results.append(result)
            total_optimized_size += result["size_bytes"]
            
        except Exception as e:
            errors.append({
                "filename": file_storage.filename,
                "error": str(e)
            })
    
    # Calculate batch statistics
    batch_stats = {
        "total_files": len(file_list),
        "successful": len(results),
        "failed": len(errors),
        "total_original_kb": round(total_original_size / 1024, 1),
        "total_optimized_kb": round(total_optimized_size / 1024, 1),
        "total_savings_kb": round((total_original_size - total_optimized_size) / 1024, 1),
        "overall_compression_ratio": round((1 - total_optimized_size / total_original_size) * 100, 1) if total_original_size > 0 else 0
    }
    
    return results, errors, batch_stats


def _resize_if_needed(image: Image.Image, max_width: int, max_height: int) -> Image.Image:
    """
    Resize image if it exceeds maximum dimensions while maintaining aspect ratio
    """
    width, height = image.size
    
    if width <= max_width and height <= max_height:
        return image
    
    # Calculate scaling factor to fit within max dimensions
    scale_w = max_width / width
    scale_h = max_height / height
    scale = min(scale_w, scale_h)
    
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)


def _determine_optimal_format(image: Image.Image, original_filename: str) -> str:
    """
    Automatically determine the best output format based on image characteristics
    """
    # Check if image has transparency
    has_alpha = image.mode in ("RGBA", "LA")
    
    # Check if image is likely a photo or graphic
    width, height = image.size
    total_pixels = width * height
    
    # Get original format for reference
    original_ext = Path(original_filename).suffix.lower()
    
    # Decision logic
    if has_alpha:
        # Images with transparency: WebP > PNG
        return "webp"
    elif total_pixels > 500000:  # Large images (likely photos)
        # Large photos: WebP > JPEG
        return "webp"
    elif original_ext in [".png"] and total_pixels < 100000:
        # Small graphics, keep as PNG for compatibility
        return "png"
    else:
        # Default to WebP for best compression
        return "webp"


def _save_optimized_image(image: Image.Image, out_path: Path, output_format: str, config: dict):
    """
    Save image with optimization-specific settings
    """
    save_kwargs = {}
    
    if output_format == "webp":
        save_kwargs.update({
            "format": "WEBP",
            "method": 6,  # Best compression method
            "quality": config["quality"],
            "optimize": config["optimize"]
        })
    
    elif output_format == "jpeg":
        save_kwargs.update({
            "format": "JPEG",
            "quality": config["quality"],
            "optimize": config["optimize"],
            "progressive": config.get("progressive", True)
        })
    
    elif output_format == "png":
        save_kwargs.update({
            "format": "PNG",
            "optimize": config["optimize"],
            "compress_level": 9
        })
    
    elif output_format == "avif":
        try:
            save_kwargs.update({
                "format": "AVIF",
                "quality": config["quality"]
            })
        except Exception:
            # Fallback to WebP
            save_kwargs.update({
                "format": "WEBP",
                "method": 6,
                "quality": config["quality"],
                "optimize": config["optimize"]
            })
            # Update path extension
            out_path = out_path.with_suffix(".webp")
    
    # Strip metadata if requested
    if config.get("strip_metadata", True):
        # Create new image without EXIF data
        if image.mode == "RGBA":
            clean_image = Image.new("RGBA", image.size)
            clean_image.paste(image, (0, 0))
        else:
            clean_image = Image.new(image.mode, image.size)
            clean_image.paste(image, (0, 0))
        clean_image.save(out_path, **save_kwargs)
    else:
        image.save(out_path, **save_kwargs)


def _estimate_original_size(image: Image.Image) -> int:
    """
    Estimate the file size of the original image for comparison
    """
    # Save to memory to get approximate size
    with io.BytesIO() as buffer:
        # Use PNG for accurate size estimation (lossless)
        image.save(buffer, format="PNG")
        return buffer.tell()


def extract_image_metadata(image: Image.Image) -> dict:
    """
    Extract useful metadata from image
    """
    metadata = {
        "format": image.format,
        "mode": image.mode,
        "size": image.size,
        "has_exif": hasattr(image, '_getexif') and image._getexif() is not None
    }
    
    # Extract EXIF data if present
    if hasattr(image, '_getexif') and image._getexif():
        exif_dict = image._getexif()
        if exif_dict:
            exif_data = {}
            for tag_id, value in exif_dict.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag in ["DateTime", "Make", "Model", "Software", "ImageWidth", "ImageLength"]:
                    exif_data[tag] = str(value)
            metadata["exif"] = exif_data
    
    return metadata


def analyze_image_complexity(image: Image.Image) -> dict:
    """
    Analyze image complexity to suggest optimal compression settings
    """
    # Convert to RGB for analysis
    if image.mode != "RGB":
        rgb_image = image.convert("RGB")
    else:
        rgb_image = image
    
    # Sample the image for analysis (for performance)
    sample_size = min(image.size[0], image.size[1], 200)
    sample = rgb_image.resize((sample_size, sample_size), Image.Resampling.LANCZOS)
    
    # Calculate color statistics
    pixels = list(sample.getdata())
    
    # Calculate color variation
    r_values = [p[0] for p in pixels]
    g_values = [p[1] for p in pixels]
    b_values = [p[2] for p in pixels]
    
    r_range = max(r_values) - min(r_values)
    g_range = max(g_values) - min(g_values)
    b_range = max(b_values) - min(b_values)
    
    avg_range = (r_range + g_range + b_range) / 3
    
    # Determine complexity
    if avg_range < 50:
        complexity = "low"
        suggested_quality = 70
    elif avg_range < 150:
        complexity = "medium"
        suggested_quality = 80
    else:
        complexity = "high"
        suggested_quality = 90
    
    return {
        "complexity": complexity,
        "color_range": round(avg_range, 1),
        "suggested_quality": suggested_quality,
        "is_likely_photo": avg_range > 100,
        "total_pixels": image.size[0] * image.size[1]
    }


def generate_optimization_report(results: list, batch_stats: dict = None) -> dict:
    """
    Generate a comprehensive optimization report
    """
    if not results:
        return {"error": "No results to analyze"}
    
    # Calculate aggregate statistics
    total_files = len(results)
    total_original_kb = sum(r.get("size_kb", 0) for r in results)
    avg_compression = sum(r.get("compression_ratio", 0) for r in results) / total_files
    
    # Format breakdown
    format_breakdown = {}
    for result in results:
        fmt = result.get("format", "Unknown")
        if fmt not in format_breakdown:
            format_breakdown[fmt] = {"count": 0, "total_kb": 0}
        format_breakdown[fmt]["count"] += 1
        format_breakdown[fmt]["total_kb"] += result.get("size_kb", 0)
    
    # Quality distribution
    quality_distribution = {}
    for result in results:
        quality = result.get("quality", "Unknown")
        quality_distribution[quality] = quality_distribution.get(quality, 0) + 1
    
    report = {
        "summary": {
            "total_files": total_files,
            "total_size_kb": round(total_original_kb, 1),
            "average_compression_ratio": round(avg_compression, 1),
            "formats_used": list(format_breakdown.keys())
        },
        "format_breakdown": format_breakdown,
        "quality_distribution": quality_distribution,
        "batch_stats": batch_stats
    }
    
    return report

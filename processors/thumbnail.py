"""
Thumbnail Generation Functions
"""
from pathlib import Path
from PIL import Image, ImageOps
from .webp_converter import sanitize_filename

# Common thumbnail sizes
THUMBNAIL_SIZES = {
    "small": (150, 150),
    "medium": (300, 300),
    "large": (500, 500),
    "profile": (128, 128),
    "gallery": (200, 200),
    "card": (350, 350)
}

CROP_METHODS = {
    "center": "center",
    "smart": "smart",
    "top": "top",
    "bottom": "bottom"
}


def generate_thumbnails(file_storage, out_dir: Path, quality: int, lossless: bool, 
                       selected_sizes: list, crop_method: str = "center", 
                       format_type: str = "webp"):
    """Generate square thumbnails from images"""
    base_filename = sanitize_filename(file_storage.filename)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        original_width, original_height = im.size
        
        for size_name in selected_sizes:
            if size_name not in THUMBNAIL_SIZES:
                continue
                
            target_size = THUMBNAIL_SIZES[size_name]
            target_width, target_height = target_size
            
            # Create thumbnail with different cropping methods
            thumbnail = create_thumbnail(im, target_size, crop_method)
            
            # Generate filename with size suffix
            extension = "webp" if format_type == "webp" else "jpg"
            filename = f"{base_filename}-thumb-{size_name}-{target_width}x{target_height}.{extension}"
            out_path = out_dir / filename
            
            # Save thumbnail
            if format_type == "webp":
                if lossless:
                    if thumbnail.mode not in ("RGBA", "LA"):
                        thumbnail = thumbnail.convert("RGBA")
                    thumbnail.save(out_path, format="WEBP", lossless=True, method=6)
                else:
                    if thumbnail.mode not in ("RGB", "RGBA"):
                        thumbnail = thumbnail.convert("RGBA" if "A" in thumbnail.getbands() else "RGB")
                    thumbnail.save(out_path, format="WEBP", quality=quality, method=6)
            else:  # JPEG
                if thumbnail.mode in ("RGBA", "LA"):
                    # Convert to RGB for JPEG (no alpha support)
                    background = Image.new("RGB", thumbnail.size, (255, 255, 255))
                    background.paste(thumbnail, mask=thumbnail.split()[-1] if thumbnail.mode == "RGBA" else None)
                    thumbnail = background
                thumbnail.save(out_path, format="JPEG", quality=quality, optimize=True)
            
            results.append({
                "name": filename,
                "size_kb": round(out_path.stat().st_size / 1024, 1),
                "dimensions": f"{target_width}x{target_height}",
                "size_name": size_name,
                "crop_method": crop_method
            })
    
    return results


def create_thumbnail(image, target_size, crop_method):
    """Create a square thumbnail with specified cropping method"""
    target_width, target_height = target_size
    original_width, original_height = image.size
    
    if crop_method == "center":
        # Standard center crop
        return ImageOps.fit(image, target_size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    
    elif crop_method == "smart":
        # Smart crop - try to detect interesting content
        # For now, use center crop with slight bias towards upper portion
        return ImageOps.fit(image, target_size, Image.Resampling.LANCZOS, centering=(0.5, 0.4))
    
    elif crop_method == "top":
        # Crop from the top
        return ImageOps.fit(image, target_size, Image.Resampling.LANCZOS, centering=(0.5, 0.0))
    
    elif crop_method == "bottom":
        # Crop from the bottom
        return ImageOps.fit(image, target_size, Image.Resampling.LANCZOS, centering=(0.5, 1.0))
    
    else:
        # Default to center
        return ImageOps.fit(image, target_size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def generate_thumbnail_css(results, base_url="/output/"):
    """Generate CSS examples for using thumbnails"""
    if not results:
        return ""
    
    css_examples = []
    
    # Group by size for CSS classes
    size_groups = {}
    for item in results:
        size_name = item["size_name"]
        if size_name not in size_groups:
            size_groups[size_name] = []
        size_groups[size_name].append(item)
    
    # Generate CSS for each size
    for size_name, items in size_groups.items():
        if items:
            dimensions = items[0]["dimensions"]
            width, height = dimensions.split("x")
            
            css = f'''.thumbnail-{size_name} {{
    width: {width}px;
    height: {height}px;
    object-fit: cover;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}

.thumbnail-{size_name}:hover {{
    transform: scale(1.05);
    transition: transform 0.2s ease;
}}'''
            css_examples.append(css)
    
    return css_examples

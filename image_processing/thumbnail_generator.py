"""
Thumbnail generation utilities
"""
from pathlib import Path
from PIL import Image, ImageOps
from .webp_converter import sanitize_filename


# Common thumbnail sizes for web development
THUMBNAIL_SIZES = {
    "tiny": (64, 64),      # Profile pictures, small icons
    "small": (128, 128),   # User avatars, small cards
    "medium": (256, 256),  # Gallery thumbnails, medium cards
    "large": (384, 384),   # Large previews, hero thumbnails
    "gallery": (512, 512), # Gallery displays, detailed previews
    "xl": (768, 768)       # High-res thumbnails, modal previews
}

# Crop methods for thumbnails
CROP_METHODS = {
    "center": "center",
    "top": "top", 
    "bottom": "bottom",
    "left": "left",
    "right": "right"
}


def generate_thumbnails(file_storage, out_dir: Path, quality: int, lossless: bool, 
                       selected_sizes: list, crop_method: str, output_format: str):
    """Generate square thumbnails with smart cropping for all web formats"""
    from .webp_converter import WEB_FORMATS, _convert_for_format, _save_image
    
    if output_format not in WEB_FORMATS:
        raise ValueError(f"Unsupported format: {output_format}")
    
    base_filename = sanitize_filename(file_storage.filename)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    format_info = WEB_FORMATS[output_format]
    
    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        original_width, original_height = im.size
        
        for size_name in selected_sizes:
            if size_name not in THUMBNAIL_SIZES:
                continue
                
            target_size = THUMBNAIL_SIZES[size_name]
            target_width, target_height = target_size
            
            # Create square thumbnail with cropping
            thumbnail = create_square_thumbnail(im, target_width, crop_method)
            
            # Convert for target format
            converted_thumbnail = _convert_for_format(thumbnail, output_format, quality, lossless)
            
            # Generate filename with size and crop info
            filename = f"{base_filename}-thumb-{size_name}-{target_width}x{target_height}-{crop_method}{format_info['ext']}"
            out_path = out_dir / filename
            
            # Save thumbnail using the universal save function
            _save_image(converted_thumbnail, out_path, output_format, quality, lossless)
            
            results.append({
                "name": filename,
                "size_kb": round(out_path.stat().st_size / 1024, 1),
                "dimensions": f"{target_width}x{target_height}",
                "size_name": size_name,
                "crop_method": crop_method,
                "format": format_info["name"]
            })
    
    return results


def create_square_thumbnail(image, size, crop_method):
    """Create a square thumbnail using the specified crop method"""
    original_width, original_height = image.size
    
    # Calculate the size for cropping to square
    crop_size = min(original_width, original_height)
    
    # Calculate crop box based on method
    if crop_method == "center":
        left = (original_width - crop_size) // 2
        top = (original_height - crop_size) // 2
    elif crop_method == "top":
        left = (original_width - crop_size) // 2
        top = 0
    elif crop_method == "bottom":
        left = (original_width - crop_size) // 2
        top = original_height - crop_size
    elif crop_method == "left":
        left = 0
        top = (original_height - crop_size) // 2
    elif crop_method == "right":
        left = original_width - crop_size
        top = (original_height - crop_size) // 2
    else:  # Default to center
        left = (original_width - crop_size) // 2
        top = (original_height - crop_size) // 2
    
    # Crop to square
    right = left + crop_size
    bottom = top + crop_size
    cropped = image.crop((left, top, right, bottom))
    
    # Resize to target size
    thumbnail = cropped.resize((size, size), Image.Resampling.LANCZOS)
    
    return thumbnail


def generate_thumbnail_css(results):
    """Generate CSS examples for thumbnails"""
    if not results:
        return []
    
    css_examples = []
    
    # Group by size
    sizes = {}
    for item in results:
        size_name = item["size_name"]
        if size_name not in sizes:
            sizes[size_name] = []
        sizes[size_name].append(item)
    
    # Generate CSS for each size
    for size_name, items in sizes.items():
        if items:
            dimensions = items[0]["dimensions"]
            width, height = dimensions.split("x")
            
            css = f""".thumbnail-{size_name} {{
    width: {width}px;
    height: {height}px;
    object-fit: cover;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}}

.thumbnail-{size_name}:hover {{
    transform: scale(1.05);
    transition: transform 0.2s ease;
}}"""
            css_examples.append(css)
    
    return css_examples


def generate_thumbnail_html(results):
    """Generate HTML usage examples for thumbnails"""
    if not results:
        return []
    
    html_examples = []
    
    # Group by size
    sizes = {}
    for item in results:
        size_name = item["size_name"]
        if size_name not in sizes:
            sizes[size_name] = []
        sizes[size_name].append(item)
    
    # Gallery grid example
    if "medium" in sizes:
        medium_thumbs = sizes["medium"][:4]  # Show first 4 as example
        gallery_html = """<div class="thumbnail-gallery">
"""
        for item in medium_thumbs:
            gallery_html += f'  <img src="{item["name"]}" class="thumbnail-medium" alt="Gallery thumbnail" />\n'
        gallery_html += """</div>

<style>
.thumbnail-gallery {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(256px, 1fr));
    gap: 1rem;
    padding: 1rem;
}
</style>"""
        html_examples.append(gallery_html)
    
    # Profile picture example
    if "small" in sizes:
        small_item = sizes["small"][0]
        profile_html = f"""<div class="user-profile">
  <img src="{small_item["name"]}" class="thumbnail-small user-avatar" alt="User avatar" />
  <div class="user-info">
    <h3>User Name</h3>
    <p>User bio text here...</p>
  </div>
</div>

<style>
.user-profile {{
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1rem;
}}

.user-avatar {{
    border-radius: 50%;
}}
</style>"""
        html_examples.append(profile_html)
    
    return html_examples

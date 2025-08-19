"""
Responsive Image Generation Functions
"""
from pathlib import Path
from PIL import Image, ImageOps
from .webp_converter import sanitize_filename

# Common responsive breakpoints for web development
RESPONSIVE_SIZES = {
    "mobile": 320,
    "mobile-large": 480,
    "tablet": 768,
    "desktop": 1024,
    "desktop-large": 1440,
    "desktop-xl": 1920
}


def generate_responsive_images(file_storage, out_dir: Path, quality: int, lossless: bool, selected_sizes: list):
    """Generate multiple sizes of an image for responsive web design"""
    base_filename = sanitize_filename(file_storage.filename)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        original_width, original_height = im.size
        
        for size_name in selected_sizes:
            if size_name not in RESPONSIVE_SIZES:
                continue
                
            target_width = RESPONSIVE_SIZES[size_name]
            
            # Skip if target size is larger than original
            if target_width >= original_width:
                continue
                
            # Calculate proportional height
            ratio = target_width / original_width
            target_height = int(original_height * ratio)
            
            # Resize image
            resized = im.resize((target_width, target_height), Image.Resampling.LANCZOS)
            
            # Generate filename with size suffix
            filename = f"{base_filename}-{size_name}-{target_width}w.webp"
            out_path = out_dir / filename
            
            # Save as WebP
            if lossless:
                if resized.mode not in ("RGBA", "LA"):
                    resized = resized.convert("RGBA")
                resized.save(out_path, format="WEBP", lossless=True, method=6)
            else:
                if resized.mode not in ("RGB", "RGBA"):
                    resized = resized.convert("RGBA" if "A" in resized.getbands() else "RGB")
                resized.save(out_path, format="WEBP", quality=quality, method=6)
            
            results.append({
                "name": filename,
                "size_kb": round(out_path.stat().st_size / 1024, 1),
                "dimensions": f"{target_width}x{target_height}",
                "size_name": size_name
            })
    
    return results


def generate_srcset_html(results):
    """Generate HTML srcset example from responsive images"""
    if not results:
        return ""
    
    # Group by base filename
    grouped = {}
    for item in results:
        base_name = item["name"].split("-")[0]  # Get base filename
        if base_name not in grouped:
            grouped[base_name] = []
        grouped[base_name].append(item)
    
    html_examples = []
    for base_name, items in grouped.items():
        # Sort by width
        items.sort(key=lambda x: int(x["dimensions"].split("x")[0]))
        
        srcset_parts = []
        for item in items:
            width = item["dimensions"].split("x")[0]
            srcset_parts.append(f"{item['name']} {width}w")
        
        srcset = ", ".join(srcset_parts)
        largest_item = items[-1]  # Fallback to largest image
        
        html = f'''<img src="{largest_item['name']}" 
     srcset="{srcset}"
     sizes="(max-width: 480px) 320px, (max-width: 768px) 480px, (max-width: 1024px) 768px, 1024px"
     alt="Responsive image" />'''
        
        html_examples.append(html)
    
    return html_examples

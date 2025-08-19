"""
Favicon generation utilities for web development
Creates multiple favicon formats and sizes for modern browsers
"""
from pathlib import Path
from PIL import Image, ImageOps
from .webp_converter import sanitize_filename


# Standard favicon sizes for modern web browsers
FAVICON_SIZES = {
    "ico_16": (16, 16),      # Traditional favicon.ico small
    "ico_32": (32, 32),      # Traditional favicon.ico medium  
    "ico_48": (48, 48),      # Traditional favicon.ico large
    "png_32": (32, 32),      # Standard favicon
    "png_64": (64, 64),      # High-DPI favicon
    "png_128": (128, 128),   # Chrome Web Store
    "png_180": (180, 180),   # Apple Touch Icon
    "png_192": (192, 192),   # Android Chrome
    "png_512": (512, 512),   # Android Chrome (high-res)
}

# Favicon file specifications
FAVICON_SPECS = {
    "ico_16": {"format": "ICO", "filename": "favicon-16x16.ico"},
    "ico_32": {"format": "ICO", "filename": "favicon-32x32.ico"},
    "ico_48": {"format": "ICO", "filename": "favicon-48x48.ico"},
    "png_32": {"format": "PNG", "filename": "favicon-32x32.png"},
    "png_64": {"format": "PNG", "filename": "favicon-64x64.png"},
    "png_128": {"format": "PNG", "filename": "favicon-128x128.png"},
    "png_180": {"format": "PNG", "filename": "apple-touch-icon.png"},
    "png_192": {"format": "PNG", "filename": "android-chrome-192x192.png"},
    "png_512": {"format": "PNG", "filename": "android-chrome-512x512.png"},
}


def generate_favicons(file_storage, out_dir: Path, selected_sizes: list, background_color: str = "transparent"):
    """Generate favicons in multiple sizes and formats"""
    base_filename = sanitize_filename(file_storage.filename)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        original_size = im.size
        
        # Convert to RGBA for consistent processing
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        
        for size_key in selected_sizes:
            if size_key not in FAVICON_SIZES:
                continue
                
            target_size = FAVICON_SIZES[size_key]
            spec = FAVICON_SPECS[size_key]
            
            # Create favicon with background handling
            favicon = create_favicon(im, target_size, background_color)
            
            # Generate filename
            filename = spec["filename"]
            out_path = out_dir / filename
            
            # Save favicon
            save_favicon(favicon, out_path, spec["format"])
            
            results.append({
                "name": filename,
                "size_kb": round(out_path.stat().st_size / 1024, 1),
                "dimensions": f"{target_size[0]}x{target_size[1]}",
                "format": spec["format"],
                "size_key": size_key,
                "purpose": get_favicon_purpose(size_key)
            })
    
    return results


def create_favicon(image: Image.Image, target_size: tuple, background_color: str = "transparent"):
    """Create a favicon with proper sizing and background handling"""
    target_width, target_height = target_size
    
    # Calculate scaling to fit within target size while maintaining aspect ratio
    original_width, original_height = image.size
    scale = min(target_width / original_width, target_height / original_height)
    
    # Calculate new size maintaining aspect ratio
    new_width = int(original_width * scale)
    new_height = int(original_height * scale)
    
    # Resize the image
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # Create final favicon with background
    if background_color.lower() == "transparent":
        # Create transparent background
        favicon = Image.new("RGBA", target_size, (0, 0, 0, 0))
    else:
        # Parse background color
        if background_color.startswith("#"):
            # Hex color
            bg_color = tuple(int(background_color[i:i+2], 16) for i in (1, 3, 5))
            favicon = Image.new("RGB", target_size, bg_color)
        else:
            # Named color or default to white
            favicon = Image.new("RGB", target_size, background_color if background_color else "white")
    
    # Center the resized image on the background
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    
    if favicon.mode == "RGBA" and resized.mode == "RGBA":
        favicon.paste(resized, (x_offset, y_offset), resized)
    else:
        # Convert to same mode for pasting
        if favicon.mode != resized.mode:
            if favicon.mode == "RGB":
                resized = resized.convert("RGB")
            else:
                favicon = favicon.convert("RGBA")
        favicon.paste(resized, (x_offset, y_offset))
    
    return favicon


def save_favicon(image: Image.Image, out_path: Path, format_type: str):
    """Save favicon with format-specific optimizations"""
    if format_type == "ICO":
        # ICO format
        image.save(out_path, format="ICO", optimize=True)
    elif format_type == "PNG":
        # PNG format with optimization
        image.save(out_path, format="PNG", optimize=True, compress_level=9)


def get_favicon_purpose(size_key: str) -> str:
    """Get the purpose/usage description for each favicon size"""
    purposes = {
        "ico_16": "Traditional favicon (16x16)",
        "ico_32": "Traditional favicon (32x32)", 
        "ico_48": "Traditional favicon (48x48)",
        "png_32": "Standard web favicon",
        "png_64": "High-DPI web favicon",
        "png_128": "Chrome Web Store",
        "png_180": "Apple Touch Icon (iOS)",
        "png_192": "Android Chrome",
        "png_512": "Android Chrome (high-res)",
    }
    return purposes.get(size_key, "Unknown purpose")


def generate_favicon_html():
    """Generate HTML code for favicon integration"""
    html_code = '''<!-- Standard favicon -->
<link rel="icon" type="image/x-icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32x32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16x16.png">

<!-- Apple Touch Icon -->
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">

<!-- Android Chrome -->
<link rel="icon" type="image/png" sizes="192x192" href="/android-chrome-192x192.png">
<link rel="icon" type="image/png" sizes="512x512" href="/android-chrome-512x512.png">

<!-- Web App Manifest (optional) -->
<link rel="manifest" href="/site.webmanifest">'''
    
    return html_code


def generate_favicon_manifest():
    """Generate a web app manifest for PWA support"""
    manifest = '''{
    "name": "Your App Name",
    "short_name": "App",
    "icons": [
        {
            "src": "/android-chrome-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/android-chrome-512x512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ],
    "theme_color": "#ffffff",
    "background_color": "#ffffff",
    "display": "standalone"
}'''
    
    return manifest


def create_multi_ico_favicon(image: Image.Image, out_path: Path, background_color: str = "transparent"):
    """Create a traditional favicon.ico with multiple sizes embedded"""
    sizes = [(16, 16), (32, 32), (48, 48)]
    favicon_images = []
    
    for size in sizes:
        favicon = create_favicon(image, size, background_color)
        # Convert to appropriate mode for ICO
        if favicon.mode == "RGBA":
            # Keep RGBA for transparency
            favicon_images.append(favicon)
        else:
            favicon_images.append(favicon.convert("RGBA"))
    
    # Save as multi-size ICO
    favicon_images[0].save(
        out_path,
        format="ICO",
        sizes=[(img.size[0], img.size[1]) for img in favicon_images],
        append_images=favicon_images[1:],
        optimize=True
    )

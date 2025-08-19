"""
Image Analysis Tools for Web Development
Provides detailed analysis and insights about images to help with optimization decisions
"""
import io
import math
from pathlib import Path
from PIL import Image, ImageStat, ImageOps
from PIL.ExifTags import TAGS
import colorsys
from collections import Counter
from werkzeug.datastructures import FileStorage
from .utils import sanitize_filename

# Constants for magic numbers
SAMPLE_SIZE_LIMIT = 100
EDGE_DETECTION_SAMPLE_SIZE = 200
MONOCHROME_THRESHOLD = 30
HIGH_CONTRAST_THRESHOLD = 200
LOW_COMPLEXITY_THRESHOLD = 1000
MEDIUM_COMPLEXITY_THRESHOLD = 5000
MAX_DOMINANT_COLORS = 3


def analyze_image_comprehensive(file_storage):
    """
    Perform comprehensive analysis of an image file
    Returns detailed metrics and recommendations
    """
    with Image.open(file_storage.stream) as im:
        # Fix rotation according to EXIF
        im = ImageOps.exif_transpose(im)
        
        # Basic image information
        basic_info = _get_basic_info(im)
        
        # Color analysis
        color_analysis = _analyze_colors(im)
        
        # Complexity analysis
        complexity_analysis = _analyze_complexity(im)
        
        # Format recommendations
        format_recommendations = _get_format_recommendations(im, basic_info, color_analysis, complexity_analysis)
        
        # Optimization suggestions
        optimization_suggestions = _get_optimization_suggestions(im, basic_info, color_analysis, complexity_analysis)
        
        # Web performance metrics
        web_metrics = _calculate_web_metrics(im, basic_info)
        
        # EXIF metadata
        metadata = _extract_detailed_metadata(im)
        
        return {
            "basic_info": basic_info,
            "color_analysis": color_analysis,
            "complexity_analysis": complexity_analysis,
            "format_recommendations": format_recommendations,
            "optimization_suggestions": optimization_suggestions,
            "web_metrics": web_metrics,
            "metadata": metadata,
            "filename": sanitize_filename(file_storage.filename)
        }


def _get_basic_info(image: Image.Image) -> dict:
    """Extract basic image information"""
    width, height = image.size
    total_pixels = width * height
    aspect_ratio = width / height
    
    # Determine image category based on dimensions
    if width == height:
        category = "square"
    elif aspect_ratio > 1.5:
        category = "landscape"
    elif aspect_ratio < 0.67:
        category = "portrait"
    else:
        category = "standard"
    
    # Calculate megapixels
    megapixels = total_pixels / 1_000_000
    
    return {
        "dimensions": f"{width}×{height}",
        "width": width,
        "height": height,
        "total_pixels": total_pixels,
        "megapixels": round(megapixels, 2),
        "aspect_ratio": round(aspect_ratio, 2),
        "category": category,
        "mode": image.mode,
        "format": image.format or "Unknown",
        "has_transparency": image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info)
    }


def _analyze_colors(image: Image.Image) -> dict:
    """Analyze color characteristics of the image"""
    # Convert to RGB for analysis
    if image.mode != "RGB":
        if image.mode in ("RGBA", "LA"):
            # Create white background for transparent images
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
        else:
            rgb_image = image.convert("RGB")
    else:
        rgb_image = image
    
    # Get image statistics
    stat = ImageStat.Stat(rgb_image)
    
    # Color range and variation
    r_range = max(stat.extrema[0]) - min(stat.extrema[0])
    g_range = max(stat.extrema[1]) - min(stat.extrema[1])
    b_range = max(stat.extrema[2]) - min(stat.extrema[2])
    avg_range = (r_range + g_range + b_range) / 3
    
    # Brightness analysis
    brightness = sum(stat.mean) / 3
    
    # Sample colors for palette analysis
    sample_size = min(rgb_image.size[0], rgb_image.size[1], SAMPLE_SIZE_LIMIT)
    sample = rgb_image.resize((sample_size, sample_size), Image.Resampling.LANCZOS)
    colors = sample.getdata()
    
    # Count unique colors (simplified)
    color_counts = Counter(colors)
    unique_colors = len(color_counts)
    
    # Dominant colors with RGB and HEX values
    dominant_colors_raw = color_counts.most_common(5)
    dominant_colors_enhanced = []
    
    for color, count in dominant_colors_raw[:MAX_DOMINANT_COLORS]:
        r, g, b = color
        hex_value = f"#{r:02x}{g:02x}{b:02x}"
        dominant_colors_enhanced.append({
            "rgb": {"r": r, "g": g, "b": b},
            "hex": hex_value,
            "color": color,  # Keep for backwards compatibility
            "count": count,
            "percentage": round((count / len(colors)) * 100, 1)
        })
    
    # Color harmony analysis
    harmony_analysis = _analyze_color_harmony(dominant_colors_raw)
    
    return {
        "avg_color_range": round(avg_range, 1),
        "brightness": round(brightness, 1),
        "unique_colors": unique_colors,
        "dominant_colors": dominant_colors_enhanced,
        "color_harmony": harmony_analysis,
        "is_monochrome": avg_range < MONOCHROME_THRESHOLD,
        "is_high_contrast": avg_range > HIGH_CONTRAST_THRESHOLD,
        "color_complexity": "low" if unique_colors < LOW_COMPLEXITY_THRESHOLD else "medium" if unique_colors < MEDIUM_COMPLEXITY_THRESHOLD else "high"
    }


def _analyze_complexity(image: Image.Image) -> dict:
    """Analyze image complexity and detail level"""
    # Convert to grayscale for edge detection
    gray = image.convert("L")
    
    # Sample for performance
    sample_size = min(gray.size[0], gray.size[1], EDGE_DETECTION_SAMPLE_SIZE)
    sample = gray.resize((sample_size, sample_size), Image.Resampling.LANCZOS)
    
    # Simple edge detection using standard deviation
    pixels = list(sample.getdata())
    
    # Calculate local variations
    variations = []
    width = sample.size[0]
    
    for i in range(1, len(pixels) - width - 1):
        if i % width != 0 and (i + 1) % width != 0:  # Not on edges
            # Compare with neighbors
            current = pixels[i]
            neighbors = [
                pixels[i-1], pixels[i+1],           # horizontal
                pixels[i-width], pixels[i+width],   # vertical
                pixels[i-width-1], pixels[i-width+1], # diagonal
                pixels[i+width-1], pixels[i+width+1]
            ]
            variation = sum(abs(current - n) for n in neighbors) / len(neighbors)
            variations.append(variation)
    
    avg_variation = sum(variations) / len(variations) if variations else 0
    
    # Texture analysis
    if avg_variation < 10:
        texture = "smooth"
        detail_level = "low"
    elif avg_variation < 25:
        texture = "moderate"
        detail_level = "medium"
    else:
        texture = "detailed"
        detail_level = "high"
    
    return {
        "edge_density": round(avg_variation, 1),
        "texture": texture,
        "detail_level": detail_level,
        "is_photo_likely": avg_variation > 15 and image.size[0] * image.size[1] > 50000,
        "is_graphic_likely": avg_variation < 20 and len(set(list(image.convert("P").getdata()))) < 256
    }


def _analyze_color_harmony(dominant_colors) -> dict:
    """Analyze color harmony and palette characteristics"""
    if len(dominant_colors) < 2:
        return {"scheme": "monochromatic", "harmony_score": 100}
    
    # Convert RGB to HSV for analysis
    hsv_colors = []
    for (r, g, b), count in dominant_colors[:5]:
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        hsv_colors.append((h * 360, s * 100, v * 100, count))
    
    # Analyze hue relationships
    hues = [h for h, s, v, c in hsv_colors]
    
    # Check for complementary colors (opposite hues)
    complementary = any(abs(h1 - h2) > 150 and abs(h1 - h2) < 210 for h1 in hues for h2 in hues if h1 != h2)
    
    # Check for analogous colors (similar hues)
    analogous = any(abs(h1 - h2) < 30 for h1 in hues for h2 in hues if h1 != h2)
    
    # Determine color scheme
    if len(set(int(h/30) for h in hues)) <= 2:
        scheme = "analogous"
    elif complementary:
        scheme = "complementary"
    elif len(hues) >= 3:
        scheme = "triadic"
    else:
        scheme = "neutral"
    
    # Calculate harmony score
    saturation_variance = max(s for h, s, v, c in hsv_colors) - min(s for h, s, v, c in hsv_colors)
    harmony_score = max(0, 100 - saturation_variance * 2)
    
    return {
        "scheme": scheme,
        "harmony_score": round(harmony_score),
        "is_complementary": complementary,
        "is_analogous": analogous
    }


def _get_format_recommendations(image: Image.Image, basic_info: dict, color_analysis: dict, complexity_analysis: dict) -> dict:
    """Provide format recommendations based on analysis"""
    recommendations = {}
    
    # WebP recommendations
    webp_score = 85  # Base score
    if basic_info["has_transparency"]:
        webp_score += 10
    if complexity_analysis["is_photo_likely"]:
        webp_score += 5
    if basic_info["total_pixels"] > 500000:
        webp_score += 5
    
    recommendations["webp"] = {
        "score": min(100, webp_score),
        "reasons": [
            "Excellent compression ratio",
            "Supports transparency" if basic_info["has_transparency"] else "Good for photos",
            "Wide browser support"
        ]
    }
    
    # JPEG recommendations
    jpeg_score = 70
    if complexity_analysis["is_photo_likely"]:
        jpeg_score += 15
    if not basic_info["has_transparency"]:
        jpeg_score += 10
    if basic_info["total_pixels"] > 1000000:
        jpeg_score += 5
    if color_analysis["color_complexity"] == "high":
        jpeg_score += 5
    
    recommendations["jpeg"] = {
        "score": min(100, jpeg_score),
        "reasons": [
            "Best for photos" if complexity_analysis["is_photo_likely"] else "Good compression",
            "Universal compatibility",
            "Small file sizes for complex images" if color_analysis["color_complexity"] == "high" else "Efficient"
        ]
    }
    
    # PNG recommendations
    png_score = 60
    if basic_info["has_transparency"]:
        png_score += 20
    if complexity_analysis["is_graphic_likely"]:
        png_score += 15
    if color_analysis["color_complexity"] == "low":
        png_score += 10
    if basic_info["total_pixels"] < 100000:
        png_score += 5
    
    recommendations["png"] = {
        "score": min(100, png_score),
        "reasons": [
            "Lossless compression",
            "Perfect for graphics" if complexity_analysis["is_graphic_likely"] else "Supports transparency",
            "Good for simple images" if color_analysis["color_complexity"] == "low" else "Quality preservation"
        ]
    }
    
    # AVIF recommendations
    avif_score = 75
    if basic_info["total_pixels"] > 500000:
        avif_score += 10
    if complexity_analysis["is_photo_likely"]:
        avif_score += 10
    if basic_info["has_transparency"]:
        avif_score += 5
    
    recommendations["avif"] = {
        "score": min(100, avif_score),
        "reasons": [
            "Superior compression",
            "Next-generation format",
            "Best for large images" if basic_info["total_pixels"] > 500000 else "High quality"
        ]
    }
    
    # Sort by score
    sorted_recommendations = dict(sorted(recommendations.items(), key=lambda x: x[1]["score"], reverse=True))
    
    return {
        "recommendations": sorted_recommendations,
        "best_format": list(sorted_recommendations.keys())[0]
    }


def _get_optimization_suggestions(image: Image.Image, basic_info: dict, color_analysis: dict, complexity_analysis: dict) -> dict:
    """Provide optimization suggestions based on analysis"""
    suggestions = []
    
    # Size recommendations
    if basic_info["total_pixels"] > 4000000:  # > 4MP
        suggestions.append({
            "type": "resize",
            "priority": "high",
            "suggestion": "Consider resizing - image is very large for web use",
            "details": f"Current: {basic_info['dimensions']} ({basic_info['megapixels']}MP). Recommend max 2560×1440 for web."
        })
    elif basic_info["total_pixels"] > 2000000:  # > 2MP
        suggestions.append({
            "type": "resize",
            "priority": "medium",
            "suggestion": "Image could be smaller for faster loading",
            "details": f"Current: {basic_info['dimensions']} ({basic_info['megapixels']}MP). Consider 1920×1080 max for most web uses."
        })
    
    # Quality recommendations
    if complexity_analysis["detail_level"] == "low":
        suggestions.append({
            "type": "quality",
            "priority": "medium",
            "suggestion": "Can use lower quality settings",
            "details": "Image has low detail - quality 70-80% should be sufficient"
        })
    elif complexity_analysis["detail_level"] == "high":
        suggestions.append({
            "type": "quality",
            "priority": "low",
            "suggestion": "Use higher quality for best results",
            "details": "Image has high detail - use quality 85-95% to preserve details"
        })
    
    # Color optimization
    if color_analysis["color_complexity"] == "low":
        suggestions.append({
            "type": "format",
            "priority": "medium",
            "suggestion": "PNG may be more efficient",
            "details": "Limited color palette - PNG might compress better than JPEG"
        })
    
    # Transparency optimization
    if basic_info["has_transparency"]:
        suggestions.append({
            "type": "format",
            "priority": "high",
            "suggestion": "Use WebP or PNG for transparency",
            "details": "Image has transparency - avoid JPEG which doesn't support alpha channel"
        })
    
    # Web performance suggestions
    if basic_info["total_pixels"] > 1000000:
        suggestions.append({
            "type": "performance",
            "priority": "high",
            "suggestion": "Generate responsive images",
            "details": "Large image - create multiple sizes for different screen resolutions"
        })
    
    return {
        "suggestions": suggestions,
        "total_suggestions": len(suggestions),
        "high_priority": len([s for s in suggestions if s["priority"] == "high"]),
        "optimization_potential": "high" if len(suggestions) >= 3 else "medium" if len(suggestions) >= 1 else "low"
    }


def _calculate_web_metrics(image: Image.Image, basic_info: dict) -> dict:
    """Calculate web performance related metrics"""
    # Estimate file sizes for different formats and qualities
    estimates = {}
    
    # Base calculations for size estimation
    base_pixels = basic_info["total_pixels"]
    
    # JPEG estimates (approximate)
    estimates["jpeg"] = {
        "quality_95": round(base_pixels * 0.8 / 1024),  # KB
        "quality_85": round(base_pixels * 0.5 / 1024),
        "quality_75": round(base_pixels * 0.3 / 1024),
        "quality_65": round(base_pixels * 0.2 / 1024)
    }
    
    # WebP estimates (typically 25-35% smaller than JPEG)
    estimates["webp"] = {
        "quality_95": round(estimates["jpeg"]["quality_95"] * 0.7),
        "quality_85": round(estimates["jpeg"]["quality_85"] * 0.7),
        "quality_75": round(estimates["jpeg"]["quality_75"] * 0.7),
        "quality_65": round(estimates["jpeg"]["quality_65"] * 0.7)
    }
    
    # PNG estimate (lossless, varies greatly)
    estimates["png"] = round(base_pixels * 1.2 / 1024)
    
    # AVIF estimates (typically 50% smaller than JPEG)
    estimates["avif"] = {
        "quality_95": round(estimates["jpeg"]["quality_95"] * 0.5),
        "quality_85": round(estimates["jpeg"]["quality_85"] * 0.5),
        "quality_75": round(estimates["jpeg"]["quality_75"] * 0.5),
        "quality_65": round(estimates["jpeg"]["quality_65"] * 0.5)
    }
    
    # Loading time estimates (assuming average 3G: 1.6 Mbps = 200 KB/s)
    connection_speeds = {
        "3g": 200,      # KB/s
        "4g": 1500,     # KB/s
        "broadband": 5000  # KB/s
    }
    
    loading_times = {}
    for format_name, format_data in estimates.items():
        if isinstance(format_data, dict):
            # Use quality 85 as baseline
            size_kb = format_data.get("quality_85", 0)
        else:
            size_kb = format_data
        
        loading_times[format_name] = {
            "3g": round(size_kb / connection_speeds["3g"], 1),
            "4g": round(size_kb / connection_speeds["4g"], 1),
            "broadband": round(size_kb / connection_speeds["broadband"], 1)
        }
    
    return {
        "estimated_sizes": estimates,
        "loading_times": loading_times,
        "recommended_max_size": "1920×1080" if base_pixels > 2073600 else "current size is good",
        "performance_score": min(100, max(0, 100 - (base_pixels / 50000)))  # Score decreases with size
    }


def _extract_detailed_metadata(image: Image.Image) -> dict:
    """Extract detailed metadata including EXIF data"""
    metadata = {
        "basic": {
            "format": image.format,
            "mode": image.mode,
            "size": image.size,
            "has_exif": False
        },
        "exif": {},
        "camera_info": {},
        "location": {},
        "technical": {}
    }
    
    # Extract EXIF data if present
    if hasattr(image, '_getexif') and image._getexif():
        exif_dict = image._getexif()
        if exif_dict:
            metadata["basic"]["has_exif"] = True
            
            for tag_id, value in exif_dict.items():
                tag = TAGS.get(tag_id, tag_id)
                
                # Camera information
                if tag in ["Make", "Model", "Software"]:
                    metadata["camera_info"][tag] = str(value)
                
                # Technical details
                elif tag in ["DateTime", "DateTimeOriginal", "ExposureTime", "FNumber", 
                           "ISOSpeedRatings", "FocalLength", "Flash", "WhiteBalance"]:
                    metadata["technical"][tag] = str(value)
                
                # Location data (if present)
                elif tag in ["GPSInfo"]:
                    if value:
                        metadata["location"]["has_gps"] = True
                
                # Other relevant EXIF data
                elif tag in ["ImageWidth", "ImageLength", "BitsPerSample", "Compression",
                           "PhotometricInterpretation", "Orientation", "XResolution", "YResolution"]:
                    metadata["exif"][tag] = str(value)
    
    return metadata


def batch_analyze_images(file_list):
    """
    Analyze multiple images and provide batch insights
    """
    results = []
    errors = []
    
    for file_storage in file_list:
        try:
            file_storage.stream.seek(0)  # Reset stream position
            analysis = analyze_image_comprehensive(file_storage)
            results.append(analysis)
        except Exception as e:
            errors.append({
                "filename": file_storage.filename,
                "error": str(e)
            })
    
    # Generate batch insights
    if results:
        batch_insights = _generate_batch_insights(results)
    else:
        batch_insights = {}
    
    return results, errors, batch_insights


def _generate_batch_insights(analyses: list) -> dict:
    """Generate insights from batch analysis"""
    total_files = len(analyses)
    
    # Aggregate statistics
    total_pixels = sum(a["basic_info"]["total_pixels"] for a in analyses)
    avg_megapixels = sum(a["basic_info"]["megapixels"] for a in analyses) / total_files
    
    # Format distribution
    formats = [a["basic_info"]["format"] for a in analyses]
    format_counts = Counter(formats)
    
    # Complexity distribution
    complexities = [a["complexity_analysis"]["detail_level"] for a in analyses]
    complexity_counts = Counter(complexities)
    
    # Optimization potential
    optimization_scores = [a["optimization_suggestions"]["optimization_potential"] for a in analyses]
    high_potential = sum(1 for score in optimization_scores if score == "high")
    
    # Best format recommendations
    recommended_formats = [a["format_recommendations"]["best_format"] for a in analyses]
    format_recommendations = Counter(recommended_formats)
    
    return {
        "summary": {
            "total_files": total_files,
            "total_megapixels": round(total_pixels / 1_000_000, 1),
            "avg_megapixels": round(avg_megapixels, 1),
            "needs_optimization": high_potential,
            "optimization_percentage": round((high_potential / total_files) * 100, 1)
        },
        "format_distribution": dict(format_counts),
        "complexity_distribution": dict(complexity_counts),
        "recommended_formats": dict(format_recommendations.most_common()),
        "insights": _generate_batch_recommendations(analyses)
    }


def _generate_batch_recommendations(analyses: list) -> list:
    """Generate actionable recommendations for the batch"""
    insights = []
    
    large_images = sum(1 for a in analyses if a["basic_info"]["total_pixels"] > 2000000)
    if large_images > len(analyses) * 0.5:
        insights.append({
            "type": "size",
            "message": f"{large_images} images are larger than recommended for web use",
            "action": "Consider batch resizing to improve loading times"
        })
    
    transparency_images = sum(1 for a in analyses if a["basic_info"]["has_transparency"])
    if transparency_images > 0:
        insights.append({
            "type": "format",
            "message": f"{transparency_images} images have transparency",
            "action": "Use WebP or PNG formats to preserve alpha channels"
        })
    
    photo_images = sum(1 for a in analyses if a["complexity_analysis"]["is_photo_likely"])
    if photo_images > len(analyses) * 0.7:
        insights.append({
            "type": "optimization",
            "message": "Most images appear to be photographs",
            "action": "WebP or JPEG formats with quality 80-85% recommended"
        })
    
    graphic_images = sum(1 for a in analyses if a["complexity_analysis"]["is_graphic_likely"])
    if graphic_images > len(analyses) * 0.5:
        insights.append({
            "type": "optimization",
            "message": "Many images appear to be graphics/logos",
            "action": "PNG or WebP lossless formats recommended for crisp edges"
        })
    
    return insights

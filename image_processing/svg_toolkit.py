"""
SVG Toolkit for Mobile App Development
Comprehensive SVG processing, optimization, and conversion tools
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Union
from PIL import Image, ImageDraw
import io
import base64

# Constants for mobile app development
MOBILE_DENSITIES = {
    "mdpi": 1.0,    # Android baseline (160dpi)
    "hdpi": 1.5,    # Android high (240dpi) 
    "xhdpi": 2.0,   # Android extra high (320dpi), iOS @2x
    "xxhdpi": 3.0,  # Android extra extra high (480dpi), iOS @3x
    "xxxhdpi": 4.0  # Android extra extra extra high (640dpi)
}

IOS_ICON_SIZES = {
    "iphone_settings": 29,
    "iphone_spotlight": 40,
    "iphone_app": 60,
    "ipad_settings": 29,
    "ipad_spotlight": 40,
    "ipad_app": 76,
    "ipad_pro": 83.5,
    "app_store": 1024
}

ANDROID_ICON_SIZES = {
    "mdpi": 48,
    "hdpi": 72,
    "xhdpi": 96,
    "xxhdpi": 144,
    "xxxhdpi": 192,
    "play_store": 512
}

FLUTTER_ICON_SIZES = {
    "android_small": 36,
    "android_medium": 48,
    "android_large": 72,
    "ios_small": 40,
    "ios_medium": 60,
    "ios_large": 76,
    "adaptive": 108
}


def validate_svg(svg_content: str) -> Dict[str, Union[bool, List[str]]]:
    """
    Validate SVG content and check for common issues.
    
    Args:
        svg_content: SVG content as string
        
    Returns:
        dict: Validation results with issues found
    """
    issues = []
    
    try:
        # Parse XML
        root = ET.fromstring(svg_content)
        
        # Check for SVG namespace
        if not root.tag.endswith('svg'):
            issues.append("Root element is not <svg>")
            
        # Check for viewBox
        if 'viewBox' not in root.attrib:
            issues.append("Missing viewBox attribute (recommended for scalability)")
            
        # Check for width/height
        has_width = 'width' in root.attrib
        has_height = 'height' in root.attrib
        if not has_width or not has_height:
            issues.append("Missing width or height attributes")
            
        # Check for accessibility
        title_found = False
        desc_found = False
        for elem in root.iter():
            if elem.tag.endswith('title'):
                title_found = True
            elif elem.tag.endswith('desc'):
                desc_found = True
        if not title_found and not desc_found:
            issues.append("Missing accessibility elements (title or desc)")
            
        # Check for embedded content
        if 'data:' in svg_content:
            issues.append("Contains embedded images (may increase file size)")
            
        # Check for complex gradients/filters
        gradients = []
        filters = []
        for elem in root.iter():
            if elem.tag.endswith('linearGradient') or elem.tag.endswith('radialGradient'):
                gradients.append(elem)
            elif elem.tag.endswith('filter'):
                filters.append(elem)
        if len(gradients) > 5:
            issues.append(f"Many gradients ({len(gradients)}) may impact performance")
        if len(filters) > 0:
            issues.append(f"Contains filters ({len(filters)}) - check mobile compatibility")
            
    except ET.ParseError as e:
        issues.append(f"XML parsing error: {str(e)}")
        return {"valid": False, "issues": issues}
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "elements_count": len(root.findall(".//*")),
        "has_viewbox": 'viewBox' in root.attrib,
        "has_dimensions": has_width and has_height
    }


def optimize_svg(svg_content: str, aggressive: bool = False) -> Dict[str, Union[str, int, float]]:
    """
    Optimize SVG content for mobile apps.
    
    Args:
        svg_content: SVG content as string
        aggressive: Whether to apply aggressive optimizations
        
    Returns:
        dict: Optimized SVG and statistics
    """
    original_size = len(svg_content)
    optimized = svg_content
    
    # Remove comments
    optimized = re.sub(r'<!--.*?-->', '', optimized, flags=re.DOTALL)
    
    # Remove metadata and editor-specific elements
    remove_elements = [
        r'<metadata.*?</metadata>',
        r'<defs>\s*</defs>',
        r'<sodipodi:.*?>',
        r'<inkscape:.*?>',
        r'<cc:.*?>',
        r'<dc:.*?>',
        r'<rdf:.*?</rdf:.*?>'
    ]
    
    for pattern in remove_elements:
        optimized = re.sub(pattern, '', optimized, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove unnecessary attributes
    remove_attrs = [
        r'\s+xmlns:sodipodi="[^"]*"',
        r'\s+xmlns:inkscape="[^"]*"',
        r'\s+xmlns:cc="[^"]*"',
        r'\s+xmlns:dc="[^"]*"',
        r'\s+xmlns:rdf="[^"]*"',
        r'\s+sodipodi:[^=]*="[^"]*"',
        r'\s+inkscape:[^=]*="[^"]*"'
    ]
    
    for pattern in remove_attrs:
        optimized = re.sub(pattern, '', optimized, flags=re.IGNORECASE)
    
    if aggressive:
        # Reduce decimal precision
        def reduce_precision(match):
            number = float(match.group())
            return f"{number:.2f}"
        
        optimized = re.sub(r'\d+\.\d{3,}', reduce_precision, optimized)
        
        # Remove default attributes
        default_attrs = [
            r'\s+fill="none"(?=\s|>)',
            r'\s+stroke="none"(?=\s|>)',
            r'\s+stroke-width="1"(?=\s|>)'
        ]
        
        for pattern in default_attrs:
            optimized = re.sub(pattern, '', optimized)
    
    # Clean up whitespace
    optimized = re.sub(r'\s+', ' ', optimized)
    optimized = re.sub(r'>\s+<', '><', optimized)
    optimized = optimized.strip()
    
    final_size = len(optimized)
    compression_ratio = ((original_size - final_size) / original_size) * 100
    
    return {
        "optimized_svg": optimized,
        "original_size": original_size,
        "optimized_size": final_size,
        "compression_ratio": compression_ratio,
        "size_reduction": original_size - final_size
    }


def svg_to_png_multi_density(svg_content: str, base_size: int, output_dir: Path, 
                            filename_base: str, densities: Dict[str, float] = None) -> List[Dict]:
    """
    Convert SVG to PNG at multiple densities for mobile apps.
    
    Args:
        svg_content: SVG content as string
        base_size: Base size in pixels (mdpi/1x)
        output_dir: Output directory
        filename_base: Base filename without extension
        densities: Density multipliers (defaults to MOBILE_DENSITIES)
        
    Returns:
        list: Generated PNG files with details
    """
    if densities is None:
        densities = MOBILE_DENSITIES
    
    try:
        # Try to use cairosvg for better SVG rendering
        import cairosvg
        
        results = []
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for density_name, multiplier in densities.items():
            size = int(base_size * multiplier)
            filename = f"{filename_base}_{density_name}_{size}px.png"
            output_path = output_dir / filename
            
            # Convert SVG to PNG
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=size,
                output_height=size
            )
            
            # Save PNG file
            with open(output_path, 'wb') as f:
                f.write(png_data)
            
            results.append({
                "filename": filename,
                "density": density_name,
                "size": size,
                "multiplier": multiplier,
                "file_size": len(png_data),
                "path": str(output_path)
            })
            
    except ImportError:
        # Fallback: Use PIL with embedded SVG (limited functionality)
        results = []
        for density_name, multiplier in densities.items():
            size = int(base_size * multiplier)
            filename = f"{filename_base}_{density_name}_{size}px.png"
            
            # Create a simple placeholder (SVG rendering requires additional libraries)
            img = Image.new('RGBA', (size, size), (200, 200, 200, 128))
            draw = ImageDraw.Draw(img)
            draw.text((size//4, size//2), f"SVG\n{size}px", fill=(100, 100, 100, 255))
            
            output_path = output_dir / filename
            img.save(output_path, 'PNG')
            
            results.append({
                "filename": filename,
                "density": density_name,
                "size": size,
                "multiplier": multiplier,
                "file_size": output_path.stat().st_size,
                "path": str(output_path),
                "note": "Placeholder - install cairosvg for actual SVG rendering"
            })
    
    return results


def generate_app_icons(svg_content: str, output_dir: Path, app_name: str) -> Dict[str, List[Dict]]:
    """
    Generate complete app icon sets for iOS, Android, and Flutter.
    
    Args:
        svg_content: SVG content as string
        output_dir: Output directory
        app_name: App name for filenames
        
    Returns:
        dict: Generated icon sets by platform
    """
    results = {
        "ios": [],
        "android": [],
        "flutter": []
    }
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # iOS Icons
    ios_dir = output_dir / "ios"
    ios_dir.mkdir(exist_ok=True)
    
    for icon_type, base_size in IOS_ICON_SIZES.items():
        # Generate @1x, @2x, @3x variants
        for scale in [1, 2, 3]:
            size = int(base_size * scale)
            scale_suffix = f"@{scale}x" if scale > 1 else ""
            filename = f"{app_name}_{icon_type}_{size}px{scale_suffix}.png"
            
            try:
                import cairosvg
                png_data = cairosvg.svg2png(
                    bytestring=svg_content.encode('utf-8'),
                    output_width=size,
                    output_height=size
                )
                
                output_path = ios_dir / filename
                with open(output_path, 'wb') as f:
                    f.write(png_data)
                
                results["ios"].append({
                    "filename": filename,
                    "type": icon_type,
                    "size": size,
                    "scale": scale,
                    "file_size": len(png_data)
                })
                
            except ImportError:
                # Placeholder
                img = Image.new('RGBA', (size, size), (70, 130, 180, 255))
                output_path = ios_dir / filename
                img.save(output_path, 'PNG')
                
                results["ios"].append({
                    "filename": filename,
                    "type": icon_type,
                    "size": size,
                    "scale": scale,
                    "file_size": output_path.stat().st_size,
                    "note": "Placeholder - install cairosvg for actual SVG rendering"
                })
    
    # Android Icons  
    android_dir = output_dir / "android"
    android_dir.mkdir(exist_ok=True)
    
    for density, size in ANDROID_ICON_SIZES.items():
        filename = f"{app_name}_android_{density}_{size}px.png"
        
        try:
            import cairosvg
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=size,
                output_height=size
            )
            
            output_path = android_dir / filename
            with open(output_path, 'wb') as f:
                f.write(png_data)
            
            results["android"].append({
                "filename": filename,
                "density": density,
                "size": size,
                "file_size": len(png_data)
            })
            
        except ImportError:
            # Placeholder
            img = Image.new('RGBA', (size, size), (60, 179, 113, 255))
            output_path = android_dir / filename
            img.save(output_path, 'PNG')
            
            results["android"].append({
                "filename": filename,
                "density": density,
                "size": size,
                "file_size": output_path.stat().st_size,
                "note": "Placeholder - install cairosvg for actual SVG rendering"
            })
    
    # Flutter Icons
    flutter_dir = output_dir / "flutter"
    flutter_dir.mkdir(exist_ok=True)
    
    for icon_type, size in FLUTTER_ICON_SIZES.items():
        filename = f"{app_name}_flutter_{icon_type}_{size}px.png"
        
        try:
            import cairosvg
            png_data = cairosvg.svg2png(
                bytestring=svg_content.encode('utf-8'),
                output_width=size,
                output_height=size
            )
            
            output_path = flutter_dir / filename
            with open(output_path, 'wb') as f:
                f.write(png_data)
            
            results["flutter"].append({
                "filename": filename,
                "type": icon_type,
                "size": size,
                "file_size": len(png_data)
            })
            
        except ImportError:
            # Placeholder
            img = Image.new('RGBA', (size, size), (138, 43, 226, 255))
            output_path = flutter_dir / filename
            img.save(output_path, 'PNG')
            
            results["flutter"].append({
                "filename": filename,
                "type": icon_type,
                "size": size,
                "file_size": output_path.stat().st_size,
                "note": "Placeholder - install cairosvg for actual SVG rendering"
            })
    
    return results


def generate_color_variants(svg_content: str, color_schemes: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    """
    Generate color variants of SVG for theming.
    
    Args:
        svg_content: Original SVG content
        color_schemes: Dict of scheme_name -> {old_color: new_color}
        
    Returns:
        dict: Color variant SVGs
    """
    variants = {}
    
    for scheme_name, color_map in color_schemes.items():
        variant_svg = svg_content
        
        for old_color, new_color in color_map.items():
            # Replace color values (supports hex, rgb, named colors)
            patterns = [
                f'fill="{old_color}"',
                f'stroke="{old_color}"',
                f'stop-color="{old_color}"',
                f'fill:{old_color}',
                f'stroke:{old_color}'
            ]
            
            for pattern in patterns:
                replacement = pattern.replace(old_color, new_color)
                variant_svg = variant_svg.replace(pattern, replacement)
        
        variants[scheme_name] = variant_svg
    
    return variants


def analyze_svg_complexity(svg_content: str) -> Dict[str, Union[int, float, List[str]]]:
    """
    Analyze SVG complexity and performance characteristics.
    
    Args:
        svg_content: SVG content as string
        
    Returns:
        dict: Complexity analysis results
    """
    try:
        root = ET.fromstring(svg_content)
        
        # Count elements
        all_elements = root.findall(".//*")
        element_counts = {}
        
        for elem in all_elements:
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            element_counts[tag] = element_counts.get(tag, 0) + 1
        
        # Analyze paths
        paths = []
        for elem in root.iter():
            if elem.tag.endswith('path'):
                paths.append(elem)
        total_path_commands = 0
        complex_paths = 0
        
        for path in paths:
            d_attr = path.get('d', '')
            commands = len(re.findall(r'[MmLlHhVvCcSsQqTtAaZz]', d_attr))
            total_path_commands += commands
            if commands > 20:
                complex_paths += 1
        
        # Performance indicators
        performance_issues = []
        
        if len(all_elements) > 100:
            performance_issues.append(f"Many elements ({len(all_elements)}) - consider simplification")
        
        if complex_paths > 0:
            performance_issues.append(f"{complex_paths} complex paths detected")
        
        if element_counts.get('gradient', 0) + element_counts.get('linearGradient', 0) + element_counts.get('radialGradient', 0) > 5:
            performance_issues.append("Many gradients - may impact rendering performance")
        
        if 'filter' in element_counts:
            performance_issues.append("Contains filters - check mobile compatibility")
        
        # Complexity score (0-100, lower is simpler)
        complexity_score = min(100, (
            len(all_elements) * 0.5 +
            total_path_commands * 0.1 +
            element_counts.get('gradient', 0) * 2 +
            element_counts.get('filter', 0) * 5
        ))
        
        return {
            "total_elements": len(all_elements),
            "element_counts": element_counts,
            "path_count": len(paths),
            "total_path_commands": total_path_commands,
            "complex_paths": complex_paths,
            "complexity_score": complexity_score,
            "performance_issues": performance_issues,
            "file_size": len(svg_content)
        }
        
    except ET.ParseError:
        return {
            "error": "Invalid SVG format",
            "complexity_score": 100,
            "performance_issues": ["Cannot parse SVG"]
        }


def generate_svg_report(svg_content: str, filename: str) -> Dict:
    """
    Generate comprehensive SVG analysis report.
    
    Args:
        svg_content: SVG content as string
        filename: Original filename
        
    Returns:
        dict: Complete analysis report
    """
    validation = validate_svg(svg_content)
    optimization = optimize_svg(svg_content, aggressive=False)
    complexity = analyze_svg_complexity(svg_content)
    
    # Mobile compatibility assessment
    mobile_compatible = True
    mobile_issues = []
    
    if complexity["complexity_score"] > 70:
        mobile_compatible = False
        mobile_issues.append("High complexity may cause performance issues on mobile")
    
    if "filter" in complexity.get("element_counts", {}):
        mobile_compatible = False
        mobile_issues.append("SVG filters may not render consistently on all mobile browsers")
    
    if len(svg_content) > 50000:  # 50KB
        mobile_issues.append("Large file size - consider optimization")
    
    return {
        "filename": filename,
        "file_size": len(svg_content),
        "validation": validation,
        "optimization": optimization,
        "complexity": complexity,
        "mobile_compatibility": {
            "compatible": mobile_compatible,
            "issues": mobile_issues
        },
        "recommendations": _generate_recommendations(validation, complexity, len(svg_content))
    }


def _generate_recommendations(validation: Dict, complexity: Dict, file_size: int) -> List[str]:
    """Generate optimization recommendations based on analysis."""
    recommendations = []
    
    if not validation["valid"]:
        recommendations.append("Fix validation errors before using in production")
    
    if not validation.get("has_viewbox", False):
        recommendations.append("Add viewBox attribute for better scalability")
    
    if complexity["complexity_score"] > 50:
        recommendations.append("Consider simplifying paths and reducing elements")
    
    if file_size > 20000:  # 20KB
        recommendations.append("Optimize SVG to reduce file size")
    
    if complexity.get("complex_paths", 0) > 0:
        recommendations.append("Simplify complex paths for better mobile performance")
    
    if len(complexity.get("performance_issues", [])) > 0:
        recommendations.append("Address performance issues for mobile compatibility")
    
    if not recommendations:
        recommendations.append("SVG is well-optimized for mobile use")
    
    return recommendations

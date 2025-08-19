"""
Utility functions for Flask routes to follow DRY principles
"""
import io
import os
import zipfile
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Union
from flask import request, flash, redirect, url_for, Response, send_file
import io
import zipfile
from flask import send_file, url_for

# Constants
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
ALLOWED_SVG_EXT = {".svg"}
DEFAULT_WEBP_QUALITY = 85
DEFAULT_THUMBNAIL_QUALITY = 82
DEFAULT_IMAGE_NAME = "image"
DEFAULT_UNKNOWN_NAME = "unknown"


def validate_and_get_files(redirect_tab: Optional[str] = None) -> Tuple[Optional[List], Optional[Response]]:
    """
    Validate uploaded files and return valid ones.
    
    Args:
        redirect_tab: Tab to redirect to if validation fails
        
    Returns:
        tuple: (valid_files, redirect_response_or_None)
    """
    files = request.files.getlist("images")
    
    # Check if files exist
    if not files or files[0].filename == "":
        flash("Please choose at least one image.")
        if redirect_tab:
            return None, redirect(url_for("index", tab=redirect_tab))
        return None, redirect(url_for("index"))
    
    # Filter valid files
    valid_files = []
    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext in ALLOWED_EXT:
            valid_files.append(f)
    
    if not valid_files:
        flash("No valid images were uploaded.")
        if redirect_tab:
            return None, redirect(url_for("index", tab=redirect_tab))
        return None, redirect(url_for("index"))
    
    return valid_files, None


def validate_and_get_svg_files(redirect_tab: str = "svg") -> Tuple[Optional[List], Optional[Response]]:
    """
    Validate uploaded SVG files and return valid ones.
    
    Args:
        redirect_tab: Tab to redirect to if validation fails
        
    Returns:
        tuple: (valid_svg_files, redirect_response_or_None)
    """
    files = request.files.getlist("svgs")
    
    # Check if files exist
    if not files or files[0].filename == "":
        flash("Please choose at least one SVG file.")
        return None, redirect(url_for("index", tab=redirect_tab))
    
    # Filter valid SVG files
    svg_files = []
    for f in files:
        if f.filename.lower().endswith('.svg'):
            svg_files.append(f)
    
    if not svg_files:
        flash("No valid SVG files were uploaded.")
        return None, redirect(url_for("index", tab=redirect_tab))
    
    return svg_files, None


def get_output_directory(base_dir: Path, default_output: Path) -> Path:
    """
    Get and validate output directory from form data.
    
    Args:
        base_dir: Base directory path
        default_output: Default output directory
        
    Returns:
        Path: Resolved output directory path
    """
    out_dir_text = request.form.get("output_dir", "").strip()
    out_dir = Path(out_dir_text) if out_dir_text else default_output
    
    if not out_dir.is_absolute():
        out_dir = (base_dir / out_dir).resolve()
    
    return out_dir


def get_quality_settings() -> Dict[str, Union[int, bool]]:
    """
    Extract quality settings from form data.
    
    Returns:
        dict: Quality settings (quality, lossless)
    """
    return {
        "quality": int(request.form.get("quality", str(DEFAULT_WEBP_QUALITY))),
        "lossless": request.form.get("lossless") == "on"
    }


def validate_selections(field_name: str, redirect_tab: str, error_message: str) -> Tuple[Optional[List[str]], Optional[Response]]:
    """
    Validate that selections were made in form.
    
    Args:
        field_name: Form field name to check
        redirect_tab: Tab to redirect to if validation fails
        error_message: Error message to flash
        
    Returns:
        tuple: (selections, redirect_response_or_None)
    """
    selections = request.form.getlist(field_name)
    
    if not selections:
        flash(error_message)
        return None, redirect(url_for("index", tab=redirect_tab))
    
    return selections, None


def create_zip_response(results: List[Dict], output_dir: Path, zip_filename: str) -> Response:
    """
    Create a ZIP file response from processing results.
    
    Args:
        results: List of result dictionaries with 'name' keys
        output_dir: Directory containing the result files
        zip_filename: Name for the ZIP file download
        
    Returns:
        Flask Response: ZIP file download response
    """
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        for item in results:
            file_path = output_dir / item["name"]
            if file_path.exists():
                z.write(file_path, arcname=item["name"])
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=zip_filename, mimetype="application/zip")


def create_svg_zip_response(svg_output_dir: Path, zip_filename: str) -> Response:
    """
    Create a ZIP file response from SVG processing directory.
    
    Args:
        svg_output_dir: Directory containing SVG processing results
        zip_filename: Name for the ZIP file download
        
    Returns:
        Flask Response: ZIP file download response
    """
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as z:
        # Add all generated files to ZIP
        for root, dirs, files in os.walk(svg_output_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(svg_output_dir)
                z.write(file_path, arcname=str(arcname))
    
    mem.seek(0)
    return send_file(mem, as_attachment=True, download_name=zip_filename, mimetype="application/zip")


def handle_processing_results(results: List[Dict], redirect_tab: str, no_results_message: str) -> Tuple[Optional[List], Optional[Response]]:
    """
    Handle processing results with error checking.
    
    Args:
        results: List of processing results
        redirect_tab: Tab to redirect to if no results
        no_results_message: Error message for no results
        
    Returns:
        tuple: (results, redirect_response_or_None)
    """
    if not results:
        flash(no_results_message)
        return None, redirect(url_for("index", tab=redirect_tab))
    
    return results, None


def get_format_settings() -> Dict[str, Union[str, int, bool]]:
    """
    Extract format-specific settings from form data.
    
    Returns:
        dict: Format settings (format_type, quality, lossless, etc.)
    """
    format_type = request.form.get("format_type", "webp")
    quality = int(request.form.get("quality", str(DEFAULT_WEBP_QUALITY)))
    lossless = request.form.get("lossless") == "on" if format_type == "webp" else False
    
    return {
        "format_type": format_type,
        "quality": quality,
        "lossless": lossless
    }


def prepare_template_data(results: List[Dict], additional_data: Optional[Dict] = None) -> Dict:
    """
    Prepare standard template data from processing results.
    
    Args:
        results: List of processing results
        additional_data: Optional additional template data
        
    Returns:
        dict: Template data ready for rendering
    """
    file_links = [url_for("serve_output", filename=item["name"]) for item in results]
    items = list(zip(results, file_links))
    
    template_data = {
        "items": items,
        "results": results
    }
    
    if additional_data:
        template_data.update(additional_data)
    
    return template_data


# Import shared utilities to avoid duplication  
from image_processing.utils import sanitize_filename

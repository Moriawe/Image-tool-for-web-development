"""
Utility functions for Flask routes to follow DRY principles
"""
from pathlib import Path
from typing import Tuple, Optional, Dict, List, Union
from flask import request, flash, redirect, url_for, Response

# Constants
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}
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


# Import shared utilities to avoid duplication  
from image_processing.utils import sanitize_filename

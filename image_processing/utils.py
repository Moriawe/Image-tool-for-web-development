"""
Shared utilities for image processing modules
"""
import re
from pathlib import Path

# Constants
MAX_FILENAME_LENGTH = 100
BYTES_PER_KB = 1024
BYTES_PER_MB = 1024 * 1024
BYTES_PER_GB = 1024 * 1024 * 1024
WHITE_RGB = (255, 255, 255)
DEFAULT_IMAGE_NAME = "image"


def sanitize_filename(name: str) -> str:
    """
    Clean filename by removing special characters and ensuring safe naming.
    
    Args:
        name: Original filename or path
        
    Returns:
        str: Sanitized filename without extension
    """
    if not name:
        return "image"
    
    # Extract stem (filename without extension)
    name = Path(name).stem
    
    # Replace problematic characters with underscores
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._-")
    
    # Ensure we have a valid name
    if not name:
        return DEFAULT_IMAGE_NAME
        
    # Limit length to avoid filesystem issues
    return name[:MAX_FILENAME_LENGTH]


def get_file_extension(format_name: str) -> str:
    """
    Get file extension for a given format.
    
    Args:
        format_name: Format name (webp, jpeg, png, avif)
        
    Returns:
        str: File extension with dot
    """
    extensions = {
        "webp": ".webp",
        "jpeg": ".jpg",
        "jpg": ".jpg", 
        "png": ".png",
        "avif": ".avif",
        "ico": ".ico"
    }
    
    return extensions.get(format_name.lower(), ".jpg")


def bytes_to_human_readable(size_bytes: int) -> str:
    """
    Convert bytes to human readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        str: Human readable size (e.g., "1.2 MB")
    """
    if size_bytes < BYTES_PER_KB:
        return f"{size_bytes} B"
    elif size_bytes < BYTES_PER_MB:
        return f"{size_bytes / BYTES_PER_KB:.1f} KB"
    elif size_bytes < BYTES_PER_GB:
        return f"{size_bytes / BYTES_PER_MB:.1f} MB"
    else:
        return f"{size_bytes / BYTES_PER_GB:.1f} GB"


def calculate_compression_ratio(original_size: int, compressed_size: int) -> float:
    """
    Calculate compression ratio as percentage.
    
    Args:
        original_size: Original file size in bytes
        compressed_size: Compressed file size in bytes
        
    Returns:
        float: Compression ratio as percentage (e.g., 75.5 for 75.5% compression)
    """
    if original_size == 0:
        return 0.0
        
    return ((original_size - compressed_size) / original_size) * 100

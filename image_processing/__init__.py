"""
Image processing utilities for web development
"""

from .webp_converter import (
    save_as_webp, 
    sanitize_filename, 
    convert_image_format,
    batch_convert_images,
    get_format_comparison,
    WEB_FORMATS
)
from .responsive_images import generate_responsive_images, generate_srcset_html, RESPONSIVE_SIZES
from .thumbnail_generator import (
    generate_thumbnails, 
    generate_thumbnail_css, 
    generate_thumbnail_html,
    THUMBNAIL_SIZES,
    CROP_METHODS
)
from .favicon_generator import (
    generate_favicons,
    generate_favicon_html,
    generate_favicon_manifest,
    create_multi_ico_favicon,
    FAVICON_SIZES,
    FAVICON_SPECS
)
from .image_analysis import (
    analyze_image_comprehensive,
    batch_analyze_images
)

__all__ = [
    'save_as_webp',
    'sanitize_filename', 
    'convert_image_format',
    'batch_convert_images',
    'get_format_comparison',
    'generate_responsive_images',
    'generate_srcset_html',
    'generate_thumbnails',
    'generate_thumbnail_css',
    'generate_thumbnail_html',
    'generate_favicons',
    'generate_favicon_html',
    'generate_favicon_manifest',
    'create_multi_ico_favicon',
    'analyze_image_comprehensive',
    'batch_analyze_images',
    'WEB_FORMATS',
    'RESPONSIVE_SIZES',
    'THUMBNAIL_SIZES', 
    'CROP_METHODS',
    'FAVICON_SIZES',
    'FAVICON_SPECS'
]

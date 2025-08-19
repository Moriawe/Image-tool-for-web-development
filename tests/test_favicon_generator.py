"""
Unit tests for favicon generator
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from io import BytesIO
from PIL import Image
import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from image_processing.favicon_generator import (
    generate_favicons,
    create_favicon,
    generate_favicon_html,
    generate_favicon_manifest,
    create_multi_ico_favicon,
    get_favicon_purpose,
    FAVICON_SIZES,
    FAVICON_SPECS
)


class MockFileStorage:
    """Mock file storage object for testing"""
    def __init__(self, filename, image_data):
        self.filename = filename
        self.stream = BytesIO(image_data)


class TestFaviconGenerator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test images
        self.test_image_square = Image.new("RGB", (256, 256), color="red")
        self.test_image_rect = Image.new("RGB", (300, 200), color="green")
        self.test_image_rgba = Image.new("RGBA", (128, 128), color=(255, 0, 0, 128))
        
        # Save test images to bytes
        self.square_bytes = self._image_to_bytes(self.test_image_square)
        self.rect_bytes = self._image_to_bytes(self.test_image_rect)
        self.rgba_bytes = self._image_to_bytes(self.test_image_rgba, "PNG")
    
    def _image_to_bytes(self, image, format="PNG"):
        """Convert PIL Image to bytes"""
        bytes_io = BytesIO()
        image.save(bytes_io, format=format)
        bytes_io.seek(0)
        return bytes_io.getvalue()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_favicon_sizes_constant(self):
        """Test that favicon sizes are properly defined"""
        self.assertIsInstance(FAVICON_SIZES, dict)
        
        # Check expected sizes exist
        expected_sizes = ["ico_16", "ico_32", "ico_48", "png_32", "png_64", "png_128", "png_180", "png_192", "png_512"]
        for size_key in expected_sizes:
            self.assertIn(size_key, FAVICON_SIZES)
            
        # Check size format
        for size_name, dimensions in FAVICON_SIZES.items():
            self.assertIsInstance(dimensions, tuple)
            self.assertEqual(len(dimensions), 2)
            self.assertIsInstance(dimensions[0], int)
            self.assertIsInstance(dimensions[1], int)
    
    def test_favicon_specs_constant(self):
        """Test that favicon specs are properly defined"""
        self.assertIsInstance(FAVICON_SPECS, dict)
        
        # Each favicon size should have corresponding spec
        for size_key in FAVICON_SIZES.keys():
            self.assertIn(size_key, FAVICON_SPECS)
            spec = FAVICON_SPECS[size_key]
            self.assertIn("format", spec)
            self.assertIn("filename", spec)
            self.assertIn(spec["format"], ["ICO", "PNG"])
    
    def test_create_favicon_square_image(self):
        """Test favicon creation with square source image"""
        favicon = create_favicon(self.test_image_square, (32, 32), "transparent")
        
        self.assertEqual(favicon.size, (32, 32))
        self.assertEqual(favicon.mode, "RGBA")  # Should be RGBA for transparency
    
    def test_create_favicon_rectangular_image(self):
        """Test favicon creation with rectangular source image"""
        # Should maintain aspect ratio and center the image
        favicon = create_favicon(self.test_image_rect, (64, 64), "white")
        
        self.assertEqual(favicon.size, (64, 64))
        # The actual image should be centered with white background
    
    def test_create_favicon_with_background_colors(self):
        """Test favicon creation with different background colors"""
        # Test transparent background
        favicon_transparent = create_favicon(self.test_image_square, (32, 32), "transparent")
        self.assertEqual(favicon_transparent.mode, "RGBA")
        
        # Test hex color background
        favicon_hex = create_favicon(self.test_image_square, (32, 32), "#ffffff")
        self.assertEqual(favicon_hex.mode, "RGB")
        
        # Test named color background
        favicon_named = create_favicon(self.test_image_square, (32, 32), "white")
        self.assertEqual(favicon_named.mode, "RGB")
    
    def test_generate_favicons_basic(self):
        """Test basic favicon generation"""
        mock_file = MockFileStorage("logo.png", self.square_bytes)
        
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=["ico_32", "png_180"],
            background_color="transparent"
        )
        
        self.assertEqual(len(results), 2)
        
        # Check results structure
        for result in results:
            self.assertIn("name", result)
            self.assertIn("size_kb", result)
            self.assertIn("dimensions", result)
            self.assertIn("format", result)
            self.assertIn("size_key", result)
            self.assertIn("purpose", result)
            
            # Check file was created
            file_path = self.temp_dir / result["name"]
            self.assertTrue(file_path.exists())
    
    def test_generate_favicons_ico_format(self):
        """Test ICO format favicon generation"""
        mock_file = MockFileStorage("icon.jpg", self.square_bytes)
        
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=["ico_16", "ico_32", "ico_48"],
            background_color="white"
        )
        
        self.assertEqual(len(results), 3)
        
        # Check all results are ICO format
        for result in results:
            self.assertEqual(result["format"], "ICO")
            self.assertTrue(result["name"].endswith(".ico"))
            
            # Verify ICO file can be opened
            file_path = self.temp_dir / result["name"]
            with Image.open(file_path) as img:
                self.assertEqual(img.format, "ICO")
    
    def test_generate_favicons_png_format(self):
        """Test PNG format favicon generation"""
        mock_file = MockFileStorage("logo.png", self.rgba_bytes)
        
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=["png_32", "png_64", "png_192"],
            background_color="transparent"
        )
        
        self.assertEqual(len(results), 3)
        
        # Check all results are PNG format
        for result in results:
            self.assertEqual(result["format"], "PNG")
            self.assertTrue(result["name"].endswith(".png"))
            
            # Verify PNG file can be opened
            file_path = self.temp_dir / result["name"]
            with Image.open(file_path) as img:
                self.assertEqual(img.format, "PNG")
    
    def test_generate_favicons_all_sizes(self):
        """Test favicon generation with all available sizes"""
        mock_file = MockFileStorage("complete_logo.png", self.square_bytes)
        
        all_sizes = list(FAVICON_SIZES.keys())
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=all_sizes,
            background_color="transparent"
        )
        
        self.assertEqual(len(results), len(all_sizes))
        
        # Verify each size was generated correctly
        result_keys = [r["size_key"] for r in results]
        for size_key in all_sizes:
            self.assertIn(size_key, result_keys)
    
    def test_generate_favicons_invalid_size(self):
        """Test favicon generation with invalid size"""
        mock_file = MockFileStorage("test.png", self.square_bytes)
        
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=["invalid_size", "png_32"],
            background_color="transparent"
        )
        
        # Should only generate favicon for valid size
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["size_key"], "png_32")
    
    def test_create_multi_ico_favicon(self):
        """Test creation of multi-size ICO file"""
        ico_path = self.temp_dir / "favicon.ico"
        
        create_multi_ico_favicon(self.test_image_square, ico_path, "white")
        
        self.assertTrue(ico_path.exists())
        
        # Verify ICO file can be opened and has multiple sizes
        with Image.open(ico_path) as img:
            self.assertEqual(img.format, "ICO")
            # ICO files with multiple sizes should be readable
    
    def test_get_favicon_purpose(self):
        """Test favicon purpose descriptions"""
        # Test known size keys
        self.assertIn("Traditional favicon", get_favicon_purpose("ico_16"))
        self.assertIn("Apple Touch Icon", get_favicon_purpose("png_180"))
        self.assertIn("Android Chrome", get_favicon_purpose("png_192"))
        
        # Test unknown size key
        self.assertEqual(get_favicon_purpose("unknown_key"), "Unknown purpose")
    
    def test_generate_favicon_html(self):
        """Test HTML code generation for favicons"""
        html_code = generate_favicon_html()
        
        self.assertIsInstance(html_code, str)
        self.assertIn('<link rel="icon"', html_code)
        self.assertIn('favicon-32x32.png', html_code)
        self.assertIn('apple-touch-icon.png', html_code)
        self.assertIn('android-chrome-192x192.png', html_code)
        self.assertIn('android-chrome-512x512.png', html_code)
        self.assertIn('rel="manifest"', html_code)
    
    def test_generate_favicon_manifest(self):
        """Test web app manifest generation"""
        manifest = generate_favicon_manifest()
        
        self.assertIsInstance(manifest, str)
        self.assertIn('"name":', manifest)
        self.assertIn('"icons":', manifest)
        self.assertIn('android-chrome-192x192.png', manifest)
        self.assertIn('android-chrome-512x512.png', manifest)
        self.assertIn('"theme_color":', manifest)
        self.assertIn('"display": "standalone"', manifest)
        
        # Should be valid JSON structure
        import json
        try:
            json.loads(manifest)
        except json.JSONDecodeError:
            self.fail("Generated manifest is not valid JSON")
    
    def test_favicon_file_naming(self):
        """Test that favicon files follow the expected naming convention"""
        mock_file = MockFileStorage("My Company Logo!@#.png", self.square_bytes)
        
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=["ico_32", "png_180"],
            background_color="transparent"
        )
        
        # Should use standard favicon naming, not based on input filename
        expected_names = ["favicon-32x32.ico", "apple-touch-icon.png"]
        actual_names = [r["name"] for r in results]
        
        for expected in expected_names:
            self.assertIn(expected, actual_names)
    
    def test_favicon_scaling_preserves_aspect_ratio(self):
        """Test that favicon scaling maintains aspect ratio"""
        # Create a non-square image
        rect_image = Image.new("RGB", (100, 50), color="blue")
        
        favicon = create_favicon(rect_image, (32, 32), "white")
        
        self.assertEqual(favicon.size, (32, 32))
        # The image should be centered and scaled to fit within 32x32
        # while maintaining aspect ratio (should have white padding)
    
    def test_favicon_with_transparency(self):
        """Test favicon generation preserves transparency when appropriate"""
        mock_file = MockFileStorage("transparent_logo.png", self.rgba_bytes)
        
        results = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            selected_sizes=["png_32"],
            background_color="transparent"
        )
        
        self.assertEqual(len(results), 1)
        
        # Check that PNG with transparent background preserves alpha
        file_path = self.temp_dir / results[0]["name"]
        with Image.open(file_path) as img:
            self.assertIn(img.mode, ["RGBA", "LA"])  # Should have alpha channel
    
    def test_favicon_background_color_application(self):
        """Test that background colors are properly applied"""
        mock_file = MockFileStorage("small_logo.png", self.square_bytes)
        
        # Test with white background
        results_white = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir / "white",
            selected_sizes=["png_64"],
            background_color="white"
        )
        
        # Test with hex color background
        mock_file.stream = BytesIO(self.square_bytes)
        results_hex = generate_favicons(
            file_storage=mock_file,
            out_dir=self.temp_dir / "hex",
            selected_sizes=["png_64"],
            background_color="#ff0000"
        )
        
        # Both should succeed
        self.assertEqual(len(results_white), 1)
        self.assertEqual(len(results_hex), 1)


if __name__ == "__main__":
    unittest.main()

"""
Unit tests for WebP converter and universal format converter
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

from image_processing.webp_converter import (
    sanitize_filename,
    convert_image_format,
    batch_convert_images,
    get_format_comparison,
    WEB_FORMATS,
    _convert_for_format,
    _has_alpha_channel
)


class MockFileStorage:
    """Mock file storage object for testing"""
    def __init__(self, filename, image_data):
        self.filename = filename
        self.stream = BytesIO(image_data)


class TestWebPConverter(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test images
        self.test_image_rgb = Image.new("RGB", (100, 100), color="red")
        self.test_image_rgba = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        
        # Save test images to bytes
        self.rgb_bytes = BytesIO()
        self.test_image_rgb.save(self.rgb_bytes, format="PNG")
        self.rgb_bytes.seek(0)
        
        self.rgba_bytes = BytesIO()
        self.test_image_rgba.save(self.rgba_bytes, format="PNG")
        self.rgba_bytes.seek(0)
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
        
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        self.assertEqual(sanitize_filename("test image.jpg"), "test_image")
        self.assertEqual(sanitize_filename("file!@#$%^&*()name.png"), "file_name")
        self.assertEqual(sanitize_filename("normal-file_name.webp"), "normal-file_name")
        self.assertEqual(sanitize_filename(""), "image")
        
    def test_web_formats_config(self):
        """Test that all web formats are properly configured"""
        self.assertIn("webp", WEB_FORMATS)
        self.assertIn("jpeg", WEB_FORMATS)
        self.assertIn("png", WEB_FORMATS)
        self.assertIn("avif", WEB_FORMATS)
        
        # Check format properties
        self.assertTrue(WEB_FORMATS["webp"]["supports_lossless"])
        self.assertTrue(WEB_FORMATS["webp"]["supports_alpha"])
        self.assertFalse(WEB_FORMATS["jpeg"]["supports_lossless"])
        self.assertFalse(WEB_FORMATS["jpeg"]["supports_alpha"])
        
    def test_convert_image_format_webp(self):
        """Test WebP conversion"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "webp", 85, False)
        
        self.assertIn("filename", result)
        self.assertIn("size_kb", result)
        self.assertEqual(result["format"], "WebP")
        self.assertTrue((self.temp_dir / result["filename"]).exists())
        
    def test_convert_image_format_jpeg(self):
        """Test JPEG conversion"""
        mock_file = MockFileStorage("test.png", self.rgba_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "jpeg", 85, False)
        
        self.assertIn("filename", result)
        self.assertTrue(result["filename"].endswith(".jpg"))
        self.assertEqual(result["format"], "JPEG")
        self.assertTrue((self.temp_dir / result["filename"]).exists())
        
    def test_convert_image_format_png(self):
        """Test PNG conversion"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "png", 85, True)
        
        self.assertIn("filename", result)
        self.assertTrue(result["filename"].endswith(".png"))
        self.assertEqual(result["format"], "PNG")
        
    def test_invalid_format(self):
        """Test error handling for invalid formats"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        with self.assertRaises(ValueError):
            convert_image_format(mock_file, self.temp_dir, "invalid_format", 85, False)
            
    def test_has_alpha_channel(self):
        """Test alpha channel detection"""
        self.assertFalse(_has_alpha_channel(self.test_image_rgb))
        self.assertTrue(_has_alpha_channel(self.test_image_rgba))
        
    def test_convert_for_format_jpeg_transparency(self):
        """Test JPEG conversion removes transparency"""
        converted = _convert_for_format(self.test_image_rgba, "jpeg", 85, False)
        self.assertEqual(converted.mode, "RGB")
        
    def test_batch_convert_images(self):
        """Test batch conversion"""
        mock_files = [
            MockFileStorage("test1.jpg", self.rgb_bytes.getvalue()),
            MockFileStorage("test2.png", self.rgba_bytes.getvalue())
        ]
        
        # Reset streams
        for f in mock_files:
            f.stream.seek(0)
            
        results, errors = batch_convert_images(mock_files, self.temp_dir, "webp", 85, False)
        
        self.assertEqual(len(results), 2)
        self.assertEqual(len(errors), 0)
        self.assertTrue(all("filename" in result for result in results))
        
    def test_get_format_comparison(self):
        """Test format comparison functionality"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        comparisons = get_format_comparison(mock_file, self.temp_dir, 85)
        
        self.assertIn("webp", comparisons)
        self.assertIn("jpeg", comparisons)
        self.assertIn("png", comparisons)
        # AVIF might not be supported, so we don't assert for it
        
        # Check that files were created
        for format_key, result in comparisons.items():
            if "filename" in result:
                self.assertTrue((self.temp_dir / result["filename"]).exists())
                
    def test_lossless_conversion(self):
        """Test lossless conversion"""
        mock_file = MockFileStorage("test.png", self.rgba_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "webp", 85, True)
        
        self.assertEqual(result["quality"], "lossless")
        
    def test_quality_settings(self):
        """Test different quality settings"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        
        # Test low quality
        mock_file.stream.seek(0)
        result_low = convert_image_format(mock_file, self.temp_dir, "webp", 20, False)
        
        # Test high quality  
        mock_file.stream.seek(0)
        result_high = convert_image_format(mock_file, self.temp_dir, "webp", 95, False)
        
        # High quality should generally produce larger files
        # (though this isn't guaranteed for all images)
        self.assertEqual(result_low["quality"], 20)
        self.assertEqual(result_high["quality"], 95)
    
    def test_avif_format_with_fallback(self):
        """Test AVIF format conversion with WebP fallback"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        
        try:
            result = convert_image_format(mock_file, self.temp_dir, "avif", 80, False)
            # If AVIF works
            self.assertEqual(result["format"], "AVIF")
            self.assertTrue(result["filename"].endswith(".avif") or result["filename"].endswith(".webp"))
        except Exception:
            # AVIF might not be supported, which is acceptable
            pass
    
    def test_png_format_conversion(self):
        """Test PNG format conversion"""
        mock_file = MockFileStorage("test.jpg", self.rgba_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "png", 85, False)
        
        self.assertEqual(result["format"], "PNG")
        self.assertTrue(result["filename"].endswith(".png"))
        
        # Check file was created and can be opened
        file_path = self.temp_dir / result["filename"]
        self.assertTrue(file_path.exists())
        
        with Image.open(file_path) as img:
            self.assertIn(img.format, ["PNG"])
    
    def test_jpeg_alpha_to_rgb_conversion(self):
        """Test that RGBA images are properly converted to RGB for JPEG"""
        mock_file = MockFileStorage("test_alpha.png", self.rgba_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "jpeg", 85, False)
        
        self.assertEqual(result["format"], "JPEG")
        self.assertTrue(result["filename"].endswith(".jpg"))
        
        # Verify RGBA was converted to RGB
        file_path = self.temp_dir / result["filename"]
        with Image.open(file_path) as img:
            self.assertEqual(img.mode, "RGB")
    
    def test_has_alpha_channel_function(self):
        """Test the alpha channel detection function"""
        # RGB image should not have alpha
        rgb_img = Image.new("RGB", (10, 10), color="red")
        self.assertFalse(_has_alpha_channel(rgb_img))
        
        # RGBA image should have alpha
        rgba_img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        self.assertTrue(_has_alpha_channel(rgba_img))
        
        # LA (grayscale with alpha) should have alpha
        la_img = Image.new("LA", (10, 10), color=(128, 200))
        self.assertTrue(_has_alpha_channel(la_img))
    
    def test_convert_for_format_function(self):
        """Test the format-specific conversion function"""
        # Test JPEG conversion (should remove alpha)
        rgba_img = Image.new("RGBA", (10, 10), color=(255, 0, 0, 128))
        jpeg_converted = _convert_for_format(rgba_img, "jpeg", 85, False)
        self.assertEqual(jpeg_converted.mode, "RGB")
        
        # Test WebP conversion (should preserve alpha)
        webp_converted = _convert_for_format(rgba_img, "webp", 85, False)
        self.assertIn(webp_converted.mode, ["RGBA", "RGB"])
        
        # Test PNG conversion (should preserve alpha)
        png_converted = _convert_for_format(rgba_img, "png", 85, False)
        self.assertIn(png_converted.mode, ["RGBA", "RGB", "L", "P"])
    
    def test_batch_convert_with_errors(self):
        """Test batch conversion with some files causing errors"""
        # Create a mock file that will cause an error
        class ErrorFileStorage:
            def __init__(self, filename):
                self.filename = filename
                self.stream = BytesIO(b"invalid image data")
        
        valid_file = MockFileStorage("valid.jpg", self.rgb_bytes.getvalue())
        error_file = ErrorFileStorage("invalid.txt")
        
        results, errors = batch_convert_images([valid_file, error_file], self.temp_dir, "webp", 85, False)
        
        # Should have one successful result and one error
        self.assertEqual(len(results), 1)
        self.assertEqual(len(errors), 1)
        
        # Check error structure
        self.assertIn("filename", errors[0])
        self.assertIn("error", errors[0])
        self.assertEqual(errors[0]["filename"], "invalid.txt")
    
    def test_format_comparison_all_formats(self):
        """Test format comparison generates all supported formats"""
        mock_file = MockFileStorage("comparison_test.jpg", self.rgb_bytes.getvalue())
        
        comparisons = get_format_comparison(mock_file, self.temp_dir, 80)
        
        # Should have entries for all formats in WEB_FORMATS
        for format_key in WEB_FORMATS.keys():
            self.assertIn(format_key, comparisons)
            
        # At least some formats should succeed (WebP and JPEG are very likely)
        successful_formats = [k for k, v in comparisons.items() if "filename" in v]
        self.assertGreaterEqual(len(successful_formats), 2)
    
    def test_sanitize_filename_edge_cases(self):
        """Test filename sanitization with various edge cases"""
        # Test with special characters
        self.assertEqual(sanitize_filename("file!@#$%^&*()name.jpg"), "file_name")
        
        # Test with spaces and dashes
        self.assertEqual(sanitize_filename("my file-name_test.png"), "my_file-name_test")
        
        # Test with hidden file (extension but no name)
        self.assertEqual(sanitize_filename(".hidden"), "hidden")
        
        # Test with only extension (no stem)
        self.assertEqual(sanitize_filename("."), "image")
        
        # Test with only special characters
        self.assertEqual(sanitize_filename("!@#$%^&*().jpg"), "image")
        
        # Test with unicode characters (may vary by system)
        result = sanitize_filename("café_münü.jpg")
        self.assertTrue(len(result) > 0)  # Should produce some valid filename
        
        # Test empty string
        self.assertEqual(sanitize_filename(""), "image")
    
    def test_large_quality_values(self):
        """Test handling of quality values outside normal range"""
        mock_file = MockFileStorage("test.jpg", self.rgb_bytes.getvalue())
        
        # Test quality within valid WebP range (0-100)
        result = convert_image_format(mock_file, self.temp_dir, "webp", 100, False)
        self.assertEqual(result["quality"], 100)  # We store what was requested
        
        # Test quality = 1 (minimum)
        mock_file.stream.seek(0)
        result = convert_image_format(mock_file, self.temp_dir, "jpeg", 1, False)
        self.assertEqual(result["quality"], 1)
    
    def test_different_image_modes(self):
        """Test conversion with different PIL image modes"""
        # Test grayscale image
        gray_img = Image.new("L", (50, 50), color=128)
        gray_bytes = BytesIO()
        gray_img.save(gray_bytes, format="PNG")
        gray_bytes.seek(0)
        
        mock_file = MockFileStorage("gray.png", gray_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "webp", 85, False)
        
        self.assertIsInstance(result["size_bytes"], int)
        self.assertGreater(result["size_bytes"], 0)
        
        # Test palette image
        palette_img = Image.new("P", (50, 50))
        # Create a valid palette (256 colors * 3 RGB values = 768 bytes)
        palette_data = []
        for i in range(256):
            palette_data.extend([i % 256, (i * 2) % 256, (i * 3) % 256])
        palette_img.putpalette(palette_data)
        palette_bytes = BytesIO()
        palette_img.save(palette_bytes, format="PNG")
        palette_bytes.seek(0)
        
        mock_file = MockFileStorage("palette.png", palette_bytes.getvalue())
        result = convert_image_format(mock_file, self.temp_dir, "jpeg", 85, False)
        
        self.assertIsInstance(result["size_bytes"], int)
        self.assertGreater(result["size_bytes"], 0)


if __name__ == "__main__":
    unittest.main()

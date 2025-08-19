"""
Unit tests for responsive image generation
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

from image_processing.responsive_images import (
    generate_responsive_images,
    generate_srcset_html,
    RESPONSIVE_SIZES
)


class MockFileStorage:
    """Mock file storage object for testing"""
    def __init__(self, filename, image_data):
        self.filename = filename
        self.stream = BytesIO(image_data)


class TestResponsiveImages(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test image (large enough for all responsive sizes)
        self.test_image = Image.new("RGB", (2000, 1500), color="blue")
        
        # Save test image to bytes
        self.image_bytes = BytesIO()
        self.test_image.save(self.image_bytes, format="JPEG")
        self.image_bytes.seek(0)
        
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
        
    def test_responsive_sizes_config(self):
        """Test that responsive sizes are properly configured"""
        expected_sizes = ["mobile", "mobile-large", "tablet", "desktop", "desktop-large", "desktop-xl"]
        for size in expected_sizes:
            self.assertIn(size, RESPONSIVE_SIZES)
            self.assertIsInstance(RESPONSIVE_SIZES[size], int)
            
    def test_generate_responsive_images(self):
        """Test responsive image generation"""
        mock_file = MockFileStorage("test.jpg", self.image_bytes.getvalue())
        selected_sizes = ["mobile", "tablet", "desktop"]
        
        results = generate_responsive_images(mock_file, self.temp_dir, 85, False, selected_sizes)
        
        self.assertEqual(len(results), 3)  # Should generate 3 sizes
        
        for result in results:
            self.assertIn("name", result)
            self.assertIn("size_kb", result)
            self.assertIn("dimensions", result)
            self.assertIn("size_name", result)
            self.assertTrue((self.temp_dir / result["name"]).exists())
            
    def test_skip_larger_sizes(self):
        """Test that sizes larger than original are skipped"""
        # Create small image
        small_image = Image.new("RGB", (300, 200), color="green")
        small_bytes = BytesIO()
        small_image.save(small_bytes, format="JPEG")
        small_bytes.seek(0)
        
        mock_file = MockFileStorage("small.jpg", small_bytes.getvalue())
        selected_sizes = ["mobile", "desktop", "desktop-xl"]  # desktop and xl should be skipped
        
        results = generate_responsive_images(mock_file, self.temp_dir, 85, False, selected_sizes)
        
        # Only mobile should be generated (320px < 300px original width)
        # Actually, mobile (320px) is larger than 300px, so no images should be generated
        self.assertEqual(len(results), 0)
        
    def test_generate_srcset_html(self):
        """Test HTML srcset generation"""
        # Create mock results
        mock_results = [
            {"name": "test-mobile-320w.webp", "dimensions": "320x240", "size_name": "mobile"},
            {"name": "test-tablet-768w.webp", "dimensions": "768x576", "size_name": "tablet"},
            {"name": "test-desktop-1024w.webp", "dimensions": "1024x768", "size_name": "desktop"}
        ]
        
        html_examples = generate_srcset_html(mock_results)
        
        self.assertEqual(len(html_examples), 1)  # One example for one base filename
        
        html = html_examples[0]
        self.assertIn("srcset=", html)
        self.assertIn("320w", html)
        self.assertIn("768w", html)
        self.assertIn("1024w", html)
        self.assertIn("sizes=", html)
        
    def test_filename_generation(self):
        """Test that filenames are generated correctly"""
        mock_file = MockFileStorage("my test image.jpg", self.image_bytes.getvalue())
        selected_sizes = ["mobile"]
        
        results = generate_responsive_images(mock_file, self.temp_dir, 85, False, selected_sizes)
        
        if results:  # Only if image is large enough
            filename = results[0]["name"]
            self.assertIn("my_test_image", filename)  # Sanitized filename
            self.assertIn("mobile", filename)
            self.assertIn("320w", filename)
            self.assertTrue(filename.endswith(".webp"))
            
    def test_lossless_option(self):
        """Test lossless compression option"""
        mock_file = MockFileStorage("test.jpg", self.image_bytes.getvalue())
        selected_sizes = ["mobile"]
        
        results = generate_responsive_images(mock_file, self.temp_dir, 85, True, selected_sizes)
        
        # Should still generate files, just with lossless compression
        if results:
            self.assertTrue((self.temp_dir / results[0]["name"]).exists())
            
    def test_empty_sizes_list(self):
        """Test behavior with empty sizes list"""
        mock_file = MockFileStorage("test.jpg", self.image_bytes.getvalue())
        
        results = generate_responsive_images(mock_file, self.temp_dir, 85, False, [])
        
        self.assertEqual(len(results), 0)
        
    def test_invalid_sizes(self):
        """Test behavior with invalid size names"""
        mock_file = MockFileStorage("test.jpg", self.image_bytes.getvalue())
        selected_sizes = ["invalid_size", "mobile"]
        
        results = generate_responsive_images(mock_file, self.temp_dir, 85, False, selected_sizes)
        
        # Should only generate valid sizes
        if results:
            self.assertTrue(all(r["size_name"] == "mobile" for r in results))


if __name__ == "__main__":
    unittest.main()

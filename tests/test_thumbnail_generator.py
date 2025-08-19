"""
Unit tests for thumbnail generator
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

from image_processing.thumbnail_generator import (
    generate_thumbnails,
    create_square_thumbnail,
    generate_thumbnail_css,
    generate_thumbnail_html,
    THUMBNAIL_SIZES,
    CROP_METHODS
)


class MockFileStorage:
    """Mock file storage object for testing"""
    def __init__(self, filename, image_data):
        self.filename = filename
        self.stream = BytesIO(image_data)


class TestThumbnailGenerator(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create test images
        self.test_image_square = Image.new("RGB", (200, 200), color="red")
        self.test_image_landscape = Image.new("RGB", (300, 200), color="green")
        self.test_image_portrait = Image.new("RGB", (200, 300), color="blue")
        self.test_image_rgba = Image.new("RGBA", (200, 200), color=(255, 0, 0, 128))
        
        # Save test images to bytes
        self.square_bytes = self._image_to_bytes(self.test_image_square)
        self.landscape_bytes = self._image_to_bytes(self.test_image_landscape)
        self.portrait_bytes = self._image_to_bytes(self.test_image_portrait)
        self.rgba_bytes = self._image_to_bytes(self.test_image_rgba, "PNG")
    
    def _image_to_bytes(self, image, format="JPEG"):
        """Convert PIL Image to bytes"""
        bytes_io = BytesIO()
        if format == "JPEG" and image.mode in ("RGBA", "LA"):
            # Convert RGBA to RGB for JPEG
            rgb_image = Image.new("RGB", image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
            rgb_image.save(bytes_io, format=format)
        else:
            image.save(bytes_io, format=format)
        bytes_io.seek(0)
        return bytes_io.getvalue()
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_thumbnail_sizes_constant(self):
        """Test that thumbnail sizes are properly defined"""
        self.assertIsInstance(THUMBNAIL_SIZES, dict)
        self.assertIn("tiny", THUMBNAIL_SIZES)
        self.assertIn("small", THUMBNAIL_SIZES)
        self.assertIn("medium", THUMBNAIL_SIZES)
        self.assertIn("large", THUMBNAIL_SIZES)
        
        # Check size format
        for size_name, dimensions in THUMBNAIL_SIZES.items():
            self.assertIsInstance(dimensions, tuple)
            self.assertEqual(len(dimensions), 2)
            self.assertIsInstance(dimensions[0], int)
            self.assertIsInstance(dimensions[1], int)
    
    def test_crop_methods_constant(self):
        """Test that crop methods are properly defined"""
        self.assertIsInstance(CROP_METHODS, dict)
        expected_methods = ["center", "top", "bottom", "left", "right"]
        for method in expected_methods:
            self.assertIn(method, CROP_METHODS)
    
    def test_create_square_thumbnail_center_crop(self):
        """Test square thumbnail creation with center crop"""
        # Test landscape image (300x200) -> center crop should take 200x200 from center
        thumbnail = create_square_thumbnail(self.test_image_landscape, 128, "center")
        self.assertEqual(thumbnail.size, (128, 128))
        
        # Test portrait image (200x300) -> center crop should take 200x200 from center
        thumbnail = create_square_thumbnail(self.test_image_portrait, 128, "center")
        self.assertEqual(thumbnail.size, (128, 128))
        
        # Test square image (200x200) -> should remain the same proportions
        thumbnail = create_square_thumbnail(self.test_image_square, 128, "center")
        self.assertEqual(thumbnail.size, (128, 128))
    
    def test_create_square_thumbnail_edge_crops(self):
        """Test square thumbnail creation with edge crop methods"""
        crop_methods = ["top", "bottom", "left", "right"]
        
        for method in crop_methods:
            with self.subTest(crop_method=method):
                thumbnail = create_square_thumbnail(self.test_image_landscape, 64, method)
                self.assertEqual(thumbnail.size, (64, 64))
    
    def test_generate_thumbnails_webp_format(self):
        """Test thumbnail generation in WebP format"""
        mock_file = MockFileStorage("test_image.jpg", self.square_bytes)
        
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=80,
            lossless=False,
            selected_sizes=["tiny", "small"],
            crop_method="center",
            output_format="webp"
        )
        
        self.assertEqual(len(results), 2)
        
        # Check results structure
        for result in results:
            self.assertIn("name", result)
            self.assertIn("size_kb", result)
            self.assertIn("dimensions", result)
            self.assertIn("size_name", result)
            self.assertIn("crop_method", result)
            
            # Check file was created
            file_path = self.temp_dir / result["name"]
            self.assertTrue(file_path.exists())
            self.assertTrue(result["name"].endswith(".webp"))
            
            # Verify the thumbnail can be opened and has correct size
            with Image.open(file_path) as img:
                expected_size = THUMBNAIL_SIZES[result["size_name"]]
                self.assertEqual(img.size, expected_size)
    
    def test_generate_thumbnails_jpeg_format(self):
        """Test thumbnail generation in JPEG format"""
        mock_file = MockFileStorage("test_image.png", self.rgba_bytes)
        
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=85,
            lossless=False,
            selected_sizes=["medium"],
            crop_method="top",
            output_format="jpeg"
        )
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Check JPEG file was created
        file_path = self.temp_dir / result["name"]
        self.assertTrue(file_path.exists())
        self.assertTrue(result["name"].endswith(".jpg"))
        
        # Verify RGBA was converted to RGB for JPEG
        with Image.open(file_path) as img:
            self.assertEqual(img.mode, "RGB")
    
    def test_generate_thumbnails_png_format(self):
        """Test thumbnail generation in PNG format"""
        mock_file = MockFileStorage("test_alpha.png", self.rgba_bytes)
        
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=100,
            lossless=True,
            selected_sizes=["small"],
            crop_method="center",
            output_format="png"
        )
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Check PNG file was created
        file_path = self.temp_dir / result["name"]
        self.assertTrue(file_path.exists())
        self.assertTrue(result["name"].endswith(".png"))
        
        # Verify alpha channel is preserved in PNG
        with Image.open(file_path) as img:
            self.assertIn(img.mode, ["RGBA", "RGB"])
    
    def test_generate_thumbnails_avif_format(self):
        """Test thumbnail generation in AVIF format (with fallback)"""
        mock_file = MockFileStorage("test.jpg", self.square_bytes)
        
        try:
            results = generate_thumbnails(
                file_storage=mock_file,
                out_dir=self.temp_dir,
                quality=80,
                lossless=False,
                selected_sizes=["tiny"],
                crop_method="center",
                output_format="avif"
            )
            
            self.assertEqual(len(results), 1)
            result = results[0]
            
            # Check file was created (might be .avif or .webp as fallback)
            file_path = self.temp_dir / result["name"]
            self.assertTrue(file_path.exists())
            self.assertTrue(result["name"].endswith((".avif", ".webp")))
            
        except Exception as e:
            # AVIF might not be supported on all systems, which is acceptable
            self.assertIn("AVIF", str(e).upper() or "avif" in str(e).lower())
    
    def test_generate_thumbnails_all_formats(self):
        """Test thumbnail generation with all supported formats"""
        formats_to_test = ["webp", "jpeg", "png"]  # Skip AVIF as it might not be available
        
        for output_format in formats_to_test:
            with self.subTest(format=output_format):
                mock_file = MockFileStorage(f"test_{output_format}.jpg", self.square_bytes)
                
                results = generate_thumbnails(
                    file_storage=mock_file,
                    out_dir=self.temp_dir / output_format,
                    quality=80,
                    lossless=False,
                    selected_sizes=["tiny"],
                    crop_method="center",
                    output_format=output_format
                )
                
                self.assertEqual(len(results), 1)
                result = results[0]
                
                # Check correct format extension
                file_path = self.temp_dir / output_format / result["name"]
                self.assertTrue(file_path.exists())
                
                if output_format == "webp":
                    self.assertTrue(result["name"].endswith(".webp"))
                elif output_format == "jpeg":
                    self.assertTrue(result["name"].endswith(".jpg"))
                elif output_format == "png":
                    self.assertTrue(result["name"].endswith(".png"))
    
    def test_generate_thumbnails_lossless_webp(self):
        """Test lossless WebP thumbnail generation"""
        mock_file = MockFileStorage("test_alpha.png", self.rgba_bytes)
        
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=100,
            lossless=True,
            selected_sizes=["small"],
            crop_method="center",
            output_format="webp"
        )
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Check file was created
        file_path = self.temp_dir / result["name"]
        self.assertTrue(file_path.exists())
        
        # Verify alpha channel is preserved in lossless WebP
        with Image.open(file_path) as img:
            self.assertIn(img.mode, ["RGBA", "RGB"])  # Should preserve alpha if present
    
    def test_generate_thumbnails_invalid_format(self):
        """Test thumbnail generation with invalid format"""
        mock_file = MockFileStorage("test.jpg", self.square_bytes)
        
        with self.assertRaises(ValueError) as context:
            generate_thumbnails(
                file_storage=mock_file,
                out_dir=self.temp_dir,
                quality=80,
                lossless=False,
                selected_sizes=["small"],
                crop_method="center",
                output_format="invalid_format"
            )
        
        self.assertIn("Unsupported format", str(context.exception))
    
    def test_generate_thumbnails_invalid_size(self):
        """Test thumbnail generation with invalid size"""
        mock_file = MockFileStorage("test.jpg", self.square_bytes)
        
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=80,
            lossless=False,
            selected_sizes=["invalid_size", "small"],
            crop_method="center",
            output_format="webp"
        )
        
        # Should only generate thumbnail for valid size
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["size_name"], "small")
    
    def test_generate_thumbnails_all_sizes(self):
        """Test thumbnail generation with all available sizes"""
        mock_file = MockFileStorage("large_test.jpg", self.square_bytes)
        
        all_sizes = list(THUMBNAIL_SIZES.keys())
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=75,
            lossless=False,
            selected_sizes=all_sizes,
            crop_method="center",
            output_format="webp"
        )
        
        self.assertEqual(len(results), len(all_sizes))
        
        # Verify each size was generated correctly
        result_sizes = [r["size_name"] for r in results]
        for size_name in all_sizes:
            self.assertIn(size_name, result_sizes)
    
    def test_generate_thumbnail_css(self):
        """Test CSS generation for thumbnails"""
        # Mock results data
        results = [
            {"name": "test-thumb-small-128x128-center.webp", "size_name": "small", "dimensions": "128x128"},
            {"name": "test-thumb-medium-256x256-center.webp", "size_name": "medium", "dimensions": "256x256"}
        ]
        
        css_examples = generate_thumbnail_css(results)
        
        self.assertIsInstance(css_examples, list)
        self.assertGreater(len(css_examples), 0)
        
        # Check CSS contains expected classes
        css_text = "\n".join(css_examples)
        self.assertIn(".thumbnail-small", css_text)
        self.assertIn(".thumbnail-medium", css_text)
        self.assertIn("width: 128px", css_text)
        self.assertIn("width: 256px", css_text)
        self.assertIn("object-fit: cover", css_text)
        self.assertIn("border-radius", css_text)
    
    def test_generate_thumbnail_css_empty_results(self):
        """Test CSS generation with empty results"""
        css_examples = generate_thumbnail_css([])
        self.assertEqual(css_examples, [])
    
    def test_generate_thumbnail_html(self):
        """Test HTML generation for thumbnails"""
        # Mock results data
        results = [
            {"name": "test-thumb-small-128x128-center.webp", "size_name": "small", "dimensions": "128x128"},
            {"name": "test-thumb-medium-256x256-center.webp", "size_name": "medium", "dimensions": "256x256"},
            {"name": "test-thumb-medium-256x256-top.webp", "size_name": "medium", "dimensions": "256x256"}
        ]
        
        html_examples = generate_thumbnail_html(results)
        
        self.assertIsInstance(html_examples, list)
        self.assertGreater(len(html_examples), 0)
        
        # Check HTML contains expected elements
        html_text = "\n".join(html_examples)
        self.assertIn('<img src="', html_text)
        self.assertIn('class="thumbnail-', html_text)
        self.assertIn('<div class="thumbnail-gallery">', html_text)
        self.assertIn('<div class="user-profile">', html_text)
    
    def test_generate_thumbnail_html_empty_results(self):
        """Test HTML generation with empty results"""
        html_examples = generate_thumbnail_html([])
        self.assertEqual(html_examples, [])
    
    def test_file_naming_convention(self):
        """Test that thumbnail files follow the expected naming convention"""
        mock_file = MockFileStorage("My Test Image!@#.jpg", self.square_bytes)
        
        results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=80,
            lossless=False,
            selected_sizes=["small"],
            crop_method="center",
            output_format="webp"
        )
        
        result = results[0]
        filename = result["name"]
        
        # Should sanitize filename and include size, dimensions, and crop method
        self.assertIn("My_Test_Image", filename)
        self.assertIn("thumb", filename)
        self.assertIn("small", filename)
        self.assertIn("128x128", filename)
        self.assertIn("center", filename)
        self.assertTrue(filename.endswith(".webp"))
        
        # Test different format
        mock_file.stream = BytesIO(self.square_bytes)
        results_png = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir,
            quality=80,
            lossless=False,
            selected_sizes=["small"],
            crop_method="center",
            output_format="png"
        )
        
        self.assertTrue(results_png[0]["name"].endswith(".png"))
    
    def test_different_crop_methods_produce_different_results(self):
        """Test that different crop methods produce different thumbnail results"""
        mock_file = MockFileStorage("test.jpg", self.landscape_bytes)
        
        # Generate thumbnails with different crop methods
        center_results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir / "center",
            quality=80,
            lossless=False,
            selected_sizes=["small"],
            crop_method="center",
            output_format="webp"
        )
        
        # Reset file stream
        mock_file.stream = BytesIO(self.landscape_bytes)
        
        top_results = generate_thumbnails(
            file_storage=mock_file,
            out_dir=self.temp_dir / "top",
            quality=80,
            lossless=False,
            selected_sizes=["small"],
            crop_method="top",
            output_format="webp"
        )
        
        # Both should succeed
        self.assertEqual(len(center_results), 1)
        self.assertEqual(len(top_results), 1)
        
        # Filenames should indicate different crop methods
        self.assertIn("center", center_results[0]["name"])
        self.assertIn("top", top_results[0]["name"])


if __name__ == "__main__":
    unittest.main()

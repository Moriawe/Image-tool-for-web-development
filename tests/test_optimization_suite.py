"""
Unit tests for the optimization_suite module
"""
import io
import pytest
from PIL import Image
from pathlib import Path
import tempfile
import shutil
from werkzeug.datastructures import FileStorage

from image_processing.optimization_suite import (
    optimize_image,
    batch_optimize_images,
    analyze_image_complexity,
    generate_optimization_report,
    extract_image_metadata,
    OPTIMIZATION_PRESETS,
    _resize_if_needed,
    _determine_optimal_format,
    _estimate_original_size
)


class TestOptimizationSuite:
    """Test suite for optimization_suite functions"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample test image"""
        img = Image.new("RGB", (800, 600), color="red")
        return img
    
    @pytest.fixture
    def sample_image_with_alpha(self):
        """Create a sample test image with transparency"""
        img = Image.new("RGBA", (400, 400), color=(255, 0, 0, 128))
        return img
    
    @pytest.fixture
    def file_storage_from_image(self, sample_image):
        """Create a FileStorage object from an image"""
        buffer = io.BytesIO()
        sample_image.save(buffer, format="PNG")
        buffer.seek(0)
        return FileStorage(
            stream=buffer,
            filename="test_image.png",
            content_type="image/png"
        )
    
    def test_optimization_presets_exist(self):
        """Test that optimization presets are properly defined"""
        assert len(OPTIMIZATION_PRESETS) > 0
        
        required_keys = ["name", "description", "max_width", "max_height", 
                        "quality", "strip_metadata", "optimize"]
        
        for preset_name, preset_config in OPTIMIZATION_PRESETS.items():
            for key in required_keys:
                assert key in preset_config, f"Missing key '{key}' in preset '{preset_name}'"
            
            # Validate ranges
            assert 1 <= preset_config["quality"] <= 100
            assert preset_config["max_width"] > 0
            assert preset_config["max_height"] > 0
            assert isinstance(preset_config["strip_metadata"], bool)
            assert isinstance(preset_config["optimize"], bool)
    
    def test_optimize_image_basic(self, file_storage_from_image, temp_dir):
        """Test basic image optimization"""
        result = optimize_image(
            file_storage_from_image, 
            temp_dir, 
            "web_basic", 
            "webp"
        )
        
        # Check result structure
        required_keys = [
            "filename", "size_bytes", "size_kb", "format", 
            "original_dimensions", "optimized_dimensions", 
            "quality", "preset", "compression_ratio"
        ]
        
        for key in required_keys:
            assert key in result, f"Missing key '{key}' in result"
        
        # Check file was created
        output_file = temp_dir / result["filename"]
        assert output_file.exists()
        assert output_file.stat().st_size > 0
        
        # Check values are reasonable
        assert result["size_kb"] > 0
        assert 0 <= result["compression_ratio"] <= 100
        assert result["format"] == "WebP"
        assert result["preset"] == OPTIMIZATION_PRESETS["web_basic"]["name"]
    
    def test_optimize_image_auto_format(self, file_storage_from_image, temp_dir):
        """Test auto format selection"""
        result = optimize_image(
            file_storage_from_image, 
            temp_dir, 
            "web_basic", 
            "auto"
        )
        
        # Should select WebP for most images
        assert result["format"] in ["WebP", "PNG", "JPEG", "AVIF"]
        
        output_file = temp_dir / result["filename"]
        assert output_file.exists()
    
    def test_optimize_image_custom_settings(self, file_storage_from_image, temp_dir):
        """Test optimization with custom settings"""
        custom_quality = 90
        custom_max_size = (400, 300)
        
        result = optimize_image(
            file_storage_from_image, 
            temp_dir, 
            "web_basic", 
            "webp",
            custom_quality=custom_quality,
            custom_max_size=custom_max_size
        )
        
        assert result["quality"] == custom_quality
        
        # Check that image was resized (original was 800x600, max is 400x300)
        dimensions = result["optimized_dimensions"]
        width, height = map(int, dimensions.split('x'))
        assert width <= 400
        assert height <= 300
    
    def test_batch_optimize_images(self, sample_image, temp_dir):
        """Test batch optimization"""
        # Create multiple FileStorage objects
        files = []
        for i in range(3):
            buffer = io.BytesIO()
            # Create different sized images
            img = sample_image.resize((600 + i*100, 400 + i*50))
            img.save(buffer, format="PNG")
            buffer.seek(0)
            files.append(FileStorage(
                stream=buffer,
                filename=f"test_image_{i}.png",
                content_type="image/png"
            ))
        
        results, errors, batch_stats = batch_optimize_images(
            files, temp_dir, "web_basic", "webp"
        )
        
        # Check results
        assert len(results) == 3
        assert len(errors) == 0
        
        # Check batch stats
        assert batch_stats["total_files"] == 3
        assert batch_stats["successful"] == 3
        assert batch_stats["failed"] == 0
        assert batch_stats["total_original_kb"] > 0
        assert batch_stats["total_optimized_kb"] > 0
        assert 0 <= batch_stats["overall_compression_ratio"] <= 100
        
        # Check files were created
        for result in results:
            output_file = temp_dir / result["filename"]
            assert output_file.exists()
    
    def test_resize_if_needed(self, sample_image):
        """Test image resizing function"""
        # Image that needs resizing (800x600 -> max 400x300)
        resized = _resize_if_needed(sample_image, 400, 300)
        
        # Should maintain aspect ratio and fit within bounds
        assert resized.size[0] <= 400
        assert resized.size[1] <= 300
        
        # Check aspect ratio maintained (approximately)
        original_ratio = sample_image.size[0] / sample_image.size[1]
        resized_ratio = resized.size[0] / resized.size[1]
        assert abs(original_ratio - resized_ratio) < 0.01
        
        # Image that doesn't need resizing
        no_resize = _resize_if_needed(sample_image, 1000, 800)
        assert no_resize.size == sample_image.size
    
    def test_determine_optimal_format(self, sample_image, sample_image_with_alpha):
        """Test optimal format determination"""
        # RGB image should prefer WebP
        format1 = _determine_optimal_format(sample_image, "test.jpg")
        assert format1 in ["webp", "jpeg"]
        
        # RGBA image should prefer WebP (supports transparency)
        format2 = _determine_optimal_format(sample_image_with_alpha, "test.png")
        assert format2 == "webp"
        
        # Small PNG should stay PNG for compatibility
        small_img = sample_image.resize((100, 100))
        format3 = _determine_optimal_format(small_img, "icon.png")
        assert format3 in ["png", "webp"]
    
    def test_analyze_image_complexity(self, sample_image):
        """Test image complexity analysis"""
        analysis = analyze_image_complexity(sample_image)
        
        required_keys = [
            "complexity", "color_range", "suggested_quality", 
            "is_likely_photo", "total_pixels"
        ]
        
        for key in required_keys:
            assert key in analysis
        
        assert analysis["complexity"] in ["low", "medium", "high"]
        assert 1 <= analysis["suggested_quality"] <= 100
        assert isinstance(analysis["is_likely_photo"], bool)
        assert analysis["total_pixels"] == sample_image.size[0] * sample_image.size[1]
    
    def test_extract_image_metadata(self, sample_image):
        """Test metadata extraction"""
        metadata = extract_image_metadata(sample_image)
        
        assert "format" in metadata
        assert "mode" in metadata
        assert "size" in metadata
        assert "has_exif" in metadata
        
        assert metadata["mode"] == sample_image.mode
        assert metadata["size"] == sample_image.size
    
    def test_generate_optimization_report(self):
        """Test optimization report generation"""
        # Mock results data
        results = [
            {
                "filename": "test1.webp",
                "size_kb": 45.2,
                "format": "WebP",
                "quality": 85,
                "compression_ratio": 65.0
            },
            {
                "filename": "test2.webp", 
                "size_kb": 38.7,
                "format": "WebP",
                "quality": 80,
                "compression_ratio": 70.0
            }
        ]
        
        batch_stats = {
            "total_files": 2,
            "successful": 2,
            "failed": 0,
            "total_original_kb": 150.0,
            "total_optimized_kb": 83.9,
            "overall_compression_ratio": 67.5
        }
        
        report = generate_optimization_report(results, batch_stats)
        
        assert "summary" in report
        assert "format_breakdown" in report
        assert "quality_distribution" in report
        assert "batch_stats" in report
        
        # Check summary
        assert report["summary"]["total_files"] == 2
        assert report["summary"]["average_compression_ratio"] == 67.5
        assert "WebP" in report["summary"]["formats_used"]
        
        # Check format breakdown
        assert "WebP" in report["format_breakdown"]
        assert report["format_breakdown"]["WebP"]["count"] == 2
        
        # Check quality distribution
        assert 80 in report["quality_distribution"]
        assert 85 in report["quality_distribution"]
    
    def test_estimate_original_size(self, sample_image):
        """Test original size estimation"""
        estimated_size = _estimate_original_size(sample_image)
        
        assert isinstance(estimated_size, int)
        assert estimated_size > 0
        
        # Should be reasonable for an 800x600 image (solid color compresses well)
        assert 1000 < estimated_size < 5000000  # Between 1KB and 5MB
    
    def test_invalid_preset(self, file_storage_from_image, temp_dir):
        """Test handling of invalid preset"""
        with pytest.raises(ValueError, match="Unknown preset"):
            optimize_image(
                file_storage_from_image, 
                temp_dir, 
                "invalid_preset", 
                "webp"
            )
    
    def test_empty_results_report(self):
        """Test report generation with empty results"""
        report = generate_optimization_report([])
        
        assert "error" in report
        assert report["error"] == "No results to analyze"


if __name__ == "__main__":
    pytest.main([__file__])

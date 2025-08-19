"""
Unit tests for the image_analysis module
"""
import io
import pytest
from PIL import Image
from pathlib import Path
import tempfile
import shutil
from werkzeug.datastructures import FileStorage

from image_processing.image_analysis import (
    analyze_image_comprehensive,
    batch_analyze_images,
    _get_basic_info,
    _analyze_colors,
    _analyze_complexity,
    _analyze_color_harmony,
    _get_format_recommendations,
    _get_optimization_suggestions,
    _calculate_web_metrics,
    _extract_detailed_metadata,
    _generate_batch_insights
)


class TestImageAnalysis:
    """Test suite for image_analysis functions"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for tests"""
        temp_path = Path(tempfile.mkdtemp())
        yield temp_path
        shutil.rmtree(temp_path)
    
    @pytest.fixture
    def sample_photo_image(self):
        """Create a sample photo-like test image with high complexity"""
        img = Image.new("RGB", (800, 600))
        # Create a photo-like pattern with varying colors
        pixels = []
        for y in range(600):
            for x in range(800):
                r = int(128 + 50 * ((x + y) % 100) / 100)
                g = int(100 + 80 * ((x * 2 + y) % 150) / 150)
                b = int(80 + 70 * ((x + y * 2) % 120) / 120)
                pixels.append((r, g, b))
        img.putdata(pixels)
        return img
    
    @pytest.fixture
    def sample_graphic_image(self):
        """Create a sample graphic-like test image with low complexity"""
        img = Image.new("RGB", (400, 300), color=(255, 255, 255))
        # Add simple geometric shapes
        pixels = list(img.getdata())
        width = 400
        for i, (r, g, b) in enumerate(pixels):
            x = i % width
            y = i // width
            if 100 <= x <= 300 and 50 <= y <= 250:
                pixels[i] = (50, 100, 200)  # Blue rectangle
            elif 150 <= x <= 250 and 100 <= y <= 200:
                pixels[i] = (200, 50, 50)   # Red rectangle
        img.putdata(pixels)
        return img
    
    @pytest.fixture
    def sample_transparent_image(self):
        """Create a sample image with transparency"""
        img = Image.new("RGBA", (300, 300), color=(255, 0, 0, 128))
        return img
    
    @pytest.fixture
    def file_storage_from_image(self, sample_photo_image):
        """Create a FileStorage object from an image"""
        buffer = io.BytesIO()
        sample_photo_image.save(buffer, format="PNG")
        buffer.seek(0)
        return FileStorage(
            stream=buffer,
            filename="test_photo.png",
            content_type="image/png"
        )
    
    def test_analyze_image_comprehensive(self, file_storage_from_image):
        """Test comprehensive image analysis"""
        result = analyze_image_comprehensive(file_storage_from_image)
        
        # Check main structure
        required_keys = [
            "basic_info", "color_analysis", "complexity_analysis",
            "format_recommendations", "optimization_suggestions",
            "web_metrics", "metadata", "filename"
        ]
        
        for key in required_keys:
            assert key in result, f"Missing key '{key}' in analysis result"
        
        # Check filename sanitization
        assert result["filename"] == "test_photo"
        
        # Verify basic info structure
        basic_info = result["basic_info"]
        assert "dimensions" in basic_info
        assert "width" in basic_info
        assert "height" in basic_info
        assert basic_info["width"] == 800
        assert basic_info["height"] == 600
    
    def test_get_basic_info(self, sample_photo_image, sample_transparent_image):
        """Test basic information extraction"""
        # Test photo image
        info = _get_basic_info(sample_photo_image)
        
        assert info["width"] == 800
        assert info["height"] == 600
        assert info["total_pixels"] == 480000
        assert info["megapixels"] == 0.48
        assert info["aspect_ratio"] == pytest.approx(1.33, rel=0.01)
        assert info["category"] == "standard"
        assert info["mode"] == "RGB"
        assert not info["has_transparency"]
        
        # Test transparent image
        info_transparent = _get_basic_info(sample_transparent_image)
        assert info_transparent["mode"] == "RGBA"
        assert info_transparent["has_transparency"]
        assert info_transparent["category"] == "square"
    
    def test_analyze_colors(self, sample_photo_image, sample_graphic_image):
        """Test color analysis functionality"""
        # Test photo image (should have high complexity)
        color_analysis = _analyze_colors(sample_photo_image)
        
        required_keys = [
            "avg_color_range", "brightness", "unique_colors", "dominant_colors",
            "color_harmony", "is_monochrome", "is_high_contrast", "color_complexity"
        ]
        
        for key in required_keys:
            assert key in color_analysis
        
        assert isinstance(color_analysis["avg_color_range"], (int, float))
        assert isinstance(color_analysis["brightness"], (int, float))
        assert isinstance(color_analysis["unique_colors"], int)
        assert isinstance(color_analysis["dominant_colors"], list)
        assert color_analysis["color_complexity"] in ["low", "medium", "high"]
        
        # Check dominant colors structure with RGB and HEX values
        if color_analysis["dominant_colors"]:
            dominant_color = color_analysis["dominant_colors"][0]
            required_color_keys = ["rgb", "hex", "color", "count", "percentage"]
            
            for key in required_color_keys:
                assert key in dominant_color, f"Missing key '{key}' in dominant color"
            
            # Check RGB structure
            assert "r" in dominant_color["rgb"]
            assert "g" in dominant_color["rgb"]
            assert "b" in dominant_color["rgb"]
            
            # Check HEX format
            assert dominant_color["hex"].startswith("#")
            assert len(dominant_color["hex"]) == 7  # #RRGGBB format
            
            # Check percentage is reasonable
            assert 0 <= dominant_color["percentage"] <= 100
        
        # Test graphic image (should have lower complexity)
        graphic_analysis = _analyze_colors(sample_graphic_image)
        assert graphic_analysis["color_complexity"] in ["low", "medium"]
        assert graphic_analysis["unique_colors"] < color_analysis["unique_colors"]
    
    def test_analyze_complexity(self, sample_photo_image, sample_graphic_image):
        """Test complexity analysis"""
        # Test photo image
        photo_complexity = _analyze_complexity(sample_photo_image)
        
        required_keys = [
            "edge_density", "texture", "detail_level", 
            "is_photo_likely", "is_graphic_likely"
        ]
        
        for key in required_keys:
            assert key in photo_complexity
        
        assert photo_complexity["texture"] in ["smooth", "moderate", "detailed"]
        assert photo_complexity["detail_level"] in ["low", "medium", "high"]
        assert isinstance(photo_complexity["is_photo_likely"], bool)
        assert isinstance(photo_complexity["is_graphic_likely"], bool)
        
        # Test graphic image
        graphic_complexity = _analyze_complexity(sample_graphic_image)
        
        # Graphic should have lower edge density
        assert graphic_complexity["edge_density"] <= photo_complexity["edge_density"]
        assert graphic_complexity["is_graphic_likely"] or not graphic_complexity["is_photo_likely"]
    
    def test_analyze_color_harmony(self):
        """Test color harmony analysis"""
        # Test with complementary colors
        complementary_colors = [
            ((255, 0, 0), 100),    # Red
            ((0, 255, 255), 80),   # Cyan (complementary to red)
            ((128, 128, 128), 50)  # Gray
        ]
        
        harmony = _analyze_color_harmony(complementary_colors)
        
        assert "scheme" in harmony
        assert "harmony_score" in harmony
        assert "is_complementary" in harmony
        assert "is_analogous" in harmony
        
        assert harmony["scheme"] in ["monochromatic", "analogous", "complementary", "triadic", "neutral"]
        assert 0 <= harmony["harmony_score"] <= 100
        
        # Test with single color (monochromatic)
        mono_colors = [((255, 0, 0), 100)]
        mono_harmony = _analyze_color_harmony(mono_colors)
        assert mono_harmony["scheme"] == "monochromatic"
        assert mono_harmony["harmony_score"] == 100
    
    def test_get_format_recommendations(self, sample_photo_image, sample_transparent_image):
        """Test format recommendation system"""
        # Get basic info for photo
        photo_basic = _get_basic_info(sample_photo_image)
        photo_colors = _analyze_colors(sample_photo_image)
        photo_complexity = _analyze_complexity(sample_photo_image)
        
        recommendations = _get_format_recommendations(
            sample_photo_image, photo_basic, photo_colors, photo_complexity
        )
        
        assert "recommendations" in recommendations
        assert "best_format" in recommendations
        
        # Check all formats are present
        expected_formats = ["webp", "jpeg", "png", "avif"]
        for fmt in expected_formats:
            assert fmt in recommendations["recommendations"]
            
            rec = recommendations["recommendations"][fmt]
            assert "score" in rec
            assert "reasons" in rec
            assert 0 <= rec["score"] <= 100
            assert isinstance(rec["reasons"], list)
        
        # Best format should be in the recommendations
        assert recommendations["best_format"] in expected_formats
        
        # Test with transparent image
        transparent_basic = _get_basic_info(sample_transparent_image)
        transparent_colors = _analyze_colors(sample_transparent_image)
        transparent_complexity = _analyze_complexity(sample_transparent_image)
        
        transparent_recommendations = _get_format_recommendations(
            sample_transparent_image, transparent_basic, transparent_colors, transparent_complexity
        )
        
        # WebP or PNG should score higher for transparent images
        webp_score = transparent_recommendations["recommendations"]["webp"]["score"]
        png_score = transparent_recommendations["recommendations"]["png"]["score"]
        jpeg_score = transparent_recommendations["recommendations"]["jpeg"]["score"]
        
        assert max(webp_score, png_score) > jpeg_score
    
    def test_get_optimization_suggestions(self, sample_photo_image):
        """Test optimization suggestions"""
        # Create a very large image to trigger size suggestions
        large_image = sample_photo_image.resize((4000, 3000))
        
        basic_info = _get_basic_info(large_image)
        color_analysis = _analyze_colors(large_image)
        complexity_analysis = _analyze_complexity(large_image)
        
        suggestions = _get_optimization_suggestions(
            large_image, basic_info, color_analysis, complexity_analysis
        )
        
        assert "suggestions" in suggestions
        assert "total_suggestions" in suggestions
        assert "high_priority" in suggestions
        assert "optimization_potential" in suggestions
        
        assert isinstance(suggestions["suggestions"], list)
        assert suggestions["optimization_potential"] in ["low", "medium", "high"]
        
        # Large image should trigger resize suggestions
        resize_suggestions = [s for s in suggestions["suggestions"] if s["type"] == "resize"]
        assert len(resize_suggestions) > 0
        
        # Check suggestion structure
        if suggestions["suggestions"]:
            suggestion = suggestions["suggestions"][0]
            assert "type" in suggestion
            assert "priority" in suggestion
            assert "suggestion" in suggestion
            assert "details" in suggestion
            assert suggestion["priority"] in ["low", "medium", "high"]
    
    def test_calculate_web_metrics(self, sample_photo_image):
        """Test web performance metrics calculation"""
        basic_info = _get_basic_info(sample_photo_image)
        metrics = _calculate_web_metrics(sample_photo_image, basic_info)
        
        assert "estimated_sizes" in metrics
        assert "loading_times" in metrics
        assert "recommended_max_size" in metrics
        assert "performance_score" in metrics
        
        # Check estimated sizes structure
        sizes = metrics["estimated_sizes"]
        assert "jpeg" in sizes
        assert "webp" in sizes
        assert "png" in sizes
        assert "avif" in sizes
        
        # JPEG should have quality variants
        assert "quality_95" in sizes["jpeg"]
        assert "quality_85" in sizes["jpeg"]
        assert "quality_75" in sizes["jpeg"]
        assert "quality_65" in sizes["jpeg"]
        
        # WebP should be smaller than JPEG
        assert sizes["webp"]["quality_85"] <= sizes["jpeg"]["quality_85"]
        
        # Check loading times
        loading_times = metrics["loading_times"]
        for format_name in ["jpeg", "webp", "png", "avif"]:
            assert format_name in loading_times
            times = loading_times[format_name]
            assert "3g" in times
            assert "4g" in times
            assert "broadband" in times
            
            # Faster connections should have shorter loading times
            assert times["broadband"] <= times["4g"] <= times["3g"]
        
        # Performance score should be reasonable
        assert 0 <= metrics["performance_score"] <= 100
    
    def test_extract_detailed_metadata(self, sample_photo_image):
        """Test metadata extraction"""
        metadata = _extract_detailed_metadata(sample_photo_image)
        
        required_sections = ["basic", "exif", "camera_info", "location", "technical"]
        for section in required_sections:
            assert section in metadata
        
        basic = metadata["basic"]
        assert "format" in basic
        assert "mode" in basic
        assert "size" in basic
        assert "has_exif" in basic
        
        assert basic["mode"] == "RGB"
        assert basic["size"] == (800, 600)
        assert isinstance(basic["has_exif"], bool)
    
    def test_batch_analyze_images(self, sample_photo_image, sample_graphic_image):
        """Test batch analysis functionality"""
        # Create multiple FileStorage objects
        files = []
        
        # Add photo image
        buffer1 = io.BytesIO()
        sample_photo_image.save(buffer1, format="PNG")
        buffer1.seek(0)
        files.append(FileStorage(
            stream=buffer1,
            filename="photo.png",
            content_type="image/png"
        ))
        
        # Add graphic image
        buffer2 = io.BytesIO()
        sample_graphic_image.save(buffer2, format="PNG")
        buffer2.seek(0)
        files.append(FileStorage(
            stream=buffer2,
            filename="graphic.png",
            content_type="image/png"
        ))
        
        results, errors, batch_insights = batch_analyze_images(files)
        
        # Check results
        assert len(results) == 2
        assert len(errors) == 0
        
        # Check batch insights structure
        assert "summary" in batch_insights
        assert "format_distribution" in batch_insights
        assert "complexity_distribution" in batch_insights
        assert "recommended_formats" in batch_insights
        assert "insights" in batch_insights
        
        summary = batch_insights["summary"]
        assert summary["total_files"] == 2
        assert summary["total_megapixels"] > 0
        assert summary["avg_megapixels"] > 0
        assert 0 <= summary["optimization_percentage"] <= 100
        
        # Check insights are actionable
        insights = batch_insights["insights"]
        assert isinstance(insights, list)
        
        for insight in insights:
            assert "type" in insight
            assert "message" in insight
            assert "action" in insight
    
    def test_generate_batch_insights(self):
        """Test batch insights generation"""
        # Mock analysis results
        mock_analyses = [
            {
                "basic_info": {
                    "total_pixels": 2000000,
                    "megapixels": 2.0,
                    "format": "JPEG",
                    "has_transparency": False
                },
                "complexity_analysis": {
                    "detail_level": "high",
                    "is_photo_likely": True,
                    "is_graphic_likely": False
                },
                "format_recommendations": {
                    "best_format": "webp"
                },
                "optimization_suggestions": {
                    "optimization_potential": "high"
                }
            },
            {
                "basic_info": {
                    "total_pixels": 500000,
                    "megapixels": 0.5,
                    "format": "PNG",
                    "has_transparency": True
                },
                "complexity_analysis": {
                    "detail_level": "low",
                    "is_photo_likely": False,
                    "is_graphic_likely": True
                },
                "format_recommendations": {
                    "best_format": "png"
                },
                "optimization_suggestions": {
                    "optimization_potential": "medium"
                }
            }
        ]
        
        insights = _generate_batch_insights(mock_analyses)
        
        assert "summary" in insights
        assert "format_distribution" in insights
        assert "complexity_distribution" in insights
        assert "recommended_formats" in insights
        assert "insights" in insights
        
        summary = insights["summary"]
        assert summary["total_files"] == 2
        assert summary["needs_optimization"] == 1  # One high potential
        assert summary["optimization_percentage"] == 50.0
        
        # Check format distribution
        format_dist = insights["format_distribution"]
        assert "JPEG" in format_dist
        assert "PNG" in format_dist
        
        # Check complexity distribution
        complexity_dist = insights["complexity_distribution"]
        assert "high" in complexity_dist
        assert "low" in complexity_dist
    
    def test_error_handling_in_batch_analysis(self):
        """Test error handling in batch analysis"""
        # Create a mock file that will cause an error
        buffer = io.BytesIO(b"invalid image data")
        invalid_file = FileStorage(
            stream=buffer,
            filename="invalid.png",
            content_type="image/png"
        )
        
        results, errors, batch_insights = batch_analyze_images([invalid_file])
        
        assert len(results) == 0
        assert len(errors) == 1
        assert errors[0]["filename"] == "invalid.png"
        assert "error" in errors[0]
        
        # Batch insights should be empty when no results
        assert batch_insights == {}


if __name__ == "__main__":
    pytest.main([__file__])

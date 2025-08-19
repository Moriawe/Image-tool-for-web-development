"""
Unit tests for SVG Toolkit functionality
"""
import unittest
import tempfile
from pathlib import Path
from image_processing.svg_toolkit import (
    validate_svg,
    optimize_svg,
    analyze_svg_complexity,
    generate_color_variants,
    generate_svg_report
)


class TestSVGToolkit(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Simple test SVG
        self.simple_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="#0ea5e9" stroke="#000" stroke-width="2"/>
  <title>Test Circle</title>
</svg>'''
        
        # Complex SVG with metadata (simplified)
        self.complex_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <defs>
    <linearGradient id="grad1">
      <stop offset="0%" stop-color="#ff0000"/>
      <stop offset="100%" stop-color="#00ff00"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="40.12345678" fill="url(#grad1)"/>
  <path d="M10,10 L90,90 L10,90 Z"/>
</svg>'''
    
    def test_validate_svg_simple(self):
        """Test SVG validation with simple valid SVG"""
        result = validate_svg(self.simple_svg)
        
        self.assertTrue(result["valid"])
        self.assertTrue(result["has_viewbox"])
        self.assertTrue(result["has_dimensions"])
        self.assertGreater(result["elements_count"], 0)
    
    def test_validate_svg_complex(self):
        """Test SVG validation with complex SVG"""
        result = validate_svg(self.complex_svg)
        
        # Should be valid XML but may have optimization issues
        self.assertTrue(isinstance(result["valid"], bool))
        self.assertTrue(result["has_viewbox"])
        self.assertGreater(result["elements_count"], 3)
    
    def test_optimize_svg_basic(self):
        """Test basic SVG optimization"""
        result = optimize_svg(self.complex_svg, aggressive=False)
        
        self.assertIn("optimized_svg", result)
        self.assertIn("compression_ratio", result)
        self.assertLess(result["optimized_size"], result["original_size"])
        
        # Check that metadata was removed
        optimized = result["optimized_svg"]
        self.assertNotIn("metadata", optimized)
        self.assertNotIn("inkscape:", optimized)
    
    def test_optimize_svg_aggressive(self):
        """Test aggressive SVG optimization"""
        result = optimize_svg(self.complex_svg, aggressive=True)
        
        self.assertIn("optimized_svg", result)
        self.assertGreater(result["compression_ratio"], 0)
        
        # Aggressive optimization should reduce precision
        optimized = result["optimized_svg"]
        self.assertNotIn("40.12345678", optimized)  # High precision should be reduced
    
    def test_analyze_svg_complexity(self):
        """Test SVG complexity analysis"""
        result = analyze_svg_complexity(self.complex_svg)
        
        self.assertIn("total_elements", result)
        self.assertIn("complexity_score", result)
        self.assertIn("performance_issues", result)
        self.assertIsInstance(result["complexity_score"], (int, float))
        self.assertGreater(result["total_elements"], 0)
    
    def test_generate_color_variants(self):
        """Test color variant generation"""
        color_schemes = {
            "dark": {"#0ea5e9": "#1f2937", "#000": "#fff"},
            "red": {"#0ea5e9": "#ef4444"}
        }
        
        variants = generate_color_variants(self.simple_svg, color_schemes)
        
        self.assertIn("dark", variants)
        self.assertIn("red", variants)
        self.assertIn("#1f2937", variants["dark"])
        self.assertIn("#ef4444", variants["red"])
    
    def test_generate_svg_report(self):
        """Test comprehensive SVG report generation"""
        report = generate_svg_report(self.complex_svg, "test.svg")
        
        self.assertIn("filename", report)
        self.assertIn("validation", report)
        self.assertIn("optimization", report)
        self.assertIn("complexity", report)
        self.assertIn("mobile_compatibility", report)
        self.assertIn("recommendations", report)
        
        self.assertEqual(report["filename"], "test.svg")
        self.assertIsInstance(report["recommendations"], list)
    
    def test_invalid_svg(self):
        """Test handling of invalid SVG"""
        invalid_svg = "<not-valid-xml>"
        
        validation = validate_svg(invalid_svg)
        complexity = analyze_svg_complexity(invalid_svg)
        
        self.assertFalse(validation["valid"])
        self.assertIn("error", complexity)
    
    def test_svg_mobile_compatibility(self):
        """Test mobile compatibility assessment"""
        report = generate_svg_report(self.simple_svg, "simple.svg")
        mobile_compat = report["mobile_compatibility"]
        
        self.assertIn("compatible", mobile_compat)
        self.assertIn("issues", mobile_compat)
        self.assertIsInstance(mobile_compat["compatible"], bool)
        self.assertIsInstance(mobile_compat["issues"], list)


if __name__ == '__main__':
    unittest.main()

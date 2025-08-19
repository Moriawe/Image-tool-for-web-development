from image_processing.svg_toolkit import validate_svg, analyze_svg_complexity

# Simple SVG
simple_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="#0ea5e9"/>
</svg>'''

# Complex SVG (simplified)
complex_svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" width="100" height="100">
  <circle cx="50" cy="50" r="40" fill="#0ea5e9"/>
</svg>'''

print("=== Simple SVG ===")
result1 = validate_svg(simple_svg)
print("Validation:", result1)

print("\n=== Analyze complexity ===")
result2 = analyze_svg_complexity(simple_svg)
print("Complexity:", result2)

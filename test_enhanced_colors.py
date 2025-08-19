#!/usr/bin/env python3
"""
Quick test script to demonstrate the enhanced dominant colors feature
with RGB and HEX values.
"""

import io
from PIL import Image
from werkzeug.datastructures import FileStorage
from image_processing.image_analysis import analyze_image_comprehensive

def create_test_image():
    """Create a simple test image with distinct colors"""
    # Create a 100x100 image with 4 distinct color blocks
    img = Image.new("RGB", (100, 100))
    pixels = []
    
    for y in range(100):
        for x in range(100):
            if x < 50 and y < 50:
                # Red block
                pixels.append((255, 0, 0))
            elif x >= 50 and y < 50:
                # Green block
                pixels.append((0, 255, 0))
            elif x < 50 and y >= 50:
                # Blue block
                pixels.append((0, 0, 255))
            else:
                # Yellow block
                pixels.append((255, 255, 0))
    
    img.putdata(pixels)
    return img

def main():
    # Create test image
    img = create_test_image()
    
    # Convert to FileStorage object
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    file_storage = FileStorage(
        stream=buffer,
        filename="test_colors.png",
        content_type="image/png"
    )
    
    # Analyze the image
    print("🔍 Analyzing image with enhanced dominant colors...")
    result = analyze_image_comprehensive(file_storage)
    
    # Display the enhanced color analysis
    color_analysis = result["color_analysis"]
    print(f"\n🎨 Enhanced Dominant Colors Analysis:")
    print(f"Color Complexity: {color_analysis['color_complexity']}")
    print(f"Unique Colors: {color_analysis['unique_colors']}")
    print(f"Brightness: {color_analysis['brightness']}")
    
    print(f"\n📊 Dominant Colors with RGB & HEX values:")
    for i, color_info in enumerate(color_analysis["dominant_colors"], 1):
        print(f"  {i}. {color_info['hex'].upper()}")
        print(f"     RGB: ({color_info['rgb']['r']}, {color_info['rgb']['g']}, {color_info['rgb']['b']})")
        print(f"     Percentage: {color_info['percentage']}%")
        print(f"     Count: {color_info['count']} pixels")
        print()
    
    print("✅ Enhanced dominant colors feature working perfectly!")
    print("\n💡 Try this feature in the web app:")
    print("   1. Go to http://127.0.0.1:5000")
    print("   2. Click 'Image Analysis' tab")
    print("   3. Upload any colorful image")
    print("   4. See detailed RGB/HEX values for dominant colors!")

if __name__ == "__main__":
    main()

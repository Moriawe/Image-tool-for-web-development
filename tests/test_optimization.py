from image_processing.optimization_suite import OPTIMIZATION_PRESETS

print("🚀 Optimization Suite - Available Presets:")
print("=" * 50)

for key, preset in OPTIMIZATION_PRESETS.items():
    print(f"• {preset['name']}")
    print(f"  Description: {preset['description']}")
    print(f"  Max Size: {preset['max_width']}×{preset['max_height']}px")
    print(f"  Quality: {preset['quality']}%")
    print(f"  Strip Metadata: {'Yes' if preset['strip_metadata'] else 'No'}")
    print()

print("✅ Optimization suite successfully loaded!")

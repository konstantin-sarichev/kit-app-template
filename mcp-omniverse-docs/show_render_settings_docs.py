"""Display render settings documentation overview."""

import asyncio
import sys
import io
from src.server import call_tool

# Fix unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


async def show_render_settings_overview():
    """Show comprehensive render settings documentation."""
    
    print("\n" + "=" * 80)
    print("OMNIVERSE RENDER SETTINGS - COMPREHENSIVE OVERVIEW")
    print("=" * 80 + "\n")
    
    # Part 1: Settings system guide
    print("PART 1: SETTINGS SYSTEM (How to Access Render Settings)")
    print("-" * 80 + "\n")
    
    args = {"topic": "settings"}
    results = await call_tool("get_extension_guide", args)
    
    if results:
        print(results[0].text)
    
    # Part 2: Render settings specifics
    print("\n\n" + "=" * 80)
    print("PART 2: RENDER SETTINGS SPECIFICS")
    print("=" * 80 + "\n")
    
    render_settings_doc = """
# Omniverse RTX Render Settings

## Overview

Omniverse uses the NVIDIA RTX renderer for physically accurate, real-time ray tracing. 
Render settings are configured through the Carb settings system and can be accessed 
programmatically or through the UI.

## Key Render Settings Categories

### 1. Path Tracing Settings (/rtx/pathtracing/*)

Controls the path tracing algorithm for high-quality rendering:

```python
import carb.settings

settings = carb.settings.get_settings()

# Samples per pixel (quality vs performance)
settings.set("/rtx/pathtracing/spp", 256)  # Higher = better quality, slower

# Maximum ray bounces (affects global illumination)
settings.set("/rtx/pathtracing/maxBounces", 32)  # Higher = more accurate lighting

# Specular and transmission bounces
settings.set("/rtx/pathtracing/maxSpecularAndTransmissionBounces", 6)

# Subsurface scattering depth
settings.set("/rtx/pathtracing/maxSSSBounces", 15)

# Target error for adaptive sampling
settings.set("/rtx/pathtracing/targetError", 0.001)  # Lower = better quality
```

### 2. Render Mode Settings (/rtx/*)

```python
# Rendering mode
settings.set("/rtx/rendermode", "PathTracing")  # Options: PathTracing, RayTracedLighting

# Enable/disable features
settings.set("/rtx/ecoMode/enabled", False)  # Disable eco mode for consistent rendering
settings.set("/rtx/translucency/enabled", True)
settings.set("/rtx/reflections/enabled", True)
settings.set("/rtx/shadows/enabled", True)
```

### 3. Resolution Settings (/app/renderer/*)

```python
# Output resolution
settings.set("/app/renderer/resolution/width", 1920)
settings.set("/app/renderer/resolution/height", 1080)

# Skip rendering while minimized
settings.set("/app/renderer/skipWhileMinimized", True)
```

### 4. Post-Processing Settings

```python
# Anti-aliasing
settings.set("/rtx/post/aa/op", 2)  # DLSS, TAA, FXAA

# Tone mapping
settings.set("/rtx/post/tonemap/op", 2)  # Filmic, ACES, etc.

# Denoising
settings.set("/rtx/post/dlss/enabled", True)
```

## Vision Digital Twin Specific Settings

For synthetic data generation and physically accurate rendering:

### Synthetic Data Render Settings

Based on your project's `synthetic_out/` directory, here are optimal settings:

```python
import carb.settings

def configure_synthetic_data_rendering():
    '''Configure render settings for synthetic data generation.'''
    settings = carb.settings.get_settings()
    
    # High quality path tracing
    settings.set("/rtx/pathtracing/spp", 512)  # Tested: 512 samples
    settings.set("/rtx/pathtracing/maxBounces", 32)  # Tested: 4, 32, 64
    settings.set("/rtx/pathtracing/maxSpecularAndTransmissionBounces", 6)
    settings.set("/rtx/pathtracing/maxSSSBounces", 15)  # Tested: 15, 63
    settings.set("/rtx/pathtracing/targetError", 0.001)  # Tested
    
    # Ensure consistent rendering
    settings.set("/rtx/ecoMode/enabled", False)
    settings.set("/rtx/hydra/readTransformsFromFabricInRenderDelegate", False)
    
    # Material distilling for accuracy
    settings.set("/persistent/rtx/mdltranslator/distillMaterial", True)
    
    return True
```

### Reading Current Settings

```python
def get_current_render_settings():
    '''Read current render settings.'''
    settings = carb.settings.get_settings()
    
    current_settings = {
        "spp": settings.get("/rtx/pathtracing/spp"),
        "maxBounces": settings.get("/rtx/pathtracing/maxBounces"),
        "targetError": settings.get("/rtx/pathtracing/targetError"),
        "renderMode": settings.get("/rtx/rendermode"),
        "ecoMode": settings.get("/rtx/ecoMode/enabled"),
        "resolution": {
            "width": settings.get("/app/renderer/resolution/width"),
            "height": settings.get("/app/renderer/resolution/height"),
        }
    }
    
    return current_settings
```

## Project-Specific Settings

Your `my_company.my_usd_composer.kit` file (lines 351-363) contains:

```toml
[settings.rtx]
ecoMode.enabled = true
hydra.readTransformsFromFabricInRenderDelegate = false

[settings]
renderer.active = "rtx"  # RTX as the default renderer always
renderer.enabled = "rtx"
```

These are the base settings. For bootstrap capabilities, you may want to:

1. **Set defaults for synthetic data generation**
2. **Enforce consistent render settings across scenes**
3. **Validate render settings match requirements**
4. **Log render settings used for each capture**

## Common Render Setting Paths Reference

| Setting Path | Type | Description |
|--------------|------|-------------|
| /rtx/rendermode | string | Render mode (PathTracing, RayTracedLighting) |
| /rtx/pathtracing/spp | int | Samples per pixel |
| /rtx/pathtracing/maxBounces | int | Maximum ray bounces |
| /rtx/pathtracing/targetError | float | Adaptive sampling target error |
| /rtx/ecoMode/enabled | bool | Enable eco mode (power saving) |
| /rtx/post/dlss/enabled | bool | Enable DLSS denoising |
| /app/renderer/resolution/width | int | Output width in pixels |
| /app/renderer/resolution/height | int | Output height in pixels |

## Best Practices for Vision Digital Twin

1. **Disable Eco Mode**: Ensures consistent frame times
   ```python
   settings.set("/rtx/ecoMode/enabled", False)
   ```

2. **Set Fixed Sample Count**: For reproducible results
   ```python
   settings.set("/rtx/pathtracing/spp", 512)
   ```

3. **Configure Before Capture**: Set render settings before synthetic data capture
   ```python
   def prepare_for_capture():
       configure_synthetic_data_rendering()
       # Wait for settings to take effect
       await omni.kit.app.get_app().next_update_async()
   ```

4. **Log Settings**: Record settings used for each capture session
   ```python
   import json
   
   def save_render_settings(filepath):
       settings_dict = get_current_render_settings()
       with open(filepath, 'w') as f:
           json.dump(settings_dict, f, indent=2)
   ```

## Bootstrap Capability Ideas

Consider creating these capabilities for render settings:

1. **`40_configure_render_settings.py`**
   - Set default render settings for synthetic data
   - Enforce physical accuracy requirements
   - Validate settings on stage open

2. **`45_validate_render_config.py`**
   - Check render settings match project requirements
   - Warn if eco mode is enabled
   - Verify sample counts are sufficient

3. **`50_render_logging.py`**
   - Log render settings at capture time
   - Associate settings with output files
   - Track render configuration history

## Additional Resources

For more details, see:
- Omniverse RTX Renderer Documentation
- Kit SDK Settings System
- Replicator Extension (for synthetic data)
- Your project kit file: `source/apps/my_company.my_usd_composer.kit`

## Summary

- **Access settings via**: `carb.settings.get_settings()`
- **Key paths**: `/rtx/pathtracing/*` and `/app/renderer/*`
- **Your project uses**: RTX renderer with configurable quality
- **For synthetic data**: Use high sample counts, disable eco mode
- **Bootstrap integration**: Create capabilities to enforce and validate settings
"""
    
    print(render_settings_doc)
    
    print("\n" + "=" * 80)
    print("DOCUMENTATION COMPLETE")
    print("=" * 80 + "\n")


async def main():
    """Main entry point."""
    try:
        await show_render_settings_overview()
        print("\nRender settings documentation displayed successfully!")
        print("\nNext steps:")
        print("  1. Use these patterns in bootstrap development")
        print("  2. Create render settings capabilities")
        print("  3. Integrate with synthetic data capture workflow")
        print()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())


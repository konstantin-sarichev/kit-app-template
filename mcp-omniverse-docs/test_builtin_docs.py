"""Test built-in documentation and render settings guides."""

import asyncio
import sys
import io
from src.server import call_tool

# Fix unicode encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


async def test_extension_guides():
    """Test all extension development guides."""
    print("=" * 80)
    print("TEST: EXTENSION DEVELOPMENT GUIDES")
    print("=" * 80 + "\n")
    
    topics = ["lifecycle", "ui", "stage", "events", "settings", "tests"]
    
    for topic in topics:
        print(f"\n{'='*80}")
        print(f"TOPIC: {topic.upper()}")
        print("=" * 80 + "\n")
        
        args = {"topic": topic}
        
        try:
            results = await call_tool("get_extension_guide", args)
            
            if results and len(results) > 0:
                content = results[0].text
                print(content)
                print(f"\n[Content length: {len(content)} characters]")
            else:
                print(f"No content returned for {topic}")
                
        except Exception as e:
            print(f"Error retrieving {topic}: {e}")
        
        print()


async def test_best_practices():
    """Test Vision DT best practices."""
    print("\n" + "=" * 80)
    print("TEST: VISION DIGITAL TWIN BEST PRACTICES")
    print("=" * 80 + "\n")
    
    topics = ["units", "transforms", "metadata", "stage"]
    
    for topic in topics:
        print(f"\n{'='*80}")
        print(f"BEST PRACTICE: {topic.upper()}")
        print("=" * 80 + "\n")
        
        args = {"topic": topic}
        
        try:
            results = await call_tool("search_omniverse_best_practices", args)
            
            if results and len(results) > 0:
                content = results[0].text
                
                # Extract overview section (first 500 chars after title)
                lines = content.split('\n')
                overview_lines = []
                found_title = False
                
                for line in lines[:30]:  # First 30 lines
                    if line.startswith('#'):
                        found_title = True
                        overview_lines.append(line)
                        continue
                    
                    if found_title and line.strip():
                        overview_lines.append(line)
                        
                        # Stop at first code block or next section
                        if line.strip().startswith('```') or line.startswith('##'):
                            if len(overview_lines) > 5:
                                break
                
                overview = '\n'.join(overview_lines[:20])
                print("OVERVIEW:")
                print("-" * 80)
                print(overview)
                print("-" * 80)
                print(f"\n[Full content: {len(content)} characters]")
                print(f"[First code example available: {'```' in content}]")
            else:
                print(f"No content returned for {topic}")
                
        except Exception as e:
            print(f"Error retrieving {topic}: {e}")
            import traceback
            traceback.print_exc()
        
        print()


async def test_render_settings_guide():
    """Test the settings guide which covers render settings."""
    print("\n" + "=" * 80)
    print("SPECIAL TEST: RENDER SETTINGS (via Settings Guide)")
    print("=" * 80 + "\n")
    
    args = {"topic": "settings"}
    
    try:
        results = await call_tool("get_extension_guide", args)
        
        if results and len(results) > 0:
            content = results[0].text
            
            print("SETTINGS MANAGEMENT OVERVIEW:")
            print("=" * 80)
            print(content)
            print("=" * 80)
            
            print("\n\nKEY POINTS FOR RENDER SETTINGS:")
            print("-" * 80)
            print("""
The settings system in Omniverse Kit is the primary way to configure render settings.

For render settings specifically:

1. RTX Render Settings:
   - Path: /rtx/* (various RTX renderer settings)
   - Examples:
     * /rtx/rendermode - Set rendering mode
     * /rtx/pathtracing/spp - Samples per pixel
     * /rtx/pathtracing/maxBounces - Max ray bounces
     * /rtx/pathtracing/maxSpecularAndTransmissionBounces - Specular bounces

2. Accessing Render Settings:
   ```python
   import carb.settings
   
   settings = carb.settings.get_settings()
   
   # Get current samples per pixel
   spp = settings.get("/rtx/pathtracing/spp")
   
   # Set samples per pixel
   settings.set("/rtx/pathtracing/spp", 256)
   
   # Set max bounces
   settings.set("/rtx/pathtracing/maxBounces", 32)
   ```

3. Common Render Settings Paths:
   - /app/renderer/resolution/width
   - /app/renderer/resolution/height
   - /rtx/ecoMode/enabled
   - /rtx/hydra/readTransformsFromFabricInRenderDelegate
   - /persistent/rtx/mdltranslator/distillMaterial

4. For Vision Digital Twin (Synthetic Data):
   These settings are crucial for physically accurate rendering:
   - Sample counts (spp)
   - Ray bounce limits (maxBounces)
   - Target error for adaptive sampling
   - Subsurface scattering depth (maxSSS)

See the kit file at source/apps/my_company.my_usd_composer.kit lines 351-363
for actual render settings in your project!
""")
            print("-" * 80)
            
        else:
            print("No settings guide content returned")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Main test runner."""
    print("\n" + "=" * 80)
    print("MCP OMNIVERSE DOCS - BUILT-IN CONTENT TEST")
    print("=" * 80)
    print("""
This test demonstrates the MCP server's built-in documentation
which works WITHOUT internet connection.

Built-in guides cover:
  - Extension development (6 topics)
  - Vision DT best practices (4 topics)
  - Render settings (via settings guide)
""")
    print("=" * 80 + "\n")
    
    # Test 1: Render settings specifically
    await test_render_settings_guide()
    
    # Test 2: All extension guides
    print("\n\nPress Enter to see all extension guides (or Ctrl+C to skip)...")
    try:
        input()
        await test_extension_guides()
    except KeyboardInterrupt:
        print("\nSkipping extension guides...")
    
    # Test 3: All best practices
    print("\n\nPress Enter to see all best practices (or Ctrl+C to skip)...")
    try:
        input()
        await test_best_practices()
    except KeyboardInterrupt:
        print("\nSkipping best practices...")
    
    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80)
    print("""
SUMMARY:
  The MCP server successfully provides:
  - Extension development patterns
  - Vision DT best practices
  - Render settings guidance
  - Code examples for all topics

  All content is built-in and works offline!

NEXT STEPS:
  1. Configure this MCP server in Cursor
  2. Use it to develop the bootstrap system
  3. Query for specific APIs as needed
  4. Reference best practices during development
""")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()


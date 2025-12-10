"""
Manual Bootstrap Test Script

Run this in the Omniverse Script Editor to manually test the bootstrap system
and diagnose why it's not adding attributes to lights automatically.

Instructions:
1. Open Omniverse USD Composer
2. Open Window > Script Editor
3. Copy and paste this entire script
4. Click "Run" button
5. Check the console output for detailed diagnostics
"""

import sys
from pathlib import Path
import logging

# Setup logging to see detailed output
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bootstrap_test")

print("="*80)
print("BOOTSTRAP DIAGNOSTIC TEST")
print("="*80)

# Step 1: Check if bootstrap directory exists
print("\n1. CHECKING BOOTSTRAP DIRECTORY...")
bootstrap_path = Path("G:/Vision_Example_1/kit-app-template/bootstrap")
print(f"   Bootstrap path: {bootstrap_path}")
print(f"   Exists: {bootstrap_path.exists()}")

if not bootstrap_path.exists():
    print("   ❌ ERROR: Bootstrap directory not found!")
    print("   Please verify the path is correct.")
    sys.exit(1)

# Step 2: Add bootstrap to path
print("\n2. ADDING BOOTSTRAP TO PYTHON PATH...")
if str(bootstrap_path) not in sys.path:
    sys.path.insert(0, str(bootstrap_path))
    print(f"   ✓ Added to sys.path")
else:
    print(f"   ✓ Already in sys.path")

# Step 3: Try to import bootstrap loader
print("\n3. IMPORTING BOOTSTRAP LOADER...")
try:
    from loader import BootstrapLoader
    print("   ✓ Successfully imported BootstrapLoader")
except ImportError as e:
    print(f"   ❌ ERROR: Failed to import BootstrapLoader: {e}")
    sys.exit(1)

# Step 4: Check capabilities directory
print("\n4. CHECKING CAPABILITIES...")
capabilities_dir = bootstrap_path / "capabilities"
print(f"   Capabilities dir: {capabilities_dir}")
print(f"   Exists: {capabilities_dir.exists()}")

if capabilities_dir.exists():
    cap_files = list(capabilities_dir.glob("*.py"))
    cap_files = [f for f in cap_files if f.name != "__init__.py" and not f.name.startswith("_")]
    cap_files.sort()
    
    print(f"\n   Found {len(cap_files)} active capabilities:")
    for cap in cap_files:
        print(f"      - {cap.name}")
else:
    print("   ❌ ERROR: Capabilities directory not found!")
    sys.exit(1)

# Step 5: Get current stage
print("\n5. CHECKING CURRENT STAGE...")
try:
    import omni.usd
    context = omni.usd.get_context()
    stage = context.get_stage() if context else None
    
    if stage:
        print(f"   ✓ Stage available: {stage.GetRootLayer().identifier}")
        
        # Check for lights
        print("\n   Checking for lights in stage...")
        light_count = 0
        light_types = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]
        
        for prim in stage.Traverse():
            if prim.GetTypeName() in light_types:
                light_count += 1
                print(f"      Found: {prim.GetPath()} (type: {prim.GetTypeName()})")
                
                # Check if it already has multi-spectrum attributes
                has_red = prim.HasAttribute("vision:brightnessRed")
                has_green = prim.HasAttribute("vision:brightnessGreen")
                has_blue = prim.HasAttribute("vision:brightnessBlue")
                
                if has_red and has_green and has_blue:
                    print(f"         ✓ Already has multi-spectrum attributes")
                else:
                    print(f"         ⚠ Missing multi-spectrum attributes (R:{has_red}, G:{has_green}, B:{has_blue})")
        
        if light_count == 0:
            print("      ⚠ No lights found in stage")
            print("      TIP: Create a light (Create > Light > Rect Light) before running bootstrap")
    else:
        print("   ❌ ERROR: No stage available!")
        print("   Please open or create a stage first.")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ ERROR: Failed to get stage: {e}")
    sys.exit(1)

# Step 6: Run bootstrap manually
print("\n6. RUNNING BOOTSTRAP MANUALLY...")
print("   (This may take a few seconds...)")
print()

try:
    loader = BootstrapLoader(capabilities_dir)
    results = loader.run_all_capabilities(stage)
    
    print("\n   BOOTSTRAP RESULTS:")
    print(f"      Total capabilities: {results['total']}")
    print(f"      Successful: {results['successful']}")
    print(f"      Failed: {results['failed']}")
    
    print("\n   Detailed results:")
    for name, success, message in results['capabilities']:
        status = "✓" if success else "✗"
        print(f"      {status} {name}: {message}")
    
except Exception as e:
    print(f"   ❌ ERROR: Bootstrap execution failed: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

# Step 7: Verify lights now have attributes
print("\n7. VERIFYING LIGHT ATTRIBUTES AFTER BOOTSTRAP...")
if light_count > 0:
    for prim in stage.Traverse():
        if prim.GetTypeName() in light_types:
            has_red = prim.HasAttribute("vision:brightnessRed")
            has_green = prim.HasAttribute("vision:brightnessGreen")
            has_blue = prim.HasAttribute("vision:brightnessBlue")
            
            print(f"\n   Light: {prim.GetPath()}")
            print(f"      vision:brightnessRed: {has_red}")
            print(f"      vision:brightnessGreen: {has_green}")
            print(f"      vision:brightnessBlue: {has_blue}")
            
            if has_red and has_green and has_blue:
                # Show actual values
                red_val = prim.GetAttribute("vision:brightnessRed").Get()
                green_val = prim.GetAttribute("vision:brightnessGreen").Get()
                blue_val = prim.GetAttribute("vision:brightnessBlue").Get()
                print(f"      Values: R={red_val}, G={green_val}, B={blue_val}")
                print(f"      ✓ Successfully configured!")
            else:
                print(f"      ❌ FAILED: Attributes not added")

# Step 8: Final summary
print("\n" + "="*80)
print("DIAGNOSTIC COMPLETE")
print("="*80)

if results['successful'] == results['total'] and light_count > 0:
    print("\n✓ SUCCESS: Bootstrap is working correctly!")
    print("\nNext steps:")
    print("1. Select a light in your stage")
    print("2. Open the Properties panel (Window > Properties)")
    print("3. Scroll down to find vision:brightnessRed/Green/Blue attributes")
    print("4. Edit the values to control multi-spectrum brightness")
else:
    print("\n⚠ ISSUES DETECTED:")
    if results['failed'] > 0:
        print(f"   - {results['failed']} capabilities failed")
    if light_count == 0:
        print("   - No lights in stage to configure")
    print("\nRecommendations:")
    print("1. Check the console output above for specific error messages")
    print("2. Make sure you have lights in your stage")
    print("3. Try closing and reopening the stage")
    print("4. Verify bootstrap integration with your extension")

print("\n" + "="*80)


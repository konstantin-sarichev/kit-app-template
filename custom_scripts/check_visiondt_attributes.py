"""
Vision DT Attribute Diagnostic Script
Run this in Omniverse's Script Editor (Window > Script Editor) to check if custom attributes exist.
"""

import omni.usd
from pxr import Usd, UsdLux

def check_visiondt_attributes():
    """Check all lights for visiondt: custom attributes."""

    print("\n" + "="*60)
    print("VISION DT ATTRIBUTE DIAGNOSTIC")
    print("="*60 + "\n")

    # Get current stage
    context = omni.usd.get_context()
    stage = context.get_stage()

    if not stage:
        print("ERROR: No stage is open!")
        return

    print(f"Stage: {stage.GetRootLayer().identifier}\n")

    # Find all lights
    light_types = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]

    lights_found = []
    for prim in stage.Traverse():
        if prim.GetTypeName() in light_types:
            lights_found.append(prim)

    if not lights_found:
        print("WARNING: No lights found in the stage!")
        return

    print(f"Found {len(lights_found)} light(s):\n")

    # Check each light for visiondt attributes
    visiondt_attrs = [
        "visiondt:overallTemperature",
        "visiondt:redTemperature",
        "visiondt:greenTemperature",
        "visiondt:blueTemperature",
        "visiondt:iesProfile"
    ]

    # Also check old naming convention (to see if old attributes exist)
    old_attrs = [
        "inputs:visiondt:overallTemperature",
        "inputs:visiondt:redTemperature",
        "inputs:visiondt:greenTemperature",
        "inputs:visiondt:blueTemperature",
        "inputs:visiondt:iesProfile"
    ]

    for light in lights_found:
        print(f"Light: {light.GetPath()}")
        print(f"  Type: {light.GetTypeName()}")
        print("-" * 40)

        # Check new visiondt: attributes
        print("  NEW attributes (visiondt:):")
        has_new = False
        for attr_name in visiondt_attrs:
            attr = light.GetAttribute(attr_name)
            if attr and attr.IsValid():
                value = attr.Get()
                has_new = True
                print(f"    ✓ {attr_name} = {value}")
            else:
                print(f"    ✗ {attr_name} (NOT FOUND)")

        # Check old inputs:visiondt: attributes
        print("  OLD attributes (inputs:visiondt:):")
        has_old = False
        for attr_name in old_attrs:
            attr = light.GetAttribute(attr_name)
            if attr and attr.IsValid():
                value = attr.Get()
                has_old = True
                print(f"    ⚠ {attr_name} = {value} (OLD FORMAT)")

        if not has_old:
            print("    (none found)")

        # List ALL custom attributes on the prim
        print("  ALL attributes on this prim:")
        all_attrs = light.GetAttributes()
        custom_count = 0
        for attr in all_attrs:
            attr_name = attr.GetName()
            # Show visiondt attributes and any other custom ones (not standard USD)
            if "visiondt" in attr_name.lower() or (attr.IsCustom() and not attr_name.startswith("xformOp")):
                print(f"    → {attr_name} = {attr.Get()}")
                custom_count += 1

        if custom_count == 0:
            print("    (no custom visiondt attributes)")

        print()

    print("="*60)
    print("DIAGNOSTIC COMPLETE")
    print("="*60)
    print("\nIf no visiondt: attributes are found, the bootstrap may not")
    print("be running, or there's an error in the capability code.")
    print("\nTo manually add an attribute for testing, run:")
    print('  prim.CreateAttribute("visiondt:test", Sdf.ValueTypeNames.Float, custom=True)')

# Run the diagnostic
check_visiondt_attributes()

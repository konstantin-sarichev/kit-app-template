"""
Apply Vision DT attributes to ALL lights in the current stage.
Run this in Omniverse Script Editor to add attributes to lights
that were created before the bootstrap ran.
"""

import omni.usd
from pxr import Usd, Sdf

# Configuration
DEFAULT_TEMPERATURE = 6500.0
LIGHT_TYPES = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]

def apply_visiondt_to_light(light_prim):
    """Apply Vision DT attributes to a single light prim."""
    prim_path = str(light_prim.GetPath())

    # Temperature attributes
    attrs = [
        ("visiondt:overallTemperature", "Overall Temperature (K)", DEFAULT_TEMPERATURE),
        ("visiondt:redTemperature", "Red Temperature (K)", DEFAULT_TEMPERATURE),
        ("visiondt:greenTemperature", "Green Temperature (K)", DEFAULT_TEMPERATURE),
        ("visiondt:blueTemperature", "Blue Temperature (K)", DEFAULT_TEMPERATURE),
    ]

    created = []
    for attr_name, display_name, default_value in attrs:
        if not light_prim.HasAttribute(attr_name):
            attr = light_prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.Float, custom=True)
            if attr:
                attr.Set(default_value)
                attr.SetCustomDataByKey("displayName", display_name)
                attr.SetCustomDataByKey("displayGroup", "Vision DT")
                created.append(attr_name.split(":")[-1])

    # IES Profile
    if not light_prim.HasAttribute("visiondt:iesProfile"):
        attr = light_prim.CreateAttribute("visiondt:iesProfile", Sdf.ValueTypeNames.Asset, custom=True)
        if attr:
            attr.SetCustomDataByKey("displayName", "IES Profile (.ies)")
            attr.SetCustomDataByKey("displayGroup", "Vision DT")
            created.append("iesProfile")

    return created

# Main execution
print("\n" + "="*50)
print("APPLYING VISION DT ATTRIBUTES TO ALL LIGHTS")
print("="*50 + "\n")

stage = omni.usd.get_context().get_stage()
if not stage:
    print("ERROR: No stage open!")
else:
    total_updated = 0
    for prim in stage.Traverse():
        if prim.GetTypeName() in LIGHT_TYPES:
            created = apply_visiondt_to_light(prim)
            if created:
                print(f"✓ {prim.GetPath()}: Added {', '.join(created)}")
                total_updated += 1
            else:
                print(f"○ {prim.GetPath()}: Already has all attributes")

    print(f"\n{'='*50}")
    print(f"DONE! Updated {total_updated} light(s)")
    print("="*50)

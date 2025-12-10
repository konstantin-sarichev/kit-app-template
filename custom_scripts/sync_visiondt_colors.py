"""
Sync Vision DT Temperature to Light Color
Run this in Omniverse Script Editor to apply your temperature settings to light colors.

PRIORITY: Vision DT settings ALWAYS override Omniverse's default color temperature.

This script:
1. Reads visiondt: temperature values from each light
2. Calculates the final RGB color using multi-spectrum algorithm
3. Sets inputs:color on the light
4. DISABLES Omniverse's built-in 'Enable Color Temperature' to enforce priority
"""
import carb  # Omniverse logging

import math
import omni.usd
from pxr import Usd, Gf

# === Kelvin to RGB conversion ===

def clamp(x, min_val, max_val):
    return max(min_val, min(x, max_val))

def kelvin_to_rgb(kelvin):
    """Convert Kelvin to linear RGB."""
    # Validate input - clamp to valid range (1000K to 40000K)
    if kelvin is None or kelvin <= 0:
        kelvin = 6500.0  # Default to daylight
    kelvin = clamp(kelvin, 1000.0, 40000.0)

    temp = kelvin / 100.0
    r, g, b = 0.0, 0.0, 0.0

    if temp <= 66:
        r = 255
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = clamp(r, 0, 255)

    if temp <= 66:
        # Ensure temp > 0 for log calculation
        g = max(temp, 1.0)
        g = 99.4708025861 * math.log(g) - 161.1195681661
        g = clamp(g, 0, 255)
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
        g = clamp(g, 0, 255)

    if temp >= 66:
        b = 255
    else:
        if temp <= 19:
            b = 0
        else:
            b = max(temp - 10, 1.0)  # Ensure > 0 for log
            b = 138.5177312231 * math.log(b) - 305.0447927307
            b = clamp(b, 0, 255)

    # Convert to linear (gamma 2.2)
    r_linear = math.pow(r / 255.0, 2.2)
    g_linear = math.pow(g / 255.0, 2.2)
    b_linear = math.pow(b / 255.0, 2.2)

    return Gf.Vec3f(r_linear, g_linear, b_linear)

def calculate_color(overall_k, r_k, g_k, b_k):
    """Calculate final color from multi-spectrum temperatures."""
    c_r = kelvin_to_rgb(r_k)
    c_g = kelvin_to_rgb(g_k)
    c_b = kelvin_to_rgb(b_k)
    c_overall = kelvin_to_rgb(overall_k)

    final_r = c_r[0] * c_overall[0]
    final_g = c_g[1] * c_overall[1]
    final_b = c_b[2] * c_overall[2]

    return Gf.Vec3f(final_r, final_g, final_b)

# === Main sync logic ===

def log_info(msg):
    """Log to both console and Omniverse."""
    print(msg)
    carb.log_info(f"[Vision DT Sync] {msg}")

log_info("")
log_info("=" * 60)
log_info("VISION DT: SYNCING TEMPERATURES TO LIGHT COLORS")
log_info("PRIORITY: Vision DT overrides Omniverse color temperature")
log_info("=" * 60)
log_info("")

LIGHT_TYPES = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]

stage = omni.usd.get_context().get_stage()
if not stage:
    log_info("ERROR: No stage open!")
    carb.log_error("[Vision DT Sync] No stage open!")
else:
    synced = 0
    overrides = 0
    for prim in stage.Traverse():
        if prim.GetTypeName() in LIGHT_TYPES:
            # Check if has visiondt attributes
            if not prim.HasAttribute("visiondt:overallTemperature"):
                log_info(f"⚠ {prim.GetPath()}: No visiondt attributes (skipped)")
                continue

            # Get temperature values
            def get_temp(name):
                attr = prim.GetAttribute(f"visiondt:{name}")
                val = attr.Get() if attr else None
                # Handle None or invalid values
                if val is None or val <= 0:
                    return 6500.0
                return val

            overall = get_temp("overallTemperature")
            r_temp = get_temp("redTemperature")
            g_temp = get_temp("greenTemperature")
            b_temp = get_temp("blueTemperature")

            # Calculate color
            color = calculate_color(overall, r_temp, g_temp, b_temp)

            # PRIORITY ENFORCEMENT: Disable Omniverse color temperature
            ct_attr = prim.GetAttribute("inputs:enableColorTemperature")
            if ct_attr:
                if ct_attr.Get() != False:
                    ct_attr.Set(False)
                    overrides += 1
                    log_info(f"  → OVERRIDE: Disabled Omniverse color temp on {prim.GetPath()}")

            # Set color
            color_attr = prim.GetAttribute("inputs:color")
            if color_attr:
                color_attr.Set(color)
                log_info(f"✓ {prim.GetPath()}")
                log_info(f"  Temps: Overall={overall}K, R={r_temp}K, G={g_temp}K, B={b_temp}K")
                log_info(f"  Color: R={color[0]:.4f} G={color[1]:.4f} B={color[2]:.4f}")
                synced += 1

    log_info("")
    log_info("=" * 60)
    log_info(f"VISION DT: Sync complete!")
    log_info(f"  Lights synced: {synced}")
    log_info(f"  Omniverse overrides disabled: {overrides}")
    log_info("=" * 60)
    log_info("")
    log_info("Vision DT color settings are now ACTIVE and have priority")
    log_info("over Omniverse's built-in color temperature.")

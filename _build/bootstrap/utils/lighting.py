"""
Lighting Utility Functions
Provides functions for color temperature conversion and lighting calculations.

Vision DT Multi-Spectrum Color Temperature System:
- Each RGB channel can have its own Kelvin temperature
- Overall temperature acts as a tint/multiplier
- Valid range: 1000K (warm/red) to 40000K (cool/blue)
- 6500K is neutral daylight
"""

import math
import logging
from pxr import Gf

logger = logging.getLogger("vision_dt.lighting")

def clamp(x, min_val, max_val):
    """Clamp a value to a range."""
    return max(min_val, min(x, max_val))

def kelvin_to_rgb(kelvin):
    """
    Convert Kelvin color temperature to linear RGB.
    Based on Tanner Helland's algorithm, adapted for linear workflow.

    Args:
        kelvin (float): Color temperature in Kelvin (1000 to 40000)

    Returns:
        Gf.Vec3f: Linear RGB color (0.0 - 1.0)
    """
    # Validate input - handle None, zero, or out-of-range values
    if kelvin is None or kelvin <= 0:
        kelvin = 6500.0  # Default to daylight if invalid
    kelvin = clamp(kelvin, 1000.0, 40000.0)

    temp = kelvin / 100.0
    r, g, b = 0.0, 0.0, 0.0

    # Red
    if temp <= 66:
        r = 255
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = clamp(r, 0, 255)

    # Green
    if temp <= 66:
        # Ensure temp > 0 for log calculation
        g = max(temp, 1.0)
        g = 99.4708025861 * math.log(g) - 161.1195681661
        g = clamp(g, 0, 255)
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
        g = clamp(g, 0, 255)

    # Blue
    if temp >= 66:
        b = 255
    else:
        if temp <= 19:
            b = 0
        else:
            # Ensure value > 0 for log calculation
            b = max(temp - 10, 1.0)
            b = 138.5177312231 * math.log(b) - 305.0447927307
            b = clamp(b, 0, 255)

    # Convert to 0-1 range
    r_norm = r / 255.0
    g_norm = g / 255.0
    b_norm = b / 255.0

    # Approximate sRGB to Linear conversion (Gamma 2.2) for physically accurate rendering
    # Omniverse expects linear color inputs
    r_linear = math.pow(r_norm, 2.2)
    g_linear = math.pow(g_norm, 2.2)
    b_linear = math.pow(b_norm, 2.2)

    return Gf.Vec3f(r_linear, g_linear, b_linear)

def calculate_multispectrum_color(overall_k, r_k, g_k, b_k):
    """
    Calculate the final linear RGB color based on multi-spectrum Kelvin inputs.

    Strategy:
    1. Calculate RGB for each channel's specific temperature.
    2. Extract the relevant component (R from Red Temp, G from Green Temp, B from Blue Temp).
    3. This allows "Red Temp" to specifically control the character of the Red channel.
    4. Apply the Overall Temp as a tint/balance filter.

    Args:
        overall_k (float): Master temperature
        r_k (float): Red channel temperature
        g_k (float): Green channel temperature
        b_k (float): Blue channel temperature

    Returns:
        Gf.Vec3f: Final linear RGB color
    """
    # Get base colors for each channel setting
    # If R_temp is 3000K (warm), the R component should reflect that warmth (high red content)
    # If B_temp is 9000K (cool), the B component should reflect that coolness (high blue content)

    c_r = kelvin_to_rgb(r_k)
    c_g = kelvin_to_rgb(g_k)
    c_b = kelvin_to_rgb(b_k)
    c_overall = kelvin_to_rgb(overall_k)

    # Composite strategy:
    # Take the R component from the Red-specified temperature
    # Take the G component from the Green-specified temperature
    # Take the B component from the Blue-specified temperature
    # Multiply by Overall temperature color to maintain global coherence

    final_r = c_r[0] * c_overall[0]
    final_g = c_g[1] * c_overall[1]
    final_b = c_b[2] * c_overall[2]

    # Normalize max channel to 1.0 to preserve intensity (intensity is controlled separately)
    # max_val = max(final_r, final_g, final_b)
    # if max_val > 0:
    #     final_r /= max_val
    #     final_g /= max_val
    #     final_b /= max_val

    return Gf.Vec3f(final_r, final_g, final_b)

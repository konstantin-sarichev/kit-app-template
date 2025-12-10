"""
Capability: Advanced Lighting Configuration
This capability implements:
1. Logic to apply Multi-Spectrum Kelvin settings to the light's actual color.
2. IES Profile support (profile-based intensity distribution).

Priority: 45 (runs after custom attributes are added)
"""

import logging
from pxr import Usd, Sdf, UsdLux, Gf, UsdShade
import sys
from pathlib import Path

# Add bootstrap to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import (
    get_current_stage,
    find_prims_by_type,
    has_custom_attribute,
    log_capability_action,
    set_prim_metadata
)
from utils.lighting import calculate_multispectrum_color

# Required capability attributes
CAPABILITY_NAME = "Advanced Lighting Configuration"
CAPABILITY_DESCRIPTION = "Configures multi-spectrum Kelvin color and IES profiles for lights"

logger = logging.getLogger("vision_dt.capability.advanced_lighting")

def configure_ies_profile(light_prim: Usd.Prim):
    """
    Add IES Profile support to a light prim.
    Adds 'visiondt:iesProfile' and ensures UsdLuxShapingAPI is applied.
    """
    try:
        # 1. Add custom attribute for IES file selection
        # Using custom=True and visiondt: namespace for visibility in Raw USD Properties
        if not has_custom_attribute(light_prim, "visiondt:iesProfile"):
            attr = light_prim.CreateAttribute(
                "visiondt:iesProfile",
                Sdf.ValueTypeNames.Asset,
                custom=True  # Custom attributes appear in Raw USD Properties panel
            )
            if attr:
                # Use SetCustomDataByKey for display hints (correct USD API)
                attr.SetCustomDataByKey("displayName", "IES Profile (.ies)")
                attr.SetCustomDataByKey("displayGroup", "Vision DT")
            logger.info(f"Added IES Profile attribute: visiondt:iesProfile to {light_prim.GetPath()}")

        # 2. Check if ShapingAPI is applied (required for IES)
        # We don't force apply it yet unless a profile is actually set,
        # but we ensure the attribute exists to drive it.

        # If the user sets the visiondt attribute, we need to sync it to inputs:shaping:ies:file
        # This sync logic happens below in `sync_lighting_state`

        return True
    except Exception as e:
        logger.error(f"Failed to configure IES for {light_prim.GetPath()}: {e}")
        return False

def sync_lighting_state(light_prim: Usd.Prim):
    """
    Synchronize the light's standard USD attributes with Vision DT custom attributes.
    1. Calculate RGB from Kelvin attributes and set inputs:color.
    2. Sync IES profile to shaping API.
    """
    try:
        # --- Multi-Spectrum Color Logic ---

        # Get Kelvin attributes (defaults to 6500K if missing)
        # Using visiondt: namespace (without inputs: prefix)
        def get_val(name, default=6500.0):
            attr = light_prim.GetAttribute(f"visiondt:{name}")
            return attr.Get() if attr and attr.Get() is not None else default

        overall_k = get_val("overallTemperature")
        r_k = get_val("redTemperature")
        g_k = get_val("greenTemperature")
        b_k = get_val("blueTemperature")

        # Calculate Linear RGB
        final_color = calculate_multispectrum_color(overall_k, r_k, g_k, b_k)

        # Apply to inputs:color
        # We MUST disable standard inputs:enableColorTemperature to let our custom color take effect
        # otherwise USD mixes them or overrides inputs:color.

        # Ensure Color Temperature is disabled
        ct_enable_attr = light_prim.GetAttribute("inputs:enableColorTemperature")
        if not ct_enable_attr:
            # If attribute doesn't exist (some light types), we might need to create it or just set color
            # Most UsdLux lights have this.
            pass
        else:
            ct_enable_attr.Set(False)

        # Set Color
        color_attr = light_prim.GetAttribute("inputs:color")
        if color_attr:
            color_attr.Set(final_color)
            # logger.info(f"Updated color for {light_prim.GetPath()} based on Kelvin settings")

        # --- IES Profile Logic ---

        ies_attr = light_prim.GetAttribute("visiondt:iesProfile")
        if ies_attr:
            ies_path = ies_attr.Get()
            if ies_path and str(ies_path) != "":
                # User has selected an IES profile

                # Ensure ShapingAPI is applied
                if not light_prim.HasAPI(UsdLux.ShapingAPI):
                    UsdLux.ShapingAPI.Apply(light_prim)

                shaping_api = UsdLux.ShapingAPI(light_prim)
                shaping_file_attr = shaping_api.GetShapingIesFileAttr()

                # Sync value
                current_shaping_file = shaping_file_attr.Get()
                if current_shaping_file != ies_path:
                    shaping_file_attr.Set(ies_path)
                    logger.info(f"Synced IES profile for {light_prim.GetPath()}")

                    # Also ensure normalized IES is enabled usually?
                    # For now, we trust default shaping parameters or let user adjust 'inputs:shaping:ies:angleScale'
                    # We might want to expose angleScale in Vision DT group too?

        return True
    except Exception as e:
        logger.error(f"Failed to sync lighting state for {light_prim.GetPath()}: {e}")
        return False

def run(stage: Usd.Stage = None) -> tuple:
    """
    Run advanced lighting configuration.
    """
    try:
        if stage is None:
            stage = get_current_stage()
        if not stage:
            return True, "No stage (skipped)"

        # Find all lights
        light_types = [
            "DomeLight", "RectLight", "DiskLight", "SphereLight",
            "DistantLight", "CylinderLight"
        ]
        all_lights = []
        for light_type in light_types:
            all_lights.extend(find_prims_by_type(stage, light_type))

        if not all_lights:
            return True, "No lights found"

        count = 0
        for light in all_lights:
            # 1. Add IES attributes
            configure_ies_profile(light)

            # 2. Run logic to sync state (apply defaults or current values)
            if sync_lighting_state(light):
                count += 1

        msg = f"Configured advanced lighting (IES + Kelvin Logic) for {count} lights"
        logger.info(msg)
        return True, msg

    except Exception as e:
        logger.error(f"Advanced lighting failed: {e}")
        return False, str(e)

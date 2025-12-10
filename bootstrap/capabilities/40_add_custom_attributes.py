"""
Capability: Multi-Spectrum Light Color Temperature

This capability adds multi-spectrum color temperature controls to all light prims,
allowing independent control of red, green, and blue light color temperature in Kelvin
for accurate vision system lighting simulation.

Adds attributes that appear in the Properties panel below standard light properties.

Priority: 40 (runs after unit setup)
"""

import logging
from pxr import Usd, Sdf, UsdLux
import sys
from pathlib import Path

# Add bootstrap utils to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import (
    get_current_stage,
    find_prims_by_type,
    has_custom_attribute,
    create_custom_attribute,
    set_prim_metadata,
    log_capability_action
)

# Required capability attributes
CAPABILITY_NAME = "Multi-Spectrum Light Color Temperature"
CAPABILITY_DESCRIPTION = "Adds RGB multi-spectrum color temperature controls (Kelvin) to all lights for vision system simulation"

logger = logging.getLogger("vision_dt.capability.multispectrum_temperature")

# Default color temperature values in Kelvin
DEFAULT_OVERALL_TEMPERATURE = 6500.0  # Daylight (neutral white)
DEFAULT_RED_TEMPERATURE = 6500.0      # Neutral red component
DEFAULT_GREEN_TEMPERATURE = 6500.0    # Neutral green component
DEFAULT_BLUE_TEMPERATURE = 6500.0     # Neutral blue component


def configure_light_prim(light_prim: Usd.Prim) -> bool:
    """
    Add multi-spectrum color temperature attributes to a light prim.

    Adds overall and per-channel color temperature controls (in Kelvin) that appear
    in the Omniverse Properties panel below the standard light settings.

    Args:
        light_prim: Light prim to configure

    Returns:
        True if successful, False otherwise
    """
    try:
        prim_path = str(light_prim.GetPath())
        logger.info(f"Adding multi-spectrum color temperature to: {prim_path}")

        attributes_added = []

        # Add overall color temperature (master control)
        # Using custom=True and visiondt: namespace for visibility in Raw USD Properties
        if not has_custom_attribute(light_prim, "visiondt:overallTemperature"):
            attr = light_prim.CreateAttribute(
                "visiondt:overallTemperature",
                Sdf.ValueTypeNames.Float,
                custom=True  # Custom attributes appear in Raw USD Properties panel
            )
            if attr:
                attr.Set(DEFAULT_OVERALL_TEMPERATURE)
                # Use SetCustomDataByKey for display hints (correct USD API)
                attr.SetCustomDataByKey("displayName", "Overall Temperature (K)")
                attr.SetCustomDataByKey("displayGroup", "Vision DT")
                logger.info(f"  Created attribute: visiondt:overallTemperature = {DEFAULT_OVERALL_TEMPERATURE}")
                attributes_added.append("overallTemperature")

        # Add Red channel temperature
        if not has_custom_attribute(light_prim, "visiondt:redTemperature"):
            attr = light_prim.CreateAttribute(
                "visiondt:redTemperature",
                Sdf.ValueTypeNames.Float,
                custom=True
            )
            if attr:
                attr.Set(DEFAULT_RED_TEMPERATURE)
                attr.SetCustomDataByKey("displayName", "Red Temperature (K)")
                attr.SetCustomDataByKey("displayGroup", "Vision DT")
                logger.info(f"  Created attribute: visiondt:redTemperature = {DEFAULT_RED_TEMPERATURE}")
                attributes_added.append("redTemperature")

        # Add Green channel temperature
        if not has_custom_attribute(light_prim, "visiondt:greenTemperature"):
            attr = light_prim.CreateAttribute(
                "visiondt:greenTemperature",
                Sdf.ValueTypeNames.Float,
                custom=True
            )
            if attr:
                attr.Set(DEFAULT_GREEN_TEMPERATURE)
                attr.SetCustomDataByKey("displayName", "Green Temperature (K)")
                attr.SetCustomDataByKey("displayGroup", "Vision DT")
                logger.info(f"  Created attribute: visiondt:greenTemperature = {DEFAULT_GREEN_TEMPERATURE}")
                attributes_added.append("greenTemperature")

        # Add Blue channel temperature
        if not has_custom_attribute(light_prim, "visiondt:blueTemperature"):
            attr = light_prim.CreateAttribute(
                "visiondt:blueTemperature",
                Sdf.ValueTypeNames.Float,
                custom=True
            )
            if attr:
                attr.Set(DEFAULT_BLUE_TEMPERATURE)
                attr.SetCustomDataByKey("displayName", "Blue Temperature (K)")
                attr.SetCustomDataByKey("displayGroup", "Vision DT")
                logger.info(f"  Created attribute: visiondt:blueTemperature = {DEFAULT_BLUE_TEMPERATURE}")
                attributes_added.append("blueTemperature")

        # Add metadata to track configuration
        set_prim_metadata(light_prim, "vision_dt:multispectrum", True)
        set_prim_metadata(light_prim, "vision_dt:type", "multispectrum_light")

        if attributes_added:
            log_capability_action(
                "multispectrum_temperature",
                f"Added multi-spectrum color temperature controls to {prim_path}",
                f"Attributes: {', '.join(attributes_added)}"
            )
            logger.info(f"✓ Configured {len(attributes_added)} temperature attributes for {prim_path}")
        else:
            logger.info(f"Light {prim_path} already has multi-spectrum temperature controls")

        return True

    except Exception as e:
        logger.error(f"Failed to configure light {light_prim.GetPath()}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def add_stage_metadata(stage: Usd.Stage) -> bool:
    """
    Add Vision DT metadata to the stage root.

    Args:
        stage: USD stage

    Returns:
        True if successful, False otherwise
    """
    try:
        from utils.helpers import set_stage_metadata, get_stage_metadata

        # Add Vision DT identifier
        if not get_stage_metadata(stage, "vision_dt:initialized"):
            set_stage_metadata(stage, "vision_dt:initialized", True)
            set_stage_metadata(stage, "vision_dt:version", "1.0.0")
            set_stage_metadata(stage, "vision_dt:units", "millimeters")

            logger.info("Added Vision DT metadata to stage")
            return True

        return True

    except Exception as e:
        logger.error(f"Failed to add stage metadata: {e}")
        return False


def run(stage: Usd.Stage = None) -> tuple:
    """
    Add multi-spectrum color temperature controls to all lights in the stage.

    Args:
        stage: USD stage to process. If None, gets current stage.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get stage if not provided
        if stage is None:
            stage = get_current_stage()

        if stage is None:
            return True, "No stage available (skipped)"

        # Add stage-level metadata
        add_stage_metadata(stage)

        # Find all light prims - all common Omniverse light types
        light_types = [
            "DomeLight", "RectLight", "DiskLight", "SphereLight",
            "DistantLight", "CylinderLight"
        ]

        all_lights = []
        for light_type in light_types:
            lights = find_prims_by_type(stage, light_type)
            all_lights.extend(lights)

        if not all_lights:
            logger.info("No light prims found in stage")
            return True, "No lights found (skipped)"

        # Configure each light with multi-spectrum temperature controls
        configured_count = 0
        failed_count = 0

        for light_prim in all_lights:
            success = configure_light_prim(light_prim)
            if success:
                configured_count += 1
            else:
                failed_count += 1

        # Build result message
        if failed_count == 0:
            msg = f"Added multi-spectrum temperature controls to {configured_count} light(s)"
            logger.info(msg)
            return True, msg
        else:
            msg = f"Configured {configured_count} light(s), {failed_count} failed"
            logger.warning(msg)
            return True, msg  # Partial success is acceptable

    except Exception as e:
        logger.error(f"Exception in multispectrum_temperature capability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Exception: {str(e)}"

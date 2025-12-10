"""
Capability: Set Units to Millimeters

This capability ensures that the USD stage is configured to use millimeters
as the base unit. This is critical for the Vision Digital Twin project as all
optical and mechanical measurements are specified in millimeters.

Priority: 00 (runs first, before any other capabilities)
"""

import logging
from pxr import Usd, UsdGeom

# Required capability attributes
CAPABILITY_NAME = "Set Units to Millimeters"
CAPABILITY_DESCRIPTION = "Configures stage metersPerUnit to 0.001 for millimeter-based measurements"

logger = logging.getLogger("vision_dt.capability.set_units_mm")


def run(stage: Usd.Stage = None) -> tuple:
    """
    Set the stage units to millimeters.

    Args:
        stage: USD stage to configure. If None, gets current stage.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get stage if not provided
        if stage is None:
            import omni.usd
            context = omni.usd.get_context()
            if not context:
                return False, "No USD context available"
            stage = context.get_stage()

        if stage is None:
            return False, "No USD stage available"

        # Get current metersPerUnit setting
        current_mpu = UsdGeom.GetStageMetersPerUnit(stage)
        target_mpu = 0.001  # 1 unit = 1mm = 0.001 meters

        if abs(current_mpu - target_mpu) < 0.0001:
            logger.info(f"Stage already configured for millimeters (metersPerUnit={current_mpu})")
            return True, f"Already set to {current_mpu} (millimeters)"

        # Set the metersPerUnit metadata
        UsdGeom.SetStageMetersPerUnit(stage, target_mpu)

        # Verify the change
        new_mpu = UsdGeom.GetStageMetersPerUnit(stage)

        if abs(new_mpu - target_mpu) < 0.0001:
            logger.info(f"Successfully set metersPerUnit from {current_mpu} to {new_mpu}")
            return True, f"Set from {current_mpu} to {new_mpu} meters per unit (millimeters)"
        else:
            return False, f"Failed to set metersPerUnit (attempted {target_mpu}, got {new_mpu})"

    except Exception as e:
        logger.error(f"Exception in set_units_mm capability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Exception: {str(e)}"

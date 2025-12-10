"""
Capability: Configure Telecentric Cameras

This capability identifies camera prims in the stage and ensures they have
proper attributes for telecentric lens modeling. It adds custom attributes
for magnification, working distance, and other optical parameters that are
critical for accurate vision system simulation.

Priority: 20 (runs after basic setup, before transform normalization)
"""

import logging
from pxr import Usd, Sdf
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
    get_prim_metadata,
    set_prim_metadata,
    log_capability_action
)

# Required capability attributes
CAPABILITY_NAME = "Configure Telecentric Cameras"
CAPABILITY_DESCRIPTION = "Adds optical parameters and metadata to camera prims for telecentric lens modeling"

logger = logging.getLogger("vision_dt.capability.configure_cameras")

# Default optical parameters for telecentric cameras
DEFAULT_MAGNIFICATION = 0.25  # 0.25x magnification
DEFAULT_WORKING_DISTANCE = 100.0  # 100mm working distance
DEFAULT_FOV_WIDTH = 50.0  # 50mm field of view width
DEFAULT_FOV_HEIGHT = 50.0  # 50mm field of view height


def configure_camera_prim(camera_prim: Usd.Prim) -> bool:
    """
    Configure a single camera prim with telecentric lens attributes.
    
    Args:
        camera_prim: Camera prim to configure
        
    Returns:
        True if configuration was successful, False otherwise
    """
    try:
        prim_path = str(camera_prim.GetPath())
        logger.info(f"Configuring camera: {prim_path}")
        
        # Add custom optical attributes if they don't exist
        attributes_added = []
        
        # Magnification
        if not has_custom_attribute(camera_prim, "vision:magnification"):
            attr = create_custom_attribute(
                camera_prim,
                "vision:magnification",
                Sdf.ValueTypeNames.Float,
                DEFAULT_MAGNIFICATION
            )
            if attr:
                attributes_added.append("magnification")
        
        # Working Distance
        if not has_custom_attribute(camera_prim, "vision:workingDistance"):
            attr = create_custom_attribute(
                camera_prim,
                "vision:workingDistance",
                Sdf.ValueTypeNames.Float,
                DEFAULT_WORKING_DISTANCE
            )
            if attr:
                attributes_added.append("workingDistance")
        
        # Field of View dimensions
        if not has_custom_attribute(camera_prim, "vision:fovWidth"):
            attr = create_custom_attribute(
                camera_prim,
                "vision:fovWidth",
                Sdf.ValueTypeNames.Float,
                DEFAULT_FOV_WIDTH
            )
            if attr:
                attributes_added.append("fovWidth")
        
        if not has_custom_attribute(camera_prim, "vision:fovHeight"):
            attr = create_custom_attribute(
                camera_prim,
                "vision:fovHeight",
                Sdf.ValueTypeNames.Float,
                DEFAULT_FOV_HEIGHT
            )
            if attr:
                attributes_added.append("fovHeight")
        
        # Telecentric flag
        if not has_custom_attribute(camera_prim, "vision:isTelecentric"):
            attr = create_custom_attribute(
                camera_prim,
                "vision:isTelecentric",
                Sdf.ValueTypeNames.Bool,
                True
            )
            if attr:
                attributes_added.append("isTelecentric")
        
        # Add metadata
        if not get_prim_metadata(camera_prim, "vision_dt:configured"):
            set_prim_metadata(camera_prim, "vision_dt:configured", True)
            set_prim_metadata(camera_prim, "vision_dt:type", "telecentric_camera")
        
        if attributes_added:
            log_capability_action(
                "configure_cameras",
                f"Added attributes to {prim_path}",
                f"Attributes: {', '.join(attributes_added)}"
            )
            return True
        else:
            logger.info(f"Camera {prim_path} already configured")
            return True
            
    except Exception as e:
        logger.error(f"Failed to configure camera {camera_prim.GetPath()}: {e}")
        return False


def run(stage: Usd.Stage = None) -> tuple:
    """
    Configure all camera prims in the stage.
    
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
        
        # Find all camera prims
        camera_prims = find_prims_by_type(stage, "Camera")
        
        if not camera_prims:
            logger.info("No camera prims found in stage")
            return True, "No cameras found (skipped)"
        
        # Configure each camera
        configured_count = 0
        failed_count = 0
        
        for camera_prim in camera_prims:
            success = configure_camera_prim(camera_prim)
            if success:
                configured_count += 1
            else:
                failed_count += 1
        
        # Build result message
        if failed_count == 0:
            msg = f"Configured {configured_count} camera(s)"
            logger.info(msg)
            return True, msg
        else:
            msg = f"Configured {configured_count} camera(s), {failed_count} failed"
            logger.warning(msg)
            return True, msg  # Still return success as partial completion is acceptable
            
    except Exception as e:
        logger.error(f"Exception in configure_cameras capability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Exception: {str(e)}"



"""
Capability: Normalize Transforms

This capability ensures that all prims have normalized transforms without
non-uniform scaling. This is critical for maintaining physical accuracy in
the Vision Digital Twin environment where all measurements must be 1:1 with
real-world dimensions in millimeters.

Priority: 30 (runs after camera configuration)
"""

import logging
from pxr import Usd, UsdGeom, Gf
import sys
from pathlib import Path

# Add bootstrap utils to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import (
    get_current_stage,
    normalize_prim_transform,
    ensure_xform_ops,
    log_capability_action
)

# Required capability attributes
CAPABILITY_NAME = "Normalize Transforms"
CAPABILITY_DESCRIPTION = "Ensures all prims have normalized transforms without non-uniform scaling"

logger = logging.getLogger("vision_dt.capability.normalize_transforms")


def check_and_normalize_prim(prim: Usd.Prim) -> tuple:
    """
    Check if a prim needs normalization and normalize if necessary.
    
    Args:
        prim: Prim to check and normalize
        
    Returns:
        Tuple of (needed_normalization: bool, success: bool)
    """
    try:
        # Skip non-xformable prims
        if not prim.IsA(UsdGeom.Xformable):
            return False, True
        
        xformable = UsdGeom.Xformable(prim)
        xform_ops = xformable.GetOrderedXformOps()
        
        # Check for problematic scale operations
        needs_normalization = False
        for xform_op in xform_ops:
            if xform_op.GetOpType() == UsdGeom.XformOp.TypeScale:
                scale = xform_op.Get()
                if scale:
                    # Check for non-identity scale
                    if isinstance(scale, (Gf.Vec3d, Gf.Vec3f)):
                        if scale != Gf.Vec3d(1, 1, 1) and scale != Gf.Vec3f(1, 1, 1):
                            needs_normalization = True
                            break
                    elif isinstance(scale, (float, int)):
                        if abs(scale - 1.0) > 0.0001:
                            needs_normalization = True
                            break
        
        if needs_normalization:
            success = normalize_prim_transform(prim)
            return True, success
        
        # Ensure standard xform ops exist
        if not xform_ops:
            ensure_xform_ops(prim, "TRS")
        
        return False, True
        
    except Exception as e:
        logger.error(f"Error checking/normalizing prim {prim.GetPath()}: {e}")
        return False, False


def run(stage: Usd.Stage = None) -> tuple:
    """
    Normalize transforms for all relevant prims in the stage.
    
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
        
        # Track statistics
        total_checked = 0
        normalized_count = 0
        failed_count = 0
        
        # Traverse all prims
        for prim in stage.Traverse():
            # Skip certain prim types that shouldn't be normalized
            if prim.GetTypeName() in ["Shader", "Material"]:
                continue
            
            total_checked += 1
            needed_norm, success = check_and_normalize_prim(prim)
            
            if needed_norm:
                if success:
                    normalized_count += 1
                    log_capability_action(
                        "normalize_transforms",
                        f"Normalized {prim.GetPath()}"
                    )
                else:
                    failed_count += 1
        
        # Build result message
        if normalized_count == 0 and failed_count == 0:
            msg = f"All {total_checked} prims already normalized"
            logger.info(msg)
            return True, msg
        elif failed_count == 0:
            msg = f"Normalized {normalized_count}/{total_checked} prims"
            logger.info(msg)
            return True, msg
        else:
            msg = f"Normalized {normalized_count} prims, {failed_count} failed out of {total_checked} checked"
            logger.warning(msg)
            return True, msg  # Partial success is acceptable
            
    except Exception as e:
        logger.error(f"Exception in normalize_transforms capability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Exception: {str(e)}"



"""
Capability: Check Asset Consistency

This capability validates that assets follow the Vision Digital Twin naming
conventions and structural requirements. It checks for proper metadata,
consistent units, and adherence to the asset organization standards.

Priority: 50 (runs last, after all configuration is complete)
"""

import logging
from pxr import Usd, UsdGeom
import sys
from pathlib import Path

# Add bootstrap utils to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import (
    get_current_stage,
    get_stage_metadata,
    get_prim_metadata,
    find_prims_by_type,
    log_capability_action
)

# Required capability attributes
CAPABILITY_NAME = "Check Asset Consistency"
CAPABILITY_DESCRIPTION = "Validates assets follow Vision DT naming conventions and standards"

logger = logging.getLogger("vision_dt.capability.check_consistency")


def check_naming_convention(prim: Usd.Prim, prim_type: str) -> tuple:
    """
    Check if a prim follows the naming convention for its type.
    
    Args:
        prim: Prim to check
        prim_type: Type of prim (Camera, Light, etc.)
        
    Returns:
        Tuple of (is_valid: bool, message: str)
    """
    prim_name = prim.GetName()
    
    # Define naming patterns
    naming_patterns = {
        "Camera": ["Camera_", "camera_"],
        "DomeLight": ["Light_", "light_"],
        "RectLight": ["Light_", "light_"],
        "DiskLight": ["Light_", "light_"],
    }
    
    if prim_type in naming_patterns:
        patterns = naming_patterns[prim_type]
        for pattern in patterns:
            if prim_name.startswith(pattern):
                return True, "Follows naming convention"
        
        return False, f"Should start with {' or '.join(patterns)}"
    
    return True, "No specific naming convention"


def check_prim_consistency(prim: Usd.Prim) -> dict:
    """
    Check consistency of a single prim.
    
    Args:
        prim: Prim to check
        
    Returns:
        Dictionary with check results
    """
    results = {
        "path": str(prim.GetPath()),
        "type": prim.GetTypeName(),
        "issues": [],
        "warnings": []
    }
    
    try:
        # Check naming convention
        naming_valid, naming_msg = check_naming_convention(prim, prim.GetTypeName())
        if not naming_valid:
            results["warnings"].append(f"Naming: {naming_msg}")
        
        # Check for Vision DT metadata on configured prims
        prim_type = prim.GetTypeName()
        if prim_type in ["Camera", "DomeLight", "RectLight", "DiskLight", "SphereLight"]:
            if not get_prim_metadata(prim, "vision_dt:configured"):
                results["warnings"].append("Missing vision_dt:configured metadata")
        
        # Check for scale issues (should be identity after normalization)
        if prim.IsA(UsdGeom.Xformable):
            xformable = UsdGeom.Xformable(prim)
            xform_ops = xformable.GetOrderedXformOps()
            
            for xform_op in xform_ops:
                if xform_op.GetOpType() == UsdGeom.XformOp.TypeScale:
                    scale = xform_op.Get()
                    if scale:
                        from pxr import Gf
                        if isinstance(scale, (Gf.Vec3d, Gf.Vec3f)):
                            if scale != Gf.Vec3d(1, 1, 1) and scale != Gf.Vec3f(1, 1, 1):
                                results["warnings"].append(f"Non-identity scale: {scale}")
        
    except Exception as e:
        results["issues"].append(f"Error during check: {str(e)}")
    
    return results


def run(stage: Usd.Stage = None) -> tuple:
    """
    Check asset consistency across the stage.
    
    Args:
        stage: USD stage to check. If None, gets current stage.
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Get stage if not provided
        if stage is None:
            stage = get_current_stage()
        
        if stage is None:
            return True, "No stage available (skipped)"
        
        # Check stage-level consistency
        stage_issues = []
        
        # Verify units are set to millimeters
        meters_per_unit = UsdGeom.GetStageMetersPerUnit(stage)
        if abs(meters_per_unit - 0.001) > 0.0001:
            stage_issues.append(f"Units not set to millimeters (metersPerUnit={meters_per_unit})")
        
        # Verify up axis is Z
        up_axis = UsdGeom.GetStageUpAxis(stage)
        if up_axis != UsdGeom.Tokens.z:
            stage_issues.append(f"Up axis not set to Z (currently {up_axis})")
        
        # Check Vision DT initialization metadata
        if not get_stage_metadata(stage, "vision_dt:initialized"):
            stage_issues.append("Missing vision_dt:initialized metadata")
        
        # Check important prim types
        prim_types_to_check = ["Camera", "DomeLight", "RectLight", "DiskLight", "SphereLight"]
        
        all_results = []
        total_warnings = 0
        total_issues = 0
        
        for prim_type in prim_types_to_check:
            prims = find_prims_by_type(stage, prim_type)
            for prim in prims:
                result = check_prim_consistency(prim)
                if result["warnings"] or result["issues"]:
                    all_results.append(result)
                    total_warnings += len(result["warnings"])
                    total_issues += len(result["issues"])
        
        # Log detailed results
        if stage_issues:
            logger.warning("Stage-level issues:")
            for issue in stage_issues:
                logger.warning(f"  - {issue}")
        
        if all_results:
            logger.info("Prim-level findings:")
            for result in all_results:
                if result["issues"]:
                    logger.warning(f"  {result['path']}:")
                    for issue in result["issues"]:
                        logger.warning(f"    - ISSUE: {issue}")
                if result["warnings"]:
                    logger.info(f"  {result['path']}:")
                    for warning in result["warnings"]:
                        logger.info(f"    - Warning: {warning}")
        
        # Build result message
        total_stage_issues = len(stage_issues)
        
        if total_stage_issues == 0 and total_issues == 0 and total_warnings == 0:
            msg = "All assets consistent with Vision DT standards"
            logger.info(msg)
            return True, msg
        elif total_issues == 0:
            msg = f"Consistency check complete: {total_warnings} warnings, {total_stage_issues} stage issues"
            logger.info(msg)
            return True, msg
        else:
            msg = f"Found {total_issues} issues and {total_warnings} warnings"
            logger.warning(msg)
            return True, msg  # Return success even with issues, as this is a validation step
            
    except Exception as e:
        logger.error(f"Exception in check_consistency capability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Exception: {str(e)}"



"""
Helper utilities for bootstrap capabilities

Provides common functions for stage manipulation, prim operations,
and metadata management that are used across multiple capabilities.
"""

import logging
from typing import List, Optional, Any, Dict
from pathlib import Path

import omni.usd
from pxr import Usd, UsdGeom, Sdf, Gf


def get_current_stage() -> Optional[Usd.Stage]:
    """
    Get the currently active USD stage.
    
    Returns:
        Current USD stage or None if no stage is available
    """
    context = omni.usd.get_context()
    if context:
        return context.get_stage()
    return None


def set_stage_metadata(stage: Usd.Stage, key: str, value: Any) -> bool:
    """
    Set custom metadata on the stage root layer.
    
    Args:
        stage: USD stage
        key: Metadata key (will be prefixed with 'customData:')
        value: Metadata value
        
    Returns:
        True if successful, False otherwise
    """
    try:
        root_layer = stage.GetRootLayer()
        custom_data = root_layer.customLayerData
        if custom_data is None:
            custom_data = {}
        custom_data[key] = value
        root_layer.customLayerData = custom_data
        return True
    except Exception as e:
        logging.error(f"Failed to set stage metadata {key}: {e}")
        return False


def get_stage_metadata(stage: Usd.Stage, key: str, default: Any = None) -> Any:
    """
    Get custom metadata from the stage root layer.
    
    Args:
        stage: USD stage
        key: Metadata key to retrieve
        default: Default value if key not found
        
    Returns:
        Metadata value or default
    """
    try:
        root_layer = stage.GetRootLayer()
        custom_data = root_layer.customLayerData
        if custom_data and key in custom_data:
            return custom_data[key]
        return default
    except Exception as e:
        logging.error(f"Failed to get stage metadata {key}: {e}")
        return default


def find_prims_by_type(stage: Usd.Stage, prim_type: str) -> List[Usd.Prim]:
    """
    Find all prims of a specific type in the stage.
    
    Args:
        stage: USD stage to search
        prim_type: Type name to search for (e.g., 'Camera', 'Light')
        
    Returns:
        List of matching prims
    """
    matching_prims = []
    
    try:
        for prim in stage.Traverse():
            if prim.GetTypeName() == prim_type:
                matching_prims.append(prim)
    except Exception as e:
        logging.error(f"Error finding prims of type {prim_type}: {e}")
    
    return matching_prims


def find_prims_by_pattern(stage: Usd.Stage, name_pattern: str) -> List[Usd.Prim]:
    """
    Find all prims whose names match a pattern.
    
    Args:
        stage: USD stage to search
        name_pattern: Pattern to match (simple substring match)
        
    Returns:
        List of matching prims
    """
    matching_prims = []
    
    try:
        for prim in stage.Traverse():
            if name_pattern.lower() in prim.GetName().lower():
                matching_prims.append(prim)
    except Exception as e:
        logging.error(f"Error finding prims matching pattern {name_pattern}: {e}")
    
    return matching_prims


def has_custom_attribute(prim: Usd.Prim, attr_name: str) -> bool:
    """
    Check if a prim has a custom attribute.
    
    Args:
        prim: Prim to check
        attr_name: Attribute name to look for
        
    Returns:
        True if attribute exists, False otherwise
    """
    return prim.HasAttribute(attr_name)


def create_custom_attribute(
    prim: Usd.Prim,
    attr_name: str,
    attr_type: Sdf.ValueTypeName,
    default_value: Any = None,
    custom: bool = True
) -> Optional[Usd.Attribute]:
    """
    Create a custom attribute on a prim.
    
    Args:
        prim: Prim to add attribute to
        attr_name: Name of the attribute
        attr_type: USD type for the attribute (e.g., Sdf.ValueTypeNames.Float)
        default_value: Default value for the attribute
        custom: Whether this is a custom attribute
        
    Returns:
        Created attribute or None if failed
    """
    try:
        attr = prim.CreateAttribute(attr_name, attr_type, custom=custom)
        if attr and default_value is not None:
            attr.Set(default_value)
        return attr
    except Exception as e:
        logging.error(f"Failed to create attribute {attr_name} on {prim.GetPath()}: {e}")
        return None


def normalize_prim_transform(prim: Usd.Prim) -> bool:
    """
    Normalize a prim's transform by removing any scale that's not (1,1,1).
    
    This ensures that all geometry is at real-world scale without transform scaling.
    
    Args:
        prim: Prim to normalize
        
    Returns:
        True if normalization was performed, False otherwise
    """
    try:
        xformable = UsdGeom.Xformable(prim)
        if not xformable:
            return False
        
        # Get all xform ops
        xform_ops = xformable.GetOrderedXformOps()
        
        needs_normalization = False
        for xform_op in xform_ops:
            if xform_op.GetOpType() == UsdGeom.XformOp.TypeScale:
                scale = xform_op.Get()
                if scale and scale != Gf.Vec3d(1, 1, 1):
                    needs_normalization = True
                    break
        
        if needs_normalization:
            # Clear existing transform and set to identity
            xformable.ClearXformOpOrder()
            
            # Add standard transform ops (translate, rotate, scale)
            xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
            xformable.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble)
            xformable.AddScaleOp(UsdGeom.XformOp.PrecisionDouble)
            
            logging.info(f"Normalized transform for {prim.GetPath()}")
            return True
        
        return False
        
    except Exception as e:
        logging.error(f"Failed to normalize transform for {prim.GetPath()}: {e}")
        return False


def get_prim_metadata(prim: Usd.Prim, key: str, default: Any = None) -> Any:
    """
    Get custom metadata from a prim.
    
    Args:
        prim: Prim to get metadata from
        key: Metadata key
        default: Default value if not found
        
    Returns:
        Metadata value or default
    """
    try:
        custom_data = prim.GetCustomData()
        if custom_data and key in custom_data:
            return custom_data[key]
        return default
    except Exception as e:
        logging.error(f"Failed to get prim metadata {key} from {prim.GetPath()}: {e}")
        return default


def set_prim_metadata(prim: Usd.Prim, key: str, value: Any) -> bool:
    """
    Set custom metadata on a prim.
    
    Args:
        prim: Prim to set metadata on
        key: Metadata key
        value: Metadata value
        
    Returns:
        True if successful, False otherwise
    """
    try:
        custom_data = dict(prim.GetCustomData())
        custom_data[key] = value
        prim.SetCustomData(custom_data)
        return True
    except Exception as e:
        logging.error(f"Failed to set prim metadata {key} on {prim.GetPath()}: {e}")
        return False


def log_capability_action(capability_name: str, action: str, details: str = ""):
    """
    Log an action taken by a capability.
    
    Args:
        capability_name: Name of the capability performing the action
        action: Description of the action
        details: Additional details about the action
    """
    logger = logging.getLogger(f"vision_dt.capability.{capability_name}")
    message = f"[{capability_name}] {action}"
    if details:
        message += f": {details}"
    logger.info(message)


def ensure_xform_ops(prim: Usd.Prim, op_order: str = "TRS") -> bool:
    """
    Ensure a prim has standard xform ops in the specified order.
    
    Args:
        prim: Prim to configure
        op_order: Order of operations (T=Translate, R=Rotate, S=Scale)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        xformable = UsdGeom.Xformable(prim)
        if not xformable:
            return False
        
        # Check if xform ops already exist
        existing_ops = xformable.GetOrderedXformOps()
        if existing_ops:
            return True  # Already has ops
        
        # Add ops in specified order
        for op_char in op_order:
            if op_char.upper() == 'T':
                xformable.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
            elif op_char.upper() == 'R':
                xformable.AddRotateXYZOp(UsdGeom.XformOp.PrecisionDouble)
            elif op_char.upper() == 'S':
                xformable.AddScaleOp(UsdGeom.XformOp.PrecisionDouble)
        
        return True
        
    except Exception as e:
        logging.error(f"Failed to ensure xform ops on {prim.GetPath()}: {e}")
        return False


def get_assets_directory() -> Optional[Path]:
    """
    Get the path to the Assets directory.
    
    Returns:
        Path to Assets directory or None if not found
    """
    try:
        # Try to find the assets directory relative to the bootstrap directory
        bootstrap_dir = Path(__file__).parent.parent
        project_root = bootstrap_dir.parent
        assets_dir = project_root / "Assets"
        
        if assets_dir.exists():
            return assets_dir
        
        # Try alternate location (lowercase)
        assets_dir = project_root / "assets"
        if assets_dir.exists():
            return assets_dir
        
        logging.warning("Assets directory not found")
        return None
        
    except Exception as e:
        logging.error(f"Failed to get assets directory: {e}")
        return None





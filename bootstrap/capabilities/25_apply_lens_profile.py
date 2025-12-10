"""
Capability: Apply Lens Profile from Library

Priority: 25 (runs after camera configuration, before transforms)

This capability applies lens parameters from the Vision DT lens library to cameras
that have a visiondt:lens:libraryId attribute set. Lens parameters are applied
directly to Omniverse camera prims as custom profiles.

Lens Library Integration:
- Reads lens_library.json for available lenses
- Loads lens data from individual lens JSON files
- Applies optical parameters (focal length, F-stop, focus distance)
- Applies distortion model via Omniverse LensDistortion API
- Sets Vision DT custom attributes for reference

All lens optical data comes from Zemax file import.
Reference: bootstrap/documentation/ZEMAX_LENS_INTEGRATION.md
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List

# Setup path for imports
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

# Setup logging
logger = logging.getLogger(__name__)

# Try to import Omniverse modules
try:
    import omni.usd
    from pxr import Usd, UsdGeom, Sdf, Gf
    import carb
    OMNIVERSE_AVAILABLE = True
except ImportError:
    OMNIVERSE_AVAILABLE = False
    logger.warning("Omniverse modules not available - running in test mode")

# Capability metadata
CAPABILITY_NAME = "Apply Lens Profile"
CAPABILITY_DESCRIPTION = "Applies lens parameters from library to cameras with lens profile selection"


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb if available."""
    logger.info(message)
    if OMNIVERSE_AVAILABLE:
        carb.log_info(f"[Vision DT Lens] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb if available."""
    logger.warning(message)
    if OMNIVERSE_AVAILABLE:
        carb.log_warn(f"[Vision DT Lens] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb if available."""
    logger.error(message)
    if OMNIVERSE_AVAILABLE:
        carb.log_error(f"[Vision DT Lens] {message}")


# Lens attribute definitions
LENS_ATTRIBUTES = {
    # Lens profile selection
    "visiondt:lens:libraryId": (Sdf.ValueTypeNames.String, "", "Lens Library ID"),
    "visiondt:lens:profileName": (Sdf.ValueTypeNames.String, "", "Profile Name"),
    
    # Optical parameters (from Zemax)
    "visiondt:lens:focalLengthMm": (Sdf.ValueTypeNames.Float, 0.0, "Focal Length (mm)"),
    "visiondt:lens:workingDistanceMm": (Sdf.ValueTypeNames.Float, 0.0, "Working Distance (mm)"),
    "visiondt:lens:fNumber": (Sdf.ValueTypeNames.Float, 0.0, "F-Number"),
    "visiondt:lens:effectiveFocalLength": (Sdf.ValueTypeNames.Float, 0.0, "Effective Focal Length (mm)"),
    "visiondt:lens:backFocalLength": (Sdf.ValueTypeNames.Float, 0.0, "Back Focal Length (mm)"),
    "visiondt:lens:fieldOfViewDeg": (Sdf.ValueTypeNames.Float, 0.0, "Field of View (degrees)"),
    "visiondt:lens:numericalAperture": (Sdf.ValueTypeNames.Float, 0.0, "Numerical Aperture"),
    "visiondt:lens:magnification": (Sdf.ValueTypeNames.Float, 0.0, "Magnification"),
    "visiondt:lens:isTelecentric": (Sdf.ValueTypeNames.Bool, False, "Telecentric Lens"),
    "visiondt:lens:telecentricType": (Sdf.ValueTypeNames.String, "", "Telecentric Type"),
    
    # Distortion coefficients (from Zemax)
    "visiondt:lens:distortionModel": (Sdf.ValueTypeNames.String, "brown-conrady", "Distortion Model"),
    "visiondt:lens:k1": (Sdf.ValueTypeNames.Float, 0.0, "Radial Distortion k1"),
    "visiondt:lens:k2": (Sdf.ValueTypeNames.Float, 0.0, "Radial Distortion k2"),
    "visiondt:lens:k3": (Sdf.ValueTypeNames.Float, 0.0, "Radial Distortion k3"),
    "visiondt:lens:p1": (Sdf.ValueTypeNames.Float, 0.0, "Tangential Distortion p1"),
    "visiondt:lens:p2": (Sdf.ValueTypeNames.Float, 0.0, "Tangential Distortion p2"),
    
    # MTF reference values (from Zemax)
    "visiondt:lens:mtfAt50lpmm": (Sdf.ValueTypeNames.Float, 0.0, "MTF at 50 lp/mm"),
    "visiondt:lens:mtfAt100lpmm": (Sdf.ValueTypeNames.Float, 0.0, "MTF at 100 lp/mm"),
    "visiondt:lens:mtfDataPath": (Sdf.ValueTypeNames.Asset, "", "MTF Data File Path"),
    "visiondt:lens:mtfBlurEnabled": (Sdf.ValueTypeNames.Bool, False, "Enable MTF Blur Post-Process"),
    
    # Lens metadata
    "visiondt:lens:model": (Sdf.ValueTypeNames.String, "", "Lens Model"),
    "visiondt:lens:manufacturer": (Sdf.ValueTypeNames.String, "", "Manufacturer"),
    "visiondt:lens:zemaxFilePath": (Sdf.ValueTypeNames.Asset, "", "Zemax Source File"),
}


def get_lens_library():
    """Get the lens library instance."""
    try:
        from utils.lens_library import LensLibrary
        return LensLibrary()
    except ImportError:
        try:
            from lens_library import LensLibrary
            return LensLibrary()
        except ImportError:
            _log_error("Could not import LensLibrary")
            return None


def find_cameras(stage: Usd.Stage) -> List[Usd.Prim]:
    """Find all camera prims in the stage."""
    cameras = []
    for prim in stage.Traverse():
        if prim.GetTypeName() == "Camera":
            cameras.append(prim)
    return cameras


def add_lens_attributes(camera_prim: Usd.Prim) -> int:
    """
    Add Vision DT lens attributes to a camera prim.
    
    Args:
        camera_prim: Camera prim to add attributes to
        
    Returns:
        Number of attributes added
    """
    added = 0
    
    for attr_name, (attr_type, default_value, display_name) in LENS_ATTRIBUTES.items():
        if not camera_prim.HasAttribute(attr_name):
            try:
                attr = camera_prim.CreateAttribute(attr_name, attr_type, custom=True)
                if attr and default_value is not None:
                    # Handle Asset type specially
                    if attr_type == Sdf.ValueTypeNames.Asset and default_value == "":
                        attr.Set(Sdf.AssetPath(""))
                    else:
                        attr.Set(default_value)
                
                # Set display metadata
                if attr:
                    attr.SetCustomDataByKey("displayName", display_name)
                    attr.SetCustomDataByKey("displayGroup", "Vision DT Lens")
                
                added += 1
            except Exception as e:
                _log_error(f"Failed to create attribute {attr_name}: {e}")
    
    return added


def apply_lens_profile(camera_prim: Usd.Prim, lens_data: Dict) -> bool:
    """
    Apply lens parameters from library to camera prim.
    
    Args:
        camera_prim: Camera prim to apply lens to
        lens_data: Lens data dictionary from library
        
    Returns:
        True if successful
    """
    try:
        camera = UsdGeom.Camera(camera_prim)
        
        # Apply core optical parameters to Omniverse camera
        focal_length = lens_data.get("focal_length_mm", 0)
        if focal_length > 0:
            camera.GetFocalLengthAttr().Set(focal_length)
            _log_info(f"  → Set focal length: {focal_length}mm")
        
        f_number = lens_data.get("f_number", 0)
        if f_number > 0:
            camera.GetFStopAttr().Set(f_number)
            _log_info(f"  → Set F-stop: f/{f_number}")
        
        working_distance = lens_data.get("working_distance_mm", 0)
        if working_distance > 0:
            camera.GetFocusDistanceAttr().Set(working_distance)
            _log_info(f"  → Set focus distance: {working_distance}mm")
        
        # Apply distortion model
        apply_distortion(camera_prim, lens_data)
        
        # Apply telecentric projection if applicable
        if lens_data.get("is_telecentric", False):
            apply_telecentric_projection(camera_prim, lens_data)
        
        # Set Vision DT lens attributes for reference
        set_lens_attributes(camera_prim, lens_data)
        
        return True
        
    except Exception as e:
        _log_error(f"Failed to apply lens profile: {e}")
        return False


def apply_distortion(camera_prim: Usd.Prim, lens_data: Dict):
    """
    Apply lens distortion model to camera.
    
    Uses Omniverse's OmniLensDistortionOpenCvPinholeAPI for Brown-Conrady model.
    """
    distortion_model = lens_data.get("distortion_model", "brown-conrady")
    
    k1 = lens_data.get("k1", 0)
    k2 = lens_data.get("k2", 0)
    k3 = lens_data.get("k3", 0)
    p1 = lens_data.get("p1", 0)
    p2 = lens_data.get("p2", 0)
    
    # Only apply if there are non-zero distortion coefficients
    if k1 == 0 and k2 == 0 and k3 == 0 and p1 == 0 and p2 == 0:
        return
    
    try:
        if distortion_model == "brown-conrady":
            # Apply OpenCV pinhole distortion API
            camera_prim.ApplyAPI("OmniLensDistortionOpenCvPinholeAPI")
            
            # Set distortion parameters
            set_or_create_attr(camera_prim, "lensDistortion:k1", Sdf.ValueTypeNames.Float, k1)
            set_or_create_attr(camera_prim, "lensDistortion:k2", Sdf.ValueTypeNames.Float, k2)
            set_or_create_attr(camera_prim, "lensDistortion:k3", Sdf.ValueTypeNames.Float, k3)
            set_or_create_attr(camera_prim, "lensDistortion:p1", Sdf.ValueTypeNames.Float, p1)
            set_or_create_attr(camera_prim, "lensDistortion:p2", Sdf.ValueTypeNames.Float, p2)
            
            _log_info(f"  → Applied Brown-Conrady distortion: k1={k1:.6f}, k2={k2:.6f}, k3={k3:.6f}")
            
        elif distortion_model == "fisheye":
            # Apply fisheye distortion API
            camera_prim.ApplyAPI("OmniLensDistortionFisheyeAPI")
            
            # Set fisheye parameters (k1-k4)
            set_or_create_attr(camera_prim, "lensDistortion:k1", Sdf.ValueTypeNames.Float, k1)
            set_or_create_attr(camera_prim, "lensDistortion:k2", Sdf.ValueTypeNames.Float, k2)
            set_or_create_attr(camera_prim, "lensDistortion:k3", Sdf.ValueTypeNames.Float, k3)
            set_or_create_attr(camera_prim, "lensDistortion:k4", Sdf.ValueTypeNames.Float, lens_data.get("k4", 0))
            
            _log_info(f"  → Applied Fisheye distortion")
            
    except Exception as e:
        _log_warn(f"  → Could not apply distortion API: {e}")


def apply_telecentric_projection(camera_prim: Usd.Prim, lens_data: Dict):
    """
    Apply telecentric projection settings to camera.
    
    Telecentric lenses have parallel chief rays, which can be approximated
    with orthographic projection in some cases.
    """
    telecentric_type = lens_data.get("telecentric_type", "object-space")
    magnification = lens_data.get("magnification", 1.0)
    
    try:
        camera = UsdGeom.Camera(camera_prim)
        
        # For true telecentric simulation, we might use orthographic projection
        # Note: This is a simplification; full telecentric behavior requires
        # custom shader or post-processing
        
        # Store telecentric info as attributes for reference
        set_or_create_attr(camera_prim, "visiondt:lens:isTelecentric", 
                          Sdf.ValueTypeNames.Bool, True)
        set_or_create_attr(camera_prim, "visiondt:lens:telecentricType", 
                          Sdf.ValueTypeNames.String, telecentric_type)
        
        _log_info(f"  → Marked as telecentric ({telecentric_type})")
        
    except Exception as e:
        _log_warn(f"  → Could not apply telecentric projection: {e}")


def set_lens_attributes(camera_prim: Usd.Prim, lens_data: Dict):
    """Set Vision DT lens attributes on camera for reference."""
    
    # Profile name
    model = lens_data.get("model", "")
    manufacturer = lens_data.get("manufacturer", "")
    profile_name = f"{manufacturer} {model}".strip()
    
    set_or_create_attr(camera_prim, "visiondt:lens:profileName", 
                      Sdf.ValueTypeNames.String, profile_name)
    
    # Optical parameters
    attr_mapping = {
        "visiondt:lens:focalLengthMm": ("focal_length_mm", Sdf.ValueTypeNames.Float),
        "visiondt:lens:workingDistanceMm": ("working_distance_mm", Sdf.ValueTypeNames.Float),
        "visiondt:lens:fNumber": ("f_number", Sdf.ValueTypeNames.Float),
        "visiondt:lens:fieldOfViewDeg": ("field_of_view_deg", Sdf.ValueTypeNames.Float),
        "visiondt:lens:magnification": ("magnification", Sdf.ValueTypeNames.Float),
        "visiondt:lens:numericalAperture": ("numerical_aperture", Sdf.ValueTypeNames.Float),
        "visiondt:lens:isTelecentric": ("is_telecentric", Sdf.ValueTypeNames.Bool),
        "visiondt:lens:telecentricType": ("telecentric_type", Sdf.ValueTypeNames.String),
        
        # Distortion
        "visiondt:lens:distortionModel": ("distortion_model", Sdf.ValueTypeNames.String),
        "visiondt:lens:k1": ("k1", Sdf.ValueTypeNames.Float),
        "visiondt:lens:k2": ("k2", Sdf.ValueTypeNames.Float),
        "visiondt:lens:k3": ("k3", Sdf.ValueTypeNames.Float),
        "visiondt:lens:p1": ("p1", Sdf.ValueTypeNames.Float),
        "visiondt:lens:p2": ("p2", Sdf.ValueTypeNames.Float),
        
        # MTF
        "visiondt:lens:mtfAt50lpmm": ("mtf_at_50lpmm", Sdf.ValueTypeNames.Float),
        "visiondt:lens:mtfAt100lpmm": ("mtf_at_100lpmm", Sdf.ValueTypeNames.Float),
        
        # Metadata
        "visiondt:lens:model": ("model", Sdf.ValueTypeNames.String),
        "visiondt:lens:manufacturer": ("manufacturer", Sdf.ValueTypeNames.String),
    }
    
    for attr_name, (data_key, attr_type) in attr_mapping.items():
        value = lens_data.get(data_key)
        if value is not None:
            set_or_create_attr(camera_prim, attr_name, attr_type, value)
    
    # Zemax file path (Asset type)
    zemax_file = lens_data.get("zemax_file", "")
    if zemax_file:
        set_or_create_attr(camera_prim, "visiondt:lens:zemaxFilePath", 
                          Sdf.ValueTypeNames.Asset, Sdf.AssetPath(zemax_file))


def set_or_create_attr(prim: Usd.Prim, attr_name: str, attr_type, value):
    """Set attribute value, creating it if needed."""
    try:
        attr = prim.GetAttribute(attr_name)
        if not attr:
            attr = prim.CreateAttribute(attr_name, attr_type, custom=True)
        if attr:
            attr.Set(value)
    except Exception as e:
        _log_warn(f"Could not set {attr_name}: {e}")


def run():
    """
    Main capability function - runs on stage open.
    
    1. Finds all cameras in stage
    2. Adds Vision DT lens attributes if missing
    3. Applies lens profiles from library for cameras with libraryId set
    """
    if not OMNIVERSE_AVAILABLE:
        logger.info("Running in test mode - Omniverse not available")
        return
    
    try:
        context = omni.usd.get_context()
        stage = context.get_stage()
        
        if not stage:
            _log_warn("No stage available")
            return
        
        _log_info("=" * 50)
        _log_info("Apply Lens Profile Capability")
        _log_info("=" * 50)
        
        # Find all cameras
        cameras = find_cameras(stage)
        _log_info(f"Found {len(cameras)} camera(s) in stage")
        
        if not cameras:
            return
        
        # Get lens library
        lens_lib = get_lens_library()
        if lens_lib:
            _log_info(f"Lens library loaded: {lens_lib.get_lens_count()} lenses available")
        else:
            _log_warn("Lens library not available")
        
        # Process each camera
        cameras_configured = 0
        profiles_applied = 0
        
        for camera_prim in cameras:
            camera_path = str(camera_prim.GetPath())
            _log_info(f"\nProcessing camera: {camera_path}")
            
            # Add lens attributes if missing
            added = add_lens_attributes(camera_prim)
            if added > 0:
                _log_info(f"  → Added {added} lens attributes")
            
            cameras_configured += 1
            
            # Check for lens library ID
            lens_id_attr = camera_prim.GetAttribute("visiondt:lens:libraryId")
            if lens_id_attr:
                lens_id = lens_id_attr.Get()
                if lens_id and lens_lib:
                    # Load and apply lens profile
                    lens_data = lens_lib.get_lens_for_camera(lens_id)
                    if lens_data:
                        _log_info(f"  → Applying lens profile: {lens_id}")
                        if apply_lens_profile(camera_prim, lens_data):
                            profiles_applied += 1
                    else:
                        _log_warn(f"  → Lens profile not found: {lens_id}")
        
        _log_info(f"\n{'=' * 50}")
        _log_info(f"Lens Profile Summary:")
        _log_info(f"  Cameras configured: {cameras_configured}")
        _log_info(f"  Lens profiles applied: {profiles_applied}")
        _log_info(f"{'=' * 50}")
        
    except Exception as e:
        _log_error(f"Lens profile capability failed: {e}")
        import traceback
        traceback.print_exc()


# Utility functions for external use

def apply_lens_to_camera(camera_prim: Usd.Prim, lens_id: str) -> bool:
    """
    Apply a lens profile from the library to a camera.
    
    Args:
        camera_prim: Camera prim to apply lens to
        lens_id: Lens library ID
        
    Returns:
        True if successful
    """
    lens_lib = get_lens_library()
    if not lens_lib:
        _log_error("Lens library not available")
        return False
    
    lens_data = lens_lib.get_lens_for_camera(lens_id)
    if not lens_data:
        _log_error(f"Lens not found: {lens_id}")
        return False
    
    # Set the library ID attribute
    set_or_create_attr(camera_prim, "visiondt:lens:libraryId", 
                      Sdf.ValueTypeNames.String, lens_id)
    
    return apply_lens_profile(camera_prim, lens_data)


def list_available_lenses() -> List[Dict]:
    """Get list of available lenses from library."""
    lens_lib = get_lens_library()
    if lens_lib:
        return lens_lib.list_lenses()
    return []


def get_lens_info(lens_id: str) -> Optional[Dict]:
    """Get lens information for display."""
    lens_lib = get_lens_library()
    if lens_lib:
        return lens_lib.get_lens_for_camera(lens_id)
    return None


# For testing
if __name__ == "__main__":
    print("Lens Profile Capability - Test Mode")
    print("=" * 50)
    
    # Test without Omniverse
    lens_lib = get_lens_library()
    if lens_lib:
        lens_lib.ensure_directory_structure()
        print(f"Lens library path: {lens_lib.library_path}")
        print(f"Lenses in library: {lens_lib.get_lens_count()}")
        
        for lens in lens_lib.list_lenses():
            print(f"  - {lens['id']}: {lens['manufacturer']} {lens['model']}")
    else:
        print("Could not load lens library")


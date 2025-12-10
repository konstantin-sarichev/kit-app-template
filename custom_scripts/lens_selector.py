"""
Lens Selector for Vision DT

Run this script in Omniverse Script Editor to:
1. List available lenses
2. Apply a lens to the selected camera

Usage:
    1. Select a camera in the viewport
    2. Run this script
    3. Call: apply_lens('lens_id')

Available lens IDs:
  Telecentric:
    - telecentric_0.5x_wd100
    - telecentric_1.0x_wd65
    - telecentric_2.0x_wd30
  Standard:
    - mv_8mm_f1.4
    - mv_12mm_f1.4
    - mv_25mm_f1.4
    - mv_50mm_f2.8
    - mv_75mm_f2.8
"""

import json
import carb
import omni.usd
from pathlib import Path
from pxr import Usd, UsdGeom, Sdf, Gf


def _log(message: str):
    """Log to Omniverse console."""
    print(message)
    carb.log_info(f"[Lens Selector] {message}")


def get_project_root():
    """Get project root directory."""
    # Common locations - adjust if needed
    paths = [
        Path("G:/Vision_Example_1/kit-app-template"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def load_lens_data(lens_id: str):
    """Load lens data directly from JSON file."""
    project_root = get_project_root()
    if not project_root:
        _log("ERROR: Could not find project root")
        return None

    # Try to find the lens data file
    lens_data_path = project_root / "assets" / "Lenses" / "Library" / "Preset" / lens_id / "lens_data.json"

    if not lens_data_path.exists():
        _log(f"ERROR: Lens data file not found: {lens_data_path}")
        return None

    try:
        with open(lens_data_path, 'r') as f:
            data = json.load(f)
        _log(f"Loaded lens data from: {lens_data_path}")
        return data
    except Exception as e:
        _log(f"ERROR: Failed to load lens data: {e}")
        return None


def get_selected_camera():
    """Get the currently selected camera prim."""
    context = omni.usd.get_context()
    stage = context.get_stage()

    if not stage:
        _log("ERROR: No stage available")
        return None

    selection = context.get_selection()
    selected_paths = selection.get_selected_prim_paths()

    for path in selected_paths:
        prim = stage.GetPrimAtPath(path)
        if prim and prim.GetTypeName() == "Camera":
            return prim

    # If no camera selected, try to find one
    for prim in stage.Traverse():
        if prim.GetTypeName() == "Camera":
            _log(f"Using camera: {prim.GetPath()}")
            return prim

    return None


def list_lenses():
    """List all available lenses."""
    _log("=" * 60)
    _log("AVAILABLE LENSES")
    _log("=" * 60)

    lenses = {
        "TELECENTRIC": [
            ("telecentric_0.5x_wd100", "0.5x Telecentric", "WD 100mm, f/8"),
            ("telecentric_1.0x_wd65", "1.0x Telecentric", "WD 65mm, f/8"),
            ("telecentric_2.0x_wd30", "2.0x Telecentric", "WD 30mm, f/6"),
        ],
        "STANDARD": [
            ("mv_8mm_f1.4", "8mm f/1.4", "Wide angle, FOV 67°"),
            ("mv_12mm_f1.4", "12mm f/1.4", "Standard, FOV 48°"),
            ("mv_25mm_f1.4", "25mm f/1.4", "Medium, FOV 25°"),
            ("mv_50mm_f2.8", "50mm f/2.8", "Narrow, FOV 12.5°"),
            ("mv_75mm_f2.8", "75mm f/2.8", "Long, FOV 8.5°"),
        ]
    }

    for category, items in lenses.items():
        _log(f"\n  {category} LENSES:")
        for lens_id, name, desc in items:
            _log(f"    [{lens_id}]")
            _log(f"      {name} - {desc}")

    _log("\n" + "=" * 60)
    _log("To apply: apply_lens('lens_id')")
    _log("Example:  apply_lens('telecentric_0.5x_wd100')")
    _log("=" * 60)


def apply_lens(lens_id: str, camera_prim=None):
    """
    Apply a lens profile to the selected camera.

    This function:
    1. Loads lens data from the library
    2. Applies focal length, F-stop, focus distance to camera
    3. Sets orthographic projection for telecentric lenses
    4. Sets all Vision DT lens attributes
    5. Overrides existing Omniverse camera settings

    Args:
        lens_id: ID of the lens (e.g., 'telecentric_0.5x_wd100')
        camera_prim: Optional camera prim (uses selected if not provided)
    """
    _log("=" * 60)
    _log(f"APPLYING LENS: {lens_id}")
    _log("=" * 60)

    # Get camera
    if camera_prim is None:
        camera_prim = get_selected_camera()

    if not camera_prim:
        _log("ERROR: No camera found. Select a camera first.")
        return False

    camera_path = str(camera_prim.GetPath())
    _log(f"Camera: {camera_path}")

    # Load lens data
    lens_data = load_lens_data(lens_id)
    if not lens_data:
        _log(f"ERROR: Could not load lens '{lens_id}'")
        _log("Run list_lenses() to see available lenses")
        return False

    # Get data sections
    metadata = lens_data.get("metadata", {})
    optical = lens_data.get("optical", {})
    distortion = lens_data.get("distortion", {})
    mtf = lens_data.get("mtf", {})

    model = metadata.get("model", lens_id)
    manufacturer = metadata.get("manufacturer", "Preset")

    _log(f"Lens: {manufacturer} {model}")
    _log("-" * 40)

    try:
        camera = UsdGeom.Camera(camera_prim)

        # ============================================================
        # APPLY CORE OMNIVERSE CAMERA SETTINGS
        # These override the default Omniverse camera properties
        # ============================================================

        # Focal Length
        focal_length = optical.get("focal_length_mm", 0)
        if focal_length > 0:
            camera.GetFocalLengthAttr().Set(focal_length)
            _log(f"  ✓ Focal Length: {focal_length}mm (APPLIED)")
        else:
            _log(f"  - Focal Length: Not specified (telecentric uses magnification)")

        # F-Stop (F-Number)
        f_number = optical.get("f_number", 0)
        if f_number > 0:
            camera.GetFStopAttr().Set(f_number)
            _log(f"  ✓ F-Stop: f/{f_number} (APPLIED)")

        # Focus Distance (Working Distance)
        working_distance = optical.get("working_distance_mm", 0)
        if working_distance > 0:
            camera.GetFocusDistanceAttr().Set(working_distance)
            _log(f"  ✓ Focus Distance: {working_distance}mm (APPLIED)")

        # ============================================================
        # TELECENTRIC PROJECTION
        # For telecentric lenses, use orthographic projection
        # ============================================================

        is_telecentric = optical.get("is_telecentric", False)
        telecentric_type = optical.get("telecentric_type", "")

        if is_telecentric:
            _log("-" * 40)
            _log("  TELECENTRIC LENS DETECTED")

            # Set projection to orthographic
            projection_attr = camera.GetProjectionAttr()
            if projection_attr:
                projection_attr.Set(UsdGeom.Tokens.orthographic)
                _log(f"  ✓ Projection: ORTHOGRAPHIC (APPLIED)")

            # For telecentric, set horizontal aperture based on magnification
            magnification = optical.get("magnification", 1.0)
            if magnification > 0:
                # Calculate sensor coverage based on magnification
                # Assuming 1/2" sensor (6.4mm x 4.8mm) as reference
                sensor_width = 6.4 / magnification  # Object-space FOV width
                camera.GetHorizontalApertureAttr().Set(sensor_width)
                _log(f"  ✓ Magnification: {magnification}x")
                _log(f"  ✓ Horizontal Aperture: {sensor_width:.2f}mm (APPLIED)")

            _log(f"  ✓ Telecentric Type: {telecentric_type}")
        else:
            # Standard perspective projection
            projection_attr = camera.GetProjectionAttr()
            if projection_attr:
                projection_attr.Set(UsdGeom.Tokens.perspective)
                _log(f"  ✓ Projection: PERSPECTIVE")

        # ============================================================
        # SET VISION DT LENS ATTRIBUTES
        # These are stored for reference and future use
        # ============================================================

        _log("-" * 40)
        _log("  Setting Vision DT Lens Attributes...")

        # Profile identification
        _set_attr(camera_prim, "visiondt:lens:libraryId", Sdf.ValueTypeNames.String, lens_id)
        _set_attr(camera_prim, "visiondt:lens:profileName", Sdf.ValueTypeNames.String, f"{manufacturer} {model}")

        # Optical parameters
        _set_attr(camera_prim, "visiondt:lens:focalLengthMm", Sdf.ValueTypeNames.Float, focal_length)
        _set_attr(camera_prim, "visiondt:lens:workingDistanceMm", Sdf.ValueTypeNames.Float, working_distance)
        _set_attr(camera_prim, "visiondt:lens:fNumber", Sdf.ValueTypeNames.Float, f_number)
        _set_attr(camera_prim, "visiondt:lens:fieldOfViewDeg", Sdf.ValueTypeNames.Float, optical.get("field_of_view_deg", 0))
        _set_attr(camera_prim, "visiondt:lens:magnification", Sdf.ValueTypeNames.Float, optical.get("magnification", 0))
        _set_attr(camera_prim, "visiondt:lens:numericalAperture", Sdf.ValueTypeNames.Float, optical.get("numerical_aperture", 0))
        _set_attr(camera_prim, "visiondt:lens:isTelecentric", Sdf.ValueTypeNames.Bool, is_telecentric)
        _set_attr(camera_prim, "visiondt:lens:telecentricType", Sdf.ValueTypeNames.String, telecentric_type)

        # Distortion
        _set_attr(camera_prim, "visiondt:lens:distortionModel", Sdf.ValueTypeNames.String, distortion.get("model", "brown-conrady"))
        _set_attr(camera_prim, "visiondt:lens:k1", Sdf.ValueTypeNames.Float, distortion.get("k1", 0))
        _set_attr(camera_prim, "visiondt:lens:k2", Sdf.ValueTypeNames.Float, distortion.get("k2", 0))
        _set_attr(camera_prim, "visiondt:lens:k3", Sdf.ValueTypeNames.Float, distortion.get("k3", 0))
        _set_attr(camera_prim, "visiondt:lens:p1", Sdf.ValueTypeNames.Float, distortion.get("p1", 0))
        _set_attr(camera_prim, "visiondt:lens:p2", Sdf.ValueTypeNames.Float, distortion.get("p2", 0))

        # MTF
        _set_attr(camera_prim, "visiondt:lens:mtfAt50lpmm", Sdf.ValueTypeNames.Float, mtf.get("mtf_at_50lpmm", 0))
        _set_attr(camera_prim, "visiondt:lens:mtfAt100lpmm", Sdf.ValueTypeNames.Float, mtf.get("mtf_at_100lpmm", 0))

        # Metadata
        _set_attr(camera_prim, "visiondt:lens:model", Sdf.ValueTypeNames.String, model)
        _set_attr(camera_prim, "visiondt:lens:manufacturer", Sdf.ValueTypeNames.String, manufacturer)

        _log("  ✓ All Vision DT attributes set")

        # ============================================================
        # APPLY DISTORTION (if non-zero)
        # ============================================================

        k1 = distortion.get("k1", 0)
        k2 = distortion.get("k2", 0)

        if k1 != 0 or k2 != 0:
            _log("-" * 40)
            _log("  Applying lens distortion...")
            try:
                # Try to apply distortion API
                camera_prim.ApplyAPI("OmniLensDistortionOpenCvPinholeAPI")
                _set_attr(camera_prim, "lensDistortion:k1", Sdf.ValueTypeNames.Float, k1)
                _set_attr(camera_prim, "lensDistortion:k2", Sdf.ValueTypeNames.Float, k2)
                _set_attr(camera_prim, "lensDistortion:k3", Sdf.ValueTypeNames.Float, distortion.get("k3", 0))
                _set_attr(camera_prim, "lensDistortion:p1", Sdf.ValueTypeNames.Float, distortion.get("p1", 0))
                _set_attr(camera_prim, "lensDistortion:p2", Sdf.ValueTypeNames.Float, distortion.get("p2", 0))
                _log(f"  ✓ Distortion: k1={k1:.4f}, k2={k2:.4f} (APPLIED)")
            except Exception as e:
                _log(f"  ! Distortion API not available: {e}")

        # ============================================================
        # SUMMARY
        # ============================================================

        _log("=" * 60)
        _log(f"✓ LENS APPLIED SUCCESSFULLY: {lens_id}")
        _log("=" * 60)

        if is_telecentric:
            _log("NOTE: Camera is now using ORTHOGRAPHIC projection")
            _log("      (telecentric lenses have parallel rays)")

        return True

    except Exception as e:
        _log(f"ERROR: Failed to apply lens: {e}")
        import traceback
        traceback.print_exc()
        return False


def _set_attr(prim, attr_name, attr_type, value):
    """Set or create an attribute with logging."""
    try:
        attr = prim.GetAttribute(attr_name)
        if not attr:
            attr = prim.CreateAttribute(attr_name, attr_type, custom=True)
            attr.SetCustomDataByKey("displayGroup", "Vision DT Lens")
        if attr:
            attr.Set(value)
            return True
    except Exception as e:
        _log(f"  ! Could not set {attr_name}: {e}")
    return False


# ============================================================
# MAIN - Run when script is executed
# ============================================================

if __name__ == "__main__":
    _log("")
    _log("╔════════════════════════════════════════════════════════════╗")
    _log("║           VISION DT LENS SELECTOR                          ║")
    _log("╚════════════════════════════════════════════════════════════╝")
    _log("")

    # Check for camera
    camera = get_selected_camera()
    if camera:
        _log(f"Current camera: {camera.GetPath()}")
    else:
        _log("No camera selected - select a camera to apply lens")

    # List available lenses
    list_lenses()

    _log("")
    _log("Quick apply examples:")
    _log("  apply_lens('telecentric_0.5x_wd100')  # Telecentric 0.5x")
    _log("  apply_lens('mv_25mm_f1.4')            # 25mm standard lens")
    _log("")

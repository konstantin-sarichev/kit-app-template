"""
Camera Watcher - Automatically applies Vision DT lens attributes to newly created cameras.

This module subscribes to USD stage changes and detects when new camera prims
are added, automatically configuring them with Vision DT lens attributes.

When active, ANY new camera created will automatically receive:

  Vision DT Lens Attributes:
  - visiondt:lens:libraryId (lens library selection)
  - visiondt:lens:profileName (display name)
  - visiondt:lens:focalLengthMm, workingDistanceMm, fNumber
  - visiondt:lens:isTelecentric, magnification, fieldOfViewDeg
  - visiondt:lens:k1, k2, k3, p1, p2 (distortion coefficients)
  - visiondt:lens:mtfAt50lpmm, mtfAt100lpmm (MTF reference)
  - visiondt:lens:model, manufacturer, zemaxFilePath

After adding attributes, set visiondt:lens:libraryId to a lens ID from the
lens library, and the lens profile will be applied on next stage open.

Reference: bootstrap/documentation/ZEMAX_LENS_INTEGRATION.md
"""

import logging
import carb
import omni.usd
from pxr import Usd, Sdf, Tf

logger = logging.getLogger("vision_dt.camera_watcher")

# Singleton watcher instance
_watcher_instance = None


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb logger."""
    logger.info(message)
    carb.log_info(f"[Vision DT CameraWatcher] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb logger."""
    logger.warning(message)
    carb.log_warn(f"[Vision DT CameraWatcher] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb logger."""
    logger.error(message)
    carb.log_error(f"[Vision DT CameraWatcher] {message}")


# Lens attribute definitions - matches 25_apply_lens_profile.py
LENS_ATTRIBUTES = {
    # Lens profile selection (Vision DT Lens - Profile group)
    "visiondt:lens:libraryId": (Sdf.ValueTypeNames.String, "", "Lens Library ID", "Vision DT Lens - Profile"),
    "visiondt:lens:profileName": (Sdf.ValueTypeNames.String, "", "Profile Name", "Vision DT Lens - Profile"),

    # Optical parameters (Vision DT Lens - Optical group)
    "visiondt:lens:focalLengthMm": (Sdf.ValueTypeNames.Float, 0.0, "Focal Length (mm)", "Vision DT Lens - Optical"),
    "visiondt:lens:workingDistanceMm": (Sdf.ValueTypeNames.Float, 0.0, "Working Distance (mm)", "Vision DT Lens - Optical"),
    "visiondt:lens:fNumber": (Sdf.ValueTypeNames.Float, 0.0, "F-Number", "Vision DT Lens - Optical"),
    "visiondt:lens:effectiveFocalLength": (Sdf.ValueTypeNames.Float, 0.0, "Effective Focal Length (mm)", "Vision DT Lens - Optical"),
    "visiondt:lens:backFocalLength": (Sdf.ValueTypeNames.Float, 0.0, "Back Focal Length (mm)", "Vision DT Lens - Optical"),
    "visiondt:lens:fieldOfViewDeg": (Sdf.ValueTypeNames.Float, 0.0, "Field of View (degrees)", "Vision DT Lens - Optical"),
    "visiondt:lens:numericalAperture": (Sdf.ValueTypeNames.Float, 0.0, "Numerical Aperture", "Vision DT Lens - Optical"),
    "visiondt:lens:magnification": (Sdf.ValueTypeNames.Float, 0.0, "Magnification", "Vision DT Lens - Optical"),
    "visiondt:lens:isTelecentric": (Sdf.ValueTypeNames.Bool, False, "Telecentric Lens", "Vision DT Lens - Optical"),
    "visiondt:lens:telecentricType": (Sdf.ValueTypeNames.String, "", "Telecentric Type", "Vision DT Lens - Optical"),

    # Distortion coefficients (Vision DT Lens - Distortion group)
    "visiondt:lens:distortionModel": (Sdf.ValueTypeNames.String, "brown-conrady", "Distortion Model", "Vision DT Lens - Distortion"),
    "visiondt:lens:k1": (Sdf.ValueTypeNames.Float, 0.0, "Radial Distortion k1", "Vision DT Lens - Distortion"),
    "visiondt:lens:k2": (Sdf.ValueTypeNames.Float, 0.0, "Radial Distortion k2", "Vision DT Lens - Distortion"),
    "visiondt:lens:k3": (Sdf.ValueTypeNames.Float, 0.0, "Radial Distortion k3", "Vision DT Lens - Distortion"),
    "visiondt:lens:p1": (Sdf.ValueTypeNames.Float, 0.0, "Tangential Distortion p1", "Vision DT Lens - Distortion"),
    "visiondt:lens:p2": (Sdf.ValueTypeNames.Float, 0.0, "Tangential Distortion p2", "Vision DT Lens - Distortion"),

    # MTF reference values (Vision DT Lens - MTF group)
    "visiondt:lens:mtfAt50lpmm": (Sdf.ValueTypeNames.Float, 0.0, "MTF at 50 lp/mm", "Vision DT Lens - MTF"),
    "visiondt:lens:mtfAt100lpmm": (Sdf.ValueTypeNames.Float, 0.0, "MTF at 100 lp/mm", "Vision DT Lens - MTF"),
    "visiondt:lens:mtfBlurEnabled": (Sdf.ValueTypeNames.Bool, False, "Enable MTF Blur Post-Process", "Vision DT Lens - MTF"),

    # Lens metadata (Vision DT Lens - Info group)
    "visiondt:lens:model": (Sdf.ValueTypeNames.String, "", "Lens Model", "Vision DT Lens - Info"),
    "visiondt:lens:manufacturer": (Sdf.ValueTypeNames.String, "", "Manufacturer", "Vision DT Lens - Info"),
}

# Asset-type attributes handled separately
LENS_ASSET_ATTRIBUTES = {
    "visiondt:lens:mtfDataPath": ("MTF Data File Path", "Vision DT Lens - MTF"),
    "visiondt:lens:zemaxFilePath": ("Zemax Source File", "Vision DT Lens - Info"),
}


class CameraWatcher:
    """
    Watches for new camera prims and applies Vision DT lens attributes automatically.

    When a new camera is created in the stage, this watcher detects it and
    automatically adds all Vision DT lens attributes for lens profile selection.
    """

    def __init__(self):
        self._stage_listener = None
        self._stage = None
        self._enabled = False
        _log_info("CameraWatcher module initialized")

    def start(self, stage: Usd.Stage = None):
        """Start watching for new cameras."""
        if self._enabled:
            _log_info("CameraWatcher already running")
            return

        if stage is None:
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None

        if not stage:
            _log_warn("No stage available, cannot start CameraWatcher")
            return

        self._stage = stage

        # Register for notice about objects changed
        self._stage_listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            stage
        )

        self._enabled = True
        _log_info("CameraWatcher ACTIVE - new cameras will auto-receive Vision DT lens attributes")

    def stop(self):
        """Stop watching for new cameras."""
        if self._stage_listener:
            self._stage_listener.Revoke()
            self._stage_listener = None

        self._stage = None
        self._enabled = False
        _log_info("CameraWatcher stopped")

    def _on_objects_changed(self, notice, stage):
        """Called when objects in the stage change."""
        try:
            # Check for newly added prims
            for path in notice.GetChangedInfoOnlyPaths():
                prim = stage.GetPrimAtPath(path.GetPrimPath())
                if prim and prim.IsValid():
                    self._check_and_configure_camera(prim)

            # Also check resynced paths (for newly created prims)
            for path in notice.GetResyncedPaths():
                prim = stage.GetPrimAtPath(path)
                if prim and prim.IsValid():
                    self._check_and_configure_camera(prim)

        except Exception as e:
            _log_error(f"Error in _on_objects_changed: {e}")

    def _check_and_configure_camera(self, prim: Usd.Prim):
        """Check if prim is a camera and configure it if needed."""
        if not prim.IsValid():
            return

        prim_type = prim.GetTypeName()
        if prim_type != "Camera":
            return

        # Check if already has visiondt lens attributes
        if prim.HasAttribute("visiondt:lens:libraryId"):
            return  # Already configured

        # Apply Vision DT lens attributes
        self._apply_lens_attributes(prim)

    def _apply_lens_attributes(self, camera_prim: Usd.Prim):
        """Apply Vision DT lens custom attributes to a camera prim."""
        try:
            prim_path = str(camera_prim.GetPath())

            _log_info(f"NEW CAMERA DETECTED: {prim_path}")
            _log_info(f"  → Auto-applying Vision DT lens attributes...")

            created_attrs = []

            # Create standard attributes
            for attr_name, (attr_type, default_val, display_name, display_group) in LENS_ATTRIBUTES.items():
                if not camera_prim.HasAttribute(attr_name):
                    attr = camera_prim.CreateAttribute(
                        attr_name,
                        attr_type,
                        custom=True
                    )
                    if attr:
                        attr.Set(default_val)
                        attr.SetCustomDataByKey("displayName", display_name)
                        attr.SetCustomDataByKey("displayGroup", display_group)
                        created_attrs.append(attr_name.split(":")[-1])

            # Create Asset-type attributes
            for attr_name, (display_name, display_group) in LENS_ASSET_ATTRIBUTES.items():
                if not camera_prim.HasAttribute(attr_name):
                    attr = camera_prim.CreateAttribute(
                        attr_name,
                        Sdf.ValueTypeNames.Asset,
                        custom=True
                    )
                    if attr:
                        attr.Set(Sdf.AssetPath(""))
                        attr.SetCustomDataByKey("displayName", display_name)
                        attr.SetCustomDataByKey("displayGroup", display_group)
                        created_attrs.append(attr_name.split(":")[-1])

            _log_info(f"  ✓ Added {len(created_attrs)} Vision DT lens attributes")

            _log_info(f"  ✓ Set 'visiondt:lens:libraryId' to select a lens from the library")

        except Exception as e:
            _log_error(f"Failed to apply Vision DT lens attributes to {camera_prim.GetPath()}: {e}")
            import traceback
            _log_error(traceback.format_exc())


def get_watcher() -> CameraWatcher:
    """Get or create the singleton CameraWatcher instance."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = CameraWatcher()
    return _watcher_instance


def start_watching(stage: Usd.Stage = None):
    """Start the camera watcher."""
    _log_info("Starting Vision DT CameraWatcher...")
    watcher = get_watcher()
    watcher.start(stage)


def stop_watching():
    """Stop the camera watcher."""
    global _watcher_instance
    if _watcher_instance:
        _watcher_instance.stop()


def apply_to_all_cameras(stage: Usd.Stage = None):
    """
    Manually apply Vision DT lens attributes to ALL cameras in the stage.
    Useful for applying to cameras created before the watcher was started.
    """
    if stage is None:
        context = omni.usd.get_context()
        stage = context.get_stage() if context else None

    if not stage:
        _log_warn("No stage available")
        return 0

    _log_info("=" * 60)
    _log_info("Applying Vision DT lens attributes to all cameras in stage...")
    _log_info("=" * 60)

    watcher = get_watcher()
    count = 0
    already_configured = 0

    for prim in stage.Traverse():
        if prim.GetTypeName() == "Camera":
            if not prim.HasAttribute("visiondt:lens:libraryId"):
                watcher._apply_lens_attributes(prim)
                count += 1
            else:
                already_configured += 1

    _log_info("=" * 60)
    _log_info(f"Vision DT: {count} camera(s) configured, {already_configured} already had attributes")
    _log_info("=" * 60)

    return count


def list_available_lenses():
    """List available lenses from the library."""
    try:
        from lens_library import LensLibrary
        lib = LensLibrary()
        lenses = lib.list_lenses()

        _log_info("=" * 60)
        _log_info("Available Lenses in Library:")
        _log_info("=" * 60)

        if not lenses:
            _log_info("  (No lenses in library yet)")
            _log_info("  Add lenses using: lib.add_lens_from_zemax('path/to/lens.zmx')")
        else:
            for lens in lenses:
                _log_info(f"  ID: {lens['id']}")
                _log_info(f"      {lens['manufacturer']} {lens['model']}")
                _log_info(f"      Focal: {lens.get('focal_length_mm', 'N/A')}mm, f/{lens.get('f_number', 'N/A')}")
                _log_info("")

        _log_info("=" * 60)
        _log_info("To apply a lens: Set 'visiondt:lens:libraryId' attribute on camera")
        _log_info("=" * 60)

        return lenses

    except Exception as e:
        _log_error(f"Could not list lenses: {e}")
        return []

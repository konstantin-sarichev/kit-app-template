"""
Lens Sync - Automatically applies lens profile when libraryId changes.

This module subscribes to USD stage changes and detects when the
visiondt:lens:libraryId attribute is modified on cameras, then
automatically applies the lens profile.

When active, changing visiondt:lens:libraryId will:
1. Load lens data from the library
2. Apply focal length, F-stop, focus distance to camera
3. Set orthographic projection for telecentric lenses
4. Set all Vision DT lens attributes

Reference: bootstrap/documentation/ZEMAX_LENS_INTEGRATION.md
"""

import json
import logging
from pathlib import Path

import carb
import omni.usd
from pxr import Usd, UsdGeom, Sdf, Tf

logger = logging.getLogger("vision_dt.lens_sync")

# Singleton instance
_sync_instance = None

# Trigger attribute
LENS_ID_ATTR = "visiondt:lens:libraryId"


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb logger."""
    logger.info(message)
    carb.log_info(f"[Vision DT LensSync] {message}")


def _log_warn(message: str):
    """Log warning."""
    logger.warning(message)
    carb.log_warn(f"[Vision DT LensSync] {message}")


def _log_error(message: str):
    """Log error."""
    logger.error(message)
    carb.log_error(f"[Vision DT LensSync] {message}")


def get_library_path():
    """Get path to lens library."""
    # Find the library path relative to this file
    utils_dir = Path(__file__).parent
    bootstrap_dir = utils_dir.parent
    project_root = bootstrap_dir.parent

    # Try multiple locations in order of preference
    possible_paths = [
        # _build/assets location (where Omniverse runs from)
        project_root / "assets" / "Lenses" / "Library",
        # Source assets location
        Path("G:/Vision_Example_1/kit-app-template/assets/Lenses/Library"),
        Path("G:/Vision_Example_1/kit-app-template/_build/assets/Lenses/Library"),
    ]

    for path in possible_paths:
        if path.exists():
            # Verify it has lens_library.json
            if (path / "lens_library.json").exists():
                _log_info(f"Using lens library: {path}")
                return path

    _log_error("Could not find lens library in any location")
    return None


def load_lens_data(lens_id: str):
    """Load lens data from library."""
    library_path = get_library_path()
    if not library_path:
        _log_error("Lens library path not found")
        return None

    # Load library index
    index_path = library_path / "lens_library.json"
    if not index_path.exists():
        _log_error(f"Lens library index not found: {index_path}")
        return None

    try:
        with open(index_path, 'r') as f:
            index = json.load(f)

        # Find lens in index
        lens_entry = None
        for lens in index.get("lenses", []):
            if lens.get("id") == lens_id:
                lens_entry = lens
                break

        if not lens_entry:
            _log_warn(f"Lens not found in library: {lens_id}")
            return None

        # Load lens data file
        data_path = library_path / lens_entry.get("data_path", "")
        if not data_path.exists():
            _log_error(f"Lens data file not found: {data_path}")
            return None

        with open(data_path, 'r') as f:
            return json.load(f)

    except Exception as e:
        _log_error(f"Failed to load lens data: {e}")
        return None


class LensSync:
    """
    Watches for changes to visiondt:lens:libraryId and auto-applies lens profiles.
    """

    def __init__(self):
        self._listener = None
        self._stage = None
        self._enabled = False
        _log_info("LensSync module initialized")

    def start(self, stage: Usd.Stage = None):
        """Start watching for lens ID changes."""
        if self._enabled:
            _log_info("LensSync already running")
            return

        if stage is None:
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None

        if not stage:
            _log_warn("No stage available, cannot start LensSync")
            return

        self._stage = stage

        # Register for notice about objects changed
        self._listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            stage
        )

        self._enabled = True
        _log_info("★ LensSync ACTIVE - changing libraryId will auto-apply lens profile")

    def stop(self):
        """Stop watching."""
        if self._listener:
            self._listener.Revoke()
            self._listener = None

        self._stage = None
        self._enabled = False
        _log_info("LensSync stopped")

    def _on_objects_changed(self, notice, stage):
        """Called when objects in the stage change."""
        try:
            # Check changed paths for our trigger attribute
            for path in notice.GetChangedInfoOnlyPaths():
                path_str = str(path)
                if LENS_ID_ATTR in path_str:
                    prim_path = path.GetPrimPath()
                    prim = stage.GetPrimAtPath(prim_path)
                    if prim and prim.GetTypeName() == "Camera":
                        self._apply_lens_from_attr(prim)

            # Also check resynced paths
            for path in notice.GetResyncedPaths():
                prim = stage.GetPrimAtPath(path)
                if prim and prim.GetTypeName() == "Camera":
                    if prim.HasAttribute(LENS_ID_ATTR):
                        lens_id = prim.GetAttribute(LENS_ID_ATTR).Get()
                        if lens_id:
                            self._apply_lens_from_attr(prim)

        except Exception as e:
            _log_error(f"Error in _on_objects_changed: {e}")

    def _apply_lens_from_attr(self, camera_prim: Usd.Prim):
        """Apply lens profile based on libraryId attribute."""
        lens_id_attr = camera_prim.GetAttribute(LENS_ID_ATTR)
        if not lens_id_attr:
            return

        lens_id = lens_id_attr.Get()
        if not lens_id or lens_id == "":
            return

        camera_path = str(camera_prim.GetPath())
        _log_info("=" * 50)
        _log_info(f"★ Lens ID changed on {camera_path}")
        _log_info(f"  Applying lens: {lens_id}")
        _log_info("=" * 50)
        # Also log as warning so it's visible in default console output
        carb.log_warn(f"[Vision DT LensSync] ★ Applying lens '{lens_id}' to {camera_path}")

        # Load lens data
        lens_data = load_lens_data(lens_id)
        if not lens_data:
            _log_error(f"  ✗ Could not load lens: {lens_id}")
            return

        # Apply lens profile
        self._apply_lens_profile(camera_prim, lens_data, lens_id)

    def _apply_lens_profile(self, camera_prim: Usd.Prim, lens_data: dict, lens_id: str):
        """Apply lens profile to camera."""
        try:
            camera = UsdGeom.Camera(camera_prim)

            # Get data sections
            metadata = lens_data.get("metadata", {})
            optical = lens_data.get("optical", {})
            distortion = lens_data.get("distortion", {})
            mtf = lens_data.get("mtf", {})

            model = metadata.get("model", lens_id)
            manufacturer = metadata.get("manufacturer", "Unknown")

            _log_info(f"  Lens: {manufacturer} {model}")

            # ============================================================
            # APPLY CORE OMNIVERSE CAMERA SETTINGS
            # ============================================================

            # Focal Length
            focal_length = optical.get("focal_length_mm", 0)
            if focal_length > 0:
                camera.GetFocalLengthAttr().Set(focal_length)
                _log_info(f"  ✓ Focal Length: {focal_length}mm")

            # F-Stop
            f_number = optical.get("f_number", 0)
            if f_number > 0:
                camera.GetFStopAttr().Set(f_number)
                _log_info(f"  ✓ F-Stop: f/{f_number}")

            # Focus Distance (Working Distance)
            working_distance = optical.get("working_distance_mm", 0)
            if working_distance > 0:
                camera.GetFocusDistanceAttr().Set(working_distance)
                _log_info(f"  ✓ Focus Distance: {working_distance}mm")

            # ============================================================
            # TELECENTRIC PROJECTION
            # ============================================================

            is_telecentric = optical.get("is_telecentric", False)
            telecentric_type = optical.get("telecentric_type", "")

            if is_telecentric:
                _log_info("  ★ TELECENTRIC LENS DETECTED")

                # Set projection to orthographic
                projection_attr = camera.GetProjectionAttr()
                if projection_attr:
                    projection_attr.Set(UsdGeom.Tokens.orthographic)
                    _log_info(f"  ✓ Projection: ORTHOGRAPHIC")

                # Set horizontal aperture based on magnification
                magnification = optical.get("magnification", 1.0)
                if magnification > 0:
                    # Calculate sensor coverage (assuming 1/2" sensor reference)
                    sensor_width = 6.4 / magnification
                    camera.GetHorizontalApertureAttr().Set(sensor_width)
                    _log_info(f"  ✓ Magnification: {magnification}x")
                    _log_info(f"  ✓ Horizontal Aperture: {sensor_width:.2f}mm")
            else:
                # Standard perspective projection
                projection_attr = camera.GetProjectionAttr()
                if projection_attr:
                    projection_attr.Set(UsdGeom.Tokens.perspective)
                    _log_info(f"  ✓ Projection: PERSPECTIVE")

            # ============================================================
            # SET VISION DT LENS ATTRIBUTES
            # ============================================================

            # Profile identification
            self._set_attr(camera_prim, "visiondt:lens:profileName", Sdf.ValueTypeNames.String, f"{manufacturer} {model}")

            # Optical parameters
            self._set_attr(camera_prim, "visiondt:lens:focalLengthMm", Sdf.ValueTypeNames.Float, focal_length)
            self._set_attr(camera_prim, "visiondt:lens:workingDistanceMm", Sdf.ValueTypeNames.Float, working_distance)
            self._set_attr(camera_prim, "visiondt:lens:fNumber", Sdf.ValueTypeNames.Float, f_number)
            self._set_attr(camera_prim, "visiondt:lens:fieldOfViewDeg", Sdf.ValueTypeNames.Float, optical.get("field_of_view_deg", 0))
            self._set_attr(camera_prim, "visiondt:lens:magnification", Sdf.ValueTypeNames.Float, optical.get("magnification", 0))
            self._set_attr(camera_prim, "visiondt:lens:numericalAperture", Sdf.ValueTypeNames.Float, optical.get("numerical_aperture", 0))
            self._set_attr(camera_prim, "visiondt:lens:isTelecentric", Sdf.ValueTypeNames.Bool, is_telecentric)
            self._set_attr(camera_prim, "visiondt:lens:telecentricType", Sdf.ValueTypeNames.String, telecentric_type)

            # Distortion
            self._set_attr(camera_prim, "visiondt:lens:distortionModel", Sdf.ValueTypeNames.String, distortion.get("model", "brown-conrady"))
            self._set_attr(camera_prim, "visiondt:lens:k1", Sdf.ValueTypeNames.Float, distortion.get("k1", 0))
            self._set_attr(camera_prim, "visiondt:lens:k2", Sdf.ValueTypeNames.Float, distortion.get("k2", 0))
            self._set_attr(camera_prim, "visiondt:lens:k3", Sdf.ValueTypeNames.Float, distortion.get("k3", 0))
            self._set_attr(camera_prim, "visiondt:lens:p1", Sdf.ValueTypeNames.Float, distortion.get("p1", 0))
            self._set_attr(camera_prim, "visiondt:lens:p2", Sdf.ValueTypeNames.Float, distortion.get("p2", 0))

            # MTF
            self._set_attr(camera_prim, "visiondt:lens:mtfAt50lpmm", Sdf.ValueTypeNames.Float, mtf.get("mtf_at_50lpmm", 0))
            self._set_attr(camera_prim, "visiondt:lens:mtfAt100lpmm", Sdf.ValueTypeNames.Float, mtf.get("mtf_at_100lpmm", 0))

            # Metadata
            self._set_attr(camera_prim, "visiondt:lens:model", Sdf.ValueTypeNames.String, model)
            self._set_attr(camera_prim, "visiondt:lens:manufacturer", Sdf.ValueTypeNames.String, manufacturer)

            # ============================================================
            # APPLY DISTORTION (if non-zero)
            # ============================================================

            k1 = distortion.get("k1", 0)
            k2 = distortion.get("k2", 0)

            if k1 != 0 or k2 != 0:
                try:
                    camera_prim.ApplyAPI("OmniLensDistortionOpenCvPinholeAPI")
                    self._set_attr(camera_prim, "lensDistortion:k1", Sdf.ValueTypeNames.Float, k1)
                    self._set_attr(camera_prim, "lensDistortion:k2", Sdf.ValueTypeNames.Float, k2)
                    self._set_attr(camera_prim, "lensDistortion:k3", Sdf.ValueTypeNames.Float, distortion.get("k3", 0))
                    self._set_attr(camera_prim, "lensDistortion:p1", Sdf.ValueTypeNames.Float, distortion.get("p1", 0))
                    self._set_attr(camera_prim, "lensDistortion:p2", Sdf.ValueTypeNames.Float, distortion.get("p2", 0))
                    _log_info(f"  ✓ Distortion applied: k1={k1:.4f}")
                except Exception as e:
                    _log_warn(f"  ! Distortion API not available: {e}")

            _log_info("=" * 50)
            _log_info(f"✓ LENS APPLIED: {lens_id}")
            _log_info("=" * 50)
            # Also log as warning so it's visible in default console output
            carb.log_warn(f"[Vision DT LensSync] ✓ LENS APPLIED: {lens_id} - Camera updated with {manufacturer} {model}")

        except Exception as e:
            _log_error(f"Failed to apply lens profile: {e}")
            import traceback
            traceback.print_exc()

    def _set_attr(self, prim, attr_name, attr_type, value):
        """Set or create an attribute."""
        try:
            attr = prim.GetAttribute(attr_name)
            if not attr:
                attr = prim.CreateAttribute(attr_name, attr_type, custom=True)
                attr.SetCustomDataByKey("displayGroup", "Vision DT Lens")
            if attr:
                attr.Set(value)
        except Exception as e:
            pass  # Silently ignore errors for individual attributes


def get_sync() -> LensSync:
    """Get or create the singleton LensSync instance."""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = LensSync()
    return _sync_instance


def start_lens_sync(stage: Usd.Stage = None):
    """Start the lens sync watcher."""
    _log_info("Starting Vision DT LensSync...")
    sync = get_sync()
    sync.start(stage)


def stop_lens_sync():
    """Stop the lens sync watcher."""
    global _sync_instance
    if _sync_instance:
        _sync_instance.stop()


def sync_all_cameras(stage: Usd.Stage = None):
    """Manually sync all cameras with lens IDs set."""
    if stage is None:
        context = omni.usd.get_context()
        stage = context.get_stage() if context else None

    if not stage:
        _log_warn("No stage available")
        return 0

    sync = get_sync()
    count = 0

    for prim in stage.Traverse():
        if prim.GetTypeName() == "Camera":
            lens_id_attr = prim.GetAttribute(LENS_ID_ATTR)
            if lens_id_attr:
                lens_id = lens_id_attr.Get()
                if lens_id and lens_id != "":
                    sync._apply_lens_from_attr(prim)
                    count += 1

    return count

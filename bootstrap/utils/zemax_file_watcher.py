"""
Zemax File Watcher - Automatically imports .ZAR files and applies to cameras.

This module monitors the ZeMax directory for new .ZAR files and automatically:
1. Imports the Zemax file into the lens library
2. Applies lens parameters to all cameras in the stage
3. Sets telecentric projection if the lens is telecentric

The watcher runs periodically and processes any new .ZAR files found.
"""

import logging
import carb
import omni.usd
import omni.kit.app
from pathlib import Path
from typing import Set, Optional, Dict
from pxr import Usd, UsdGeom, Sdf
import sys
import time

logger = logging.getLogger("vision_dt.zemax_watcher")

# Singleton watcher instance
_watcher_instance = None

# Track processed files to avoid re-processing
_processed_files: Set[str] = set()

# Track the last imported lens ID for auto-applying to new cameras
_last_imported_lens_id: Optional[str] = None


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb logger."""
    logger.info(message)
    carb.log_info(f"[Vision DT ZemaxWatcher] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb logger."""
    logger.warning(message)
    carb.log_warn(f"[Vision DT ZemaxWatcher] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb logger."""
    logger.error(message)
    carb.log_error(f"[Vision DT ZemaxWatcher] {message}")


class ZemaxFileWatcher:
    """
    Watches for new .ZAR files in the ZeMax directory and automatically imports them.

    When a new .ZAR file is detected:
    1. Imports it into the lens library
    2. Applies lens parameters to all cameras
    3. Sets telecentric projection if applicable
    """

    def __init__(self):
        self._enabled = False
        self._subscription = None
        self._zemax_dir: Optional[Path] = None
        self._last_check_time = 0.0
        self._check_interval = 2.0  # Check every 2 seconds
        _log_info("ZemaxFileWatcher module initialized")

    def _get_zemax_directory(self) -> Optional[Path]:
        """Get the ZeMax directory path."""
        try:
            # Try to find project root
            bootstrap_dir = Path(__file__).parent.parent
            build_root = bootstrap_dir.parent
            project_root = build_root.parent if build_root.name == "_build" else build_root

            # Check both live project assets and legacy _build assets directories
            possible_paths = [
                project_root / "assets" / "Lenses" / "ZeMax",
                build_root / "assets" / "Lenses" / "ZeMax",
            ]

            _log_info(f"Searching for ZeMax directory...")
            _log_info(f"  Bootstrap dir: {bootstrap_dir}")
            _log_info(f"  Build root: {build_root}")
            _log_info(f"  Project root: {project_root}")

            for path in possible_paths:
                _log_info(f"  Checking: {path} (exists: {path.exists()})")
                if path.exists():
                    return path

            # If directory doesn't exist, try to create it
            target_path = project_root / "assets" / "Lenses" / "ZeMax"
            _log_info(f"Creating default ZeMax directory: {target_path}")
            target_path.mkdir(parents=True, exist_ok=True)
            return target_path

        except Exception as e:
            _log_error(f"Failed to determine ZeMax directory: {e}")
            return None

    def start(self):
        """Start watching for new .ZAR files."""
        if self._enabled:
            _log_info("ZemaxFileWatcher already running")
            return

        self._zemax_dir = self._get_zemax_directory()
        if not self._zemax_dir:
            _log_error("Cannot start watcher - ZeMax directory not found")
            return

        _log_info(f"Monitoring ZeMax directory: {self._zemax_dir}")

        # Subscribe to update stream for periodic checking
        # Use create_subscription_to_pop (the correct API method)
        try:
            self._subscription = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(
                self._on_update,
                name="zemax_file_watcher"
            )
            _log_info("Subscribed using create_subscription_to_pop")
        except Exception as e:
            _log_warn(f"create_subscription_to_pop failed: {e}, trying alternative method...")
            try:
                # Try alternative: using carb.events directly
                import carb.events
                self._subscription = carb.events.acquire_events_interface().create_subscription_to_pop(
                    omni.kit.app.get_app().get_update_event_stream(),
                    self._on_update,
                    name="zemax_file_watcher"
                )
                _log_info("Subscribed using carb.events interface")
            except Exception as e2:
                _log_error(f"All subscription methods failed: {e2}")
                _log_info("Falling back to manual polling mode - run force_check() to process files")
                # We'll still enable but rely on manual checks
                pass

        self._enabled = True
        self._last_check_time = time.time()
        _log_info("ZemaxFileWatcher ACTIVE - monitoring for new .ZAR files")

        # Do an initial check
        self._check_for_new_files()

    def stop(self):
        """Stop watching for new files."""
        if not self._enabled:
            return

        if self._subscription:
            self._subscription = None

        self._enabled = False
        _log_info("ZemaxFileWatcher stopped")

    def _on_update(self, event):
        """Called on each frame update to check for new files."""
        if not self._enabled:
            return

        current_time = time.time()
        if current_time - self._last_check_time >= self._check_interval:
            self._last_check_time = current_time
            self._check_for_new_files()

    def _check_for_new_files(self):
        """Check for new .ZAR files and process them."""
        if not self._zemax_dir or not self._zemax_dir.exists():
            return

        try:
            # Find all .ZAR and .zar files
            zar_files = list(self._zemax_dir.glob("*.ZAR")) + list(self._zemax_dir.glob("*.zar"))

            if zar_files:
                _log_info(f"Found {len(zar_files)} .ZAR file(s) in {self._zemax_dir}")

            for zar_file in zar_files:
                file_path_str = str(zar_file.absolute())

                # Skip if already processed
                if file_path_str in _processed_files:
                    continue

                # Check if file is fully written (not being copied)
                try:
                    # Get file size
                    size1 = zar_file.stat().st_size
                    time.sleep(0.1)  # Wait a bit
                    size2 = zar_file.stat().st_size

                    # If file size changed, it's still being written
                    if size1 != size2:
                        _log_info(f"File {zar_file.name} still being written, skipping for now...")
                        continue
                except Exception:
                    continue

                # Process the file
                _log_info(f"New .ZAR file detected: {zar_file.name}")
                self._process_zar_file(zar_file)

                # Mark as processed
                _processed_files.add(file_path_str)

        except Exception as e:
            _log_error(f"Error checking for new files: {e}")

    def _process_zar_file(self, zar_file: Path):
        """
        Process a .ZAR file: import it and apply to cameras.

        Args:
            zar_file: Path to the .ZAR file
        """
        try:
            _log_info("=" * 60)
            _log_info(f"Processing .ZAR file: {zar_file.name}")
            _log_info(f"Full path: {zar_file}")
            _log_info(f"File size: {zar_file.stat().st_size:,} bytes")
            _log_info("=" * 60)

            # Import lens library
            try:
                from utils.lens_library import LensLibrary
                _log_info("Successfully imported LensLibrary from utils.lens_library")
            except ImportError as ie1:
                _log_warn(f"Could not import from utils.lens_library: {ie1}")
                try:
                    # Add bootstrap to path if needed
                    bootstrap_dir = Path(__file__).parent.parent
                    if str(bootstrap_dir) not in sys.path:
                        sys.path.insert(0, str(bootstrap_dir))
                        _log_info(f"Added {bootstrap_dir} to sys.path")
                    from utils.lens_library import LensLibrary
                    _log_info("Successfully imported LensLibrary after path modification")
                except ImportError as ie2:
                    _log_error(f"Failed to import LensLibrary: {ie2}")
                    return

            # Create library instance
            _log_info("Creating LensLibrary instance...")
            lib = LensLibrary()
            _log_info(f"LensLibrary path: {lib.library_path}")

            # Import the .ZAR file
            _log_info(f"Calling add_lens_from_zemax...")
            success, result = lib.add_lens_from_zemax(
                str(zar_file),
                overwrite=True  # Allow overwriting if lens already exists
            )

            if not success:
                _log_error(f"Failed to import .ZAR file: {result}")
                return

            lens_id = result
            _log_info(f"✓ Successfully imported lens: {lens_id}")

            # Save as last imported lens for auto-applying to new cameras
            global _last_imported_lens_id
            _last_imported_lens_id = lens_id
            carb.log_warn(f"[Vision DT ZemaxWatcher] ★ NEW LENS AVAILABLE: {lens_id}")
            carb.log_warn(f"[Vision DT ZemaxWatcher]   Set camera's visiondt:lens:libraryId = '{lens_id}' to apply")

            # Load lens data for logging (no auto-apply)
            _log_info(f"Loading lens data (no auto-apply)...")
            lens_data = lib.get_lens_for_camera(lens_id)
            if not lens_data:
                _log_error(f"Failed to load lens data for {lens_id}")
                return

            # Log extracted lens data
            _log_info("Extracted lens parameters:")
            _log_info(f"  Model: {lens_data.get('model', 'Unknown')}")
            _log_info(f"  Manufacturer: {lens_data.get('manufacturer', 'Unknown')}")
            _log_info(f"  Focal Length: {lens_data.get('focal_length_mm', 0)} mm")
            _log_info(f"  F-Number: f/{lens_data.get('f_number', 0)}")
            _log_info(f"  Working Distance: {lens_data.get('working_distance_mm', 0)} mm")
            _log_info(f"  FOV: {lens_data.get('field_of_view_deg', 0)} deg")
            _log_info(f"  Magnification: {lens_data.get('magnification', 0)}x")
            _log_info(f"  Telecentric: {lens_data.get('is_telecentric', False)}")
            _log_info(f"  NA: {lens_data.get('numerical_aperture', 0)}")

            # Do NOT auto-apply. User selects lens via visiondt:lens:libraryId.
            _log_info("Lens saved to library. Set visiondt:lens:libraryId on a camera to apply.")

            _log_info("=" * 60)
            _log_info(f"✓ Completed processing: {zar_file.name}")
            _log_info("=" * 60)

        except Exception as e:
            _log_error(f"Error processing .ZAR file: {e}")
            import traceback
            _log_error(f"Traceback:\n{traceback.format_exc()}")

    def _apply_lens_to_all_cameras(self, lens_id: str, lens_data: Dict):
        """
        Apply lens parameters to all cameras in the stage.

        Args:
            lens_id: Lens library ID
            lens_data: Lens data dictionary
        """
        try:
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None

            if not stage:
                _log_warn("No stage available, cannot apply lens to cameras")
                return

            # Find all cameras
            cameras = []
            for prim in stage.Traverse():
                if prim.GetTypeName() == "Camera":
                    cameras.append(prim)

            if not cameras:
                _log_info("No cameras found in stage")
                return

            _log_info(f"Found {len(cameras)} camera(s) - applying lens parameters...")

            # Apply lens to each camera
            for camera_prim in cameras:
                camera_path = str(camera_prim.GetPath())
                _log_info(f"  Applying lens to camera: {camera_path}")

                try:
                    self._apply_lens_to_camera(camera_prim, lens_id, lens_data)
                    _log_info(f"  ✓ Applied lens to {camera_path}")
                except Exception as e:
                    _log_error(f"  ✗ Failed to apply lens to {camera_path}: {e}")

        except Exception as e:
            _log_error(f"Error applying lens to cameras: {e}")
            import traceback
            _log_error(f"Traceback:\n{traceback.format_exc()}")

    def _apply_lens_to_camera(self, camera_prim: Usd.Prim, lens_id: str, lens_data: Dict):
        """
        Apply lens parameters to a single camera.

        Args:
            camera_prim: Camera prim to apply lens to
            lens_id: Lens library ID
            lens_data: Lens data dictionary
        """
        try:
            camera = UsdGeom.Camera(camera_prim)

            # Set lens library ID
            self._set_or_create_attr(
                camera_prim,
                "visiondt:lens:libraryId",
                Sdf.ValueTypeNames.String,
                lens_id
            )

            # Apply core optical parameters
            focal_length = lens_data.get("focal_length_mm", 0)
            if focal_length > 0:
                camera.GetFocalLengthAttr().Set(focal_length)
                _log_info(f"    → Focal length: {focal_length}mm")

            f_number = lens_data.get("f_number", 0)
            if f_number > 0:
                camera.GetFStopAttr().Set(f_number)
                _log_info(f"    → F-stop: f/{f_number}")

            working_distance = lens_data.get("working_distance_mm", 0)
            if working_distance > 0:
                camera.GetFocusDistanceAttr().Set(working_distance)
                _log_info(f"    → Focus distance: {working_distance}mm")

            # Check if telecentric
            is_telecentric = lens_data.get("is_telecentric", False)
            telecentric_type = lens_data.get("telecentric_type", "")

            if is_telecentric:
                _log_info(f"    → Telecentric lens detected ({telecentric_type})")

                # Set projection to orthographic
                projection_attr = camera.GetProjectionAttr()
                if projection_attr:
                    projection_attr.Set(UsdGeom.Tokens.orthographic)
                    _log_info(f"    → Projection set to ORTHOGRAPHIC")

                # Set telecentric attributes
                self._set_or_create_attr(
                    camera_prim,
                    "visiondt:lens:isTelecentric",
                    Sdf.ValueTypeNames.Bool,
                    True
                )
                self._set_or_create_attr(
                    camera_prim,
                    "visiondt:lens:telecentricType",
                    Sdf.ValueTypeNames.String,
                    telecentric_type
                )

                # Set magnification-based aperture for telecentric
                magnification = lens_data.get("magnification", 1.0)
                if magnification > 0:
                    # Calculate object-space FOV based on magnification
                    # Assuming 1/2" sensor (6.4mm x 4.8mm) as reference
                    sensor_width = 6.4 / magnification
                    camera.GetHorizontalApertureAttr().Set(sensor_width)
                    _log_info(f"    → Magnification: {magnification}x")
                    _log_info(f"    → Horizontal aperture: {sensor_width:.2f}mm")
            else:
                # Standard perspective projection
                projection_attr = camera.GetProjectionAttr()
                if projection_attr:
                    projection_attr.Set(UsdGeom.Tokens.perspective)
                    _log_info(f"    → Projection set to PERSPECTIVE")

            # Set all Vision DT lens attributes
            self._set_or_create_attr(
                camera_prim,
                "visiondt:lens:profileName",
                Sdf.ValueTypeNames.String,
                f"{lens_data.get('manufacturer', '')} {lens_data.get('model', '')}".strip()
            )

            # Set optical parameters
            for attr_name, data_key, attr_type in [
                ("visiondt:lens:focalLengthMm", "focal_length_mm", Sdf.ValueTypeNames.Float),
                ("visiondt:lens:workingDistanceMm", "working_distance_mm", Sdf.ValueTypeNames.Float),
                ("visiondt:lens:fNumber", "f_number", Sdf.ValueTypeNames.Float),
                ("visiondt:lens:fieldOfViewDeg", "field_of_view_deg", Sdf.ValueTypeNames.Float),
                ("visiondt:lens:magnification", "magnification", Sdf.ValueTypeNames.Float),
                ("visiondt:lens:numericalAperture", "numerical_aperture", Sdf.ValueTypeNames.Float),
            ]:
                value = lens_data.get(data_key)
                if value is not None:
                    self._set_or_create_attr(camera_prim, attr_name, attr_type, value)

            # Set distortion coefficients
            for attr_name, data_key in [
                ("visiondt:lens:k1", "k1"),
                ("visiondt:lens:k2", "k2"),
                ("visiondt:lens:k3", "k3"),
                ("visiondt:lens:p1", "p1"),
                ("visiondt:lens:p2", "p2"),
            ]:
                value = lens_data.get(data_key, 0)
                if value != 0:  # Only set non-zero distortion
                    self._set_or_create_attr(
                        camera_prim,
                        attr_name,
                        Sdf.ValueTypeNames.Float,
                        value
                    )

            # Set MTF values
            for attr_name, data_key in [
                ("visiondt:lens:mtfAt50lpmm", "mtf_at_50lpmm"),
                ("visiondt:lens:mtfAt100lpmm", "mtf_at_100lpmm"),
            ]:
                value = lens_data.get(data_key, 0)
                if value > 0:
                    self._set_or_create_attr(
                        camera_prim,
                        attr_name,
                        Sdf.ValueTypeNames.Float,
                        value
                    )

            # Set metadata
            self._set_or_create_attr(
                camera_prim,
                "visiondt:lens:model",
                Sdf.ValueTypeNames.String,
                lens_data.get("model", "")
            )
            self._set_or_create_attr(
                camera_prim,
                "visiondt:lens:manufacturer",
                Sdf.ValueTypeNames.String,
                lens_data.get("manufacturer", "")
            )

            # Apply distortion API if coefficients are non-zero
            k1 = lens_data.get("k1", 0)
            k2 = lens_data.get("k2", 0)
            k3 = lens_data.get("k3", 0)
            p1 = lens_data.get("p1", 0)
            p2 = lens_data.get("p2", 0)

            if k1 != 0 or k2 != 0 or k3 != 0 or p1 != 0 or p2 != 0:
                try:
                    camera_prim.ApplyAPI("OmniLensDistortionOpenCvPinholeAPI")
                    self._set_or_create_attr(
                        camera_prim,
                        "lensDistortion:k1",
                        Sdf.ValueTypeNames.Float,
                        k1
                    )
                    self._set_or_create_attr(
                        camera_prim,
                        "lensDistortion:k2",
                        Sdf.ValueTypeNames.Float,
                        k2
                    )
                    self._set_or_create_attr(
                        camera_prim,
                        "lensDistortion:k3",
                        Sdf.ValueTypeNames.Float,
                        k3
                    )
                    self._set_or_create_attr(
                        camera_prim,
                        "lensDistortion:p1",
                        Sdf.ValueTypeNames.Float,
                        p1
                    )
                    self._set_or_create_attr(
                        camera_prim,
                        "lensDistortion:p2",
                        Sdf.ValueTypeNames.Float,
                        p2
                    )
                    _log_info(f"    → Applied lens distortion")
                except Exception as e:
                    _log_warn(f"    → Could not apply distortion API: {e}")

        except Exception as e:
            _log_error(f"Error applying lens to camera: {e}")
            raise

    def _set_or_create_attr(self, prim: Usd.Prim, attr_name: str, attr_type, value):
        """Set or create an attribute."""
        try:
            attr = prim.GetAttribute(attr_name)
            if not attr:
                attr = prim.CreateAttribute(attr_name, attr_type, custom=True)
                attr.SetCustomDataByKey("displayGroup", "Vision DT Lens")
            if attr:
                attr.Set(value)
        except Exception as e:
            _log_warn(f"Could not set {attr_name}: {e}")


# Singleton management functions
def start_watching():
    """Start the Zemax file watcher."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = ZemaxFileWatcher()
    _watcher_instance.start()


def stop_watching():
    """Stop the Zemax file watcher."""
    global _watcher_instance
    if _watcher_instance:
        _watcher_instance.stop()


def reset_processed_files():
    """Reset the list of processed files (for testing)."""
    global _processed_files
    _processed_files.clear()
    _log_info("Reset processed files list")


def force_process_file(zar_path: str):
    """Force processing of a specific .ZAR file (for testing)."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = ZemaxFileWatcher()

    zar_file = Path(zar_path)
    if zar_file.exists():
        _log_info(f"Force processing: {zar_file}")
        _watcher_instance._process_zar_file(zar_file)
    else:
        _log_error(f"File not found: {zar_path}")


def import_zemax_file(file_path: str) -> tuple:
    """
    Import a Zemax file (.ZMX or .ZAR) into the lens library.

    This is the recommended function to call for manual imports from
    menus, dialogs, or Script Editor.

    Args:
        file_path: Full path to the Zemax file

    Returns:
        Tuple of (success: bool, result: str)
        On success, result is the lens ID
        On failure, result is the error message

    Example usage in Script Editor:
        from utils.zemax_file_watcher import import_zemax_file
        success, result = import_zemax_file(r"C:\\path\\to\\lens.ZAR")
        if success:
            print(f"Imported lens ID: {result}")
            print(f"Set visiondt:lens:libraryId = '{result}' on your camera")
        else:
            print(f"Import failed: {result}")
    """
    _log_info("=" * 60)
    _log_info(f"Manual Zemax import: {file_path}")
    _log_info("=" * 60)

    zemax_file = Path(file_path)
    if not zemax_file.exists():
        error_msg = f"File not found: {file_path}"
        _log_error(error_msg)
        return (False, error_msg)

    suffix = zemax_file.suffix.lower()
    if suffix not in ['.zmx', '.zar']:
        error_msg = f"Unsupported file type: {suffix} (expected .zmx or .zar)"
        _log_error(error_msg)
        return (False, error_msg)

    try:
        # Import using lens library
        from utils.lens_library import LensLibrary
        lib = LensLibrary()
        success, result = lib.add_lens_from_zemax(str(zemax_file), overwrite=True)

        if success:
            _log_info("=" * 60)
            carb.log_warn(f"[Vision DT] ★ LENS IMPORTED: {result}")
            carb.log_warn(f"[Vision DT]   Set camera's visiondt:lens:libraryId = '{result}'")
            _log_info("=" * 60)
        else:
            _log_error(f"Import failed: {result}")

        return (success, result)

    except Exception as e:
        error_msg = f"Import error: {e}"
        _log_error(error_msg)
        import traceback
        _log_error(f"Traceback:\n{traceback.format_exc()}")
        return (False, error_msg)


def force_check():
    """
    Manually trigger a check for new .ZAR files.

    Call this from the Script Editor if automatic polling isn't working:

    ```python
    from utils.zemax_file_watcher import force_check
    force_check()
    ```
    """
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = ZemaxFileWatcher()
        _watcher_instance._zemax_dir = _watcher_instance._get_zemax_directory()

    if _watcher_instance._zemax_dir:
        _log_info("Manual check triggered for .ZAR files...")
        _watcher_instance._check_for_new_files()
    else:
        _log_error("ZeMax directory not found")


def get_last_imported_lens_id() -> Optional[str]:
    """
    Get the ID of the most recently imported lens.

    Used by camera_watcher to auto-assign new cameras to the latest lens.

    Returns:
        Lens ID string, or None if no lens has been imported this session.
    """
    return _last_imported_lens_id


def set_last_imported_lens_id(lens_id: str):
    """
    Manually set the last imported lens ID.

    Useful for testing or to reset the default lens for new cameras.

    Args:
        lens_id: The lens library ID to use for new cameras.
    """
    global _last_imported_lens_id
    _last_imported_lens_id = lens_id
    _log_info(f"Set default lens for new cameras: {lens_id}")

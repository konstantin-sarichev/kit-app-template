"""
Bootstrap Loader for Industrial Dynamics Vision Digital Twin

This module discovers and executes all capability modules in the bootstrap/capabilities
directory. Capabilities are run in numeric order based on their filename prefix
(e.g., 00_, 10_, 20_...) to ensure deterministic initialization.

The loader provides status reporting and error handling for each capability,
ensuring transparent feedback on the initialization process.
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any

import carb
import omni.usd


class BootstrapLoader:
    """
    Bootstrap loader that discovers and executes capability modules.

    This class manages the initialization of the Vision Digital Twin environment
    by loading and executing all capability modules found in the capabilities directory.
    Each capability is executed in order, with success/failure status tracked and reported.
    """

    def __init__(self, capabilities_dir: Path = None):
        """
        Initialize the bootstrap loader.

        Args:
            capabilities_dir: Path to the capabilities directory. If None, uses default location.
        """
        self.logger = logging.getLogger("vision_dt.bootstrap")
        self.logger.setLevel(logging.INFO)

        # Determine capabilities directory
        if capabilities_dir is None:
            # Get the directory where this file is located
            bootstrap_dir = Path(__file__).parent
            self.capabilities_dir = bootstrap_dir / "capabilities"
        else:
            self.capabilities_dir = Path(capabilities_dir)

        self.capabilities_dir.mkdir(parents=True, exist_ok=True)

        # Track loaded capabilities
        self.loaded_capabilities: List[Tuple[str, bool, str]] = []

    def discover_capabilities(self) -> List[Path]:
        """
        Discover all capability modules in the capabilities directory.

        Returns:
            List of capability file paths sorted by filename (numeric order)
        """
        if not self.capabilities_dir.exists():
            self.logger.warning(f"Capabilities directory does not exist: {self.capabilities_dir}")
            return []

        # DEBUG: Log directory content
        try:
            all_files_debug = list(self.capabilities_dir.glob("*"))
            self.logger.info(f"DEBUG: Scanning directory: {self.capabilities_dir}")
            self.logger.info(f"DEBUG: Found {len(all_files_debug)} items: {[f.name for f in all_files_debug]}")
        except Exception as e:
            self.logger.error(f"DEBUG: Failed to list directory: {e}")

        # Find all Python files that are not __init__.py or __pycache__
        capability_files = [
            f for f in self.capabilities_dir.glob("*.py")
            if f.name != "__init__.py" and not f.name.startswith("_")
        ]

        # Logging for debug purposes
        if not capability_files:
             self.logger.warning(f"No valid capability files found in {self.capabilities_dir}")

             # Detailed debug of directory
             if not self.capabilities_dir.exists():
                 self.logger.warning(f"Directory does not exist: {self.capabilities_dir}")
             else:
                 self.logger.warning("Directory exists. Contents:")
                 all_files = list(self.capabilities_dir.glob("*"))
                 if not all_files:
                     self.logger.warning("  <empty directory>")
                 for f in all_files:
                     self.logger.warning(f"  - {f.name} (File? {f.is_file()})")

             self.logger.warning("Check if files start with '_' (disabled) or are missing")

        # Sort by filename to ensure numeric ordering
        capability_files.sort(key=lambda x: x.name)

        return capability_files

    def load_capability_module(self, capability_path: Path) -> Any:
        """
        Load a capability module from a file path.

        Args:
            capability_path: Path to the capability Python file

        Returns:
            Loaded module object or None if loading failed
        """
        module_name = f"vision_dt.capabilities.{capability_path.stem}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, capability_path)
            if spec is None or spec.loader is None:
                self.logger.error(f"Failed to load spec for {capability_path.name}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            return module

        except Exception as e:
            self.logger.error(f"Error loading capability {capability_path.name}: {e}")
            return None

    def execute_capability(self, module: Any, capability_name: str) -> Tuple[bool, str]:
        """
        Execute a capability module's run() function.

        Args:
            module: The loaded capability module
            capability_name: Name of the capability for logging

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            # Check if module has required attributes
            if not hasattr(module, "CAPABILITY_NAME"):
                return False, "Missing CAPABILITY_NAME attribute"

            if not hasattr(module, "CAPABILITY_DESCRIPTION"):
                return False, "Missing CAPABILITY_DESCRIPTION attribute"

            if not hasattr(module, "run"):
                return False, "Missing run() function"

            # Execute the capability
            self.logger.info(f"Executing: {module.CAPABILITY_NAME}")
            self.logger.info(f"  Description: {module.CAPABILITY_DESCRIPTION}")

            result = module.run()

            if result is None or result is True:
                return True, "Success"
            elif isinstance(result, str):
                return True, result
            elif isinstance(result, tuple) and len(result) == 2:
                return result
            else:
                return False, f"Invalid return value: {result}"

        except Exception as e:
            self.logger.error(f"Error executing {capability_name}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False, f"Exception: {str(e)}"

    def run_all_capabilities(self, stage=None) -> Dict[str, Any]:
        """
        Discover and run all capability modules.

        Args:
            stage: USD stage to operate on. If None, gets the current stage.

        Returns:
            Dictionary with execution results and statistics
        """
        self.loaded_capabilities = []

        # Get USD stage if not provided
        if stage is None:
            context = omni.usd.get_context()
            if context:
                stage = context.get_stage()

        # Log stage availability
        if stage is None:
            self.logger.warning("No USD stage available - some capabilities may be skipped")
        else:
            self.logger.info(f"Running capabilities on stage: {stage.GetRootLayer().identifier}")

        # Discover capabilities
        capability_files = self.discover_capabilities()

        if not capability_files:
            self.logger.warning("No capability modules found")
            return {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "capabilities": []
            }

        self.logger.info(f"Found {len(capability_files)} capability modules")

        # Execute each capability
        for cap_file in capability_files:
            cap_name = cap_file.stem
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Loading capability: {cap_name}")

            # Load the module
            module = self.load_capability_module(cap_file)
            if module is None:
                self.loaded_capabilities.append((cap_name, False, "Failed to load module"))
                continue

            # Execute the capability
            success, message = self.execute_capability(module, cap_name)
            self.loaded_capabilities.append((cap_name, success, message))

            if success:
                self.logger.info(f"✓ {cap_name}: {message}")
            else:
                self.logger.error(f"✗ {cap_name}: {message}")

        # Calculate statistics
        successful = sum(1 for _, success, _ in self.loaded_capabilities if success)
        failed = len(self.loaded_capabilities) - successful

        # Log summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("BOOTSTRAP INITIALIZATION COMPLETE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total capabilities: {len(self.loaded_capabilities)}")
        self.logger.info(f"Successful: {successful}")
        self.logger.info(f"Failed: {failed}")

        if failed > 0:
            self.logger.warning("\nFailed capabilities:")
            for name, success, message in self.loaded_capabilities:
                if not success:
                    self.logger.warning(f"  - {name}: {message}")

        # ============================================================
        # CRITICAL: Stop existing watchers before starting new ones
        # This ensures watchers are bound to the current stage, not
        # a previous stage (fixes issue with new file creation)
        # ============================================================

        self.logger.info("Restarting Vision DT watchers for current stage...")
        carb.log_info("[Vision DT] Restarting watchers for current stage...")

        # Stop existing light watcher
        try:
            from utils.light_watcher import stop_watching as stop_light_watching
            stop_light_watching()
            self.logger.info("Stopped previous light watcher (if any)")
        except Exception as e:
            self.logger.debug(f"No previous light watcher to stop: {e}")

        # Stop existing color sync
        try:
            from utils.color_sync import stop_color_sync
            stop_color_sync()
            self.logger.info("Stopped previous color sync (if any)")
        except Exception as e:
            self.logger.debug(f"No previous color sync to stop: {e}")

        # Stop existing LED color sync
        try:
            from utils.led_color_sync import stop_led_sync
            stop_led_sync()
            self.logger.info("Stopped previous LED color sync (if any)")
        except Exception as e:
            self.logger.debug(f"No previous LED color sync to stop: {e}")

        # Stop existing camera watcher
        try:
            from utils.camera_watcher import stop_watching as stop_camera_watching
            stop_camera_watching()
            self.logger.info("Stopped previous camera watcher (if any)")
        except Exception as e:
            self.logger.debug(f"No previous camera watcher to stop: {e}")

        # Stop existing lens sync
        try:
            from utils.lens_sync import stop_lens_sync
            stop_lens_sync()
            self.logger.info("Stopped previous lens sync (if any)")
        except Exception as e:
            self.logger.debug(f"No previous lens sync to stop: {e}")

        # Stop existing Zemax file watcher
        try:
            from utils.zemax_file_watcher import stop_watching as stop_zemax_watching
            stop_zemax_watching()
            self.logger.info("Stopped previous Zemax file watcher (if any)")
        except Exception as e:
            self.logger.debug(f"No previous Zemax file watcher to stop: {e}")

        # ============================================================
        # Start watchers with the CURRENT stage
        # ============================================================

        # Start the light watcher to handle newly created lights
        try:
            from utils.light_watcher import start_watching
            start_watching(stage)
            self.logger.info("Light watcher started - new lights will be auto-configured")
            carb.log_info("[Vision DT] ★ LightWatcher ACTIVE on current stage")
        except Exception as e:
            self.logger.warning(f"Could not start light watcher: {e}")
            carb.log_warn(f"[Vision DT] Could not start light watcher: {e}")

        # Start the color sync to handle real-time temperature changes
        try:
            from utils.color_sync import start_color_sync
            start_color_sync(stage)
            self.logger.info("Color sync started - temperature changes will update light color in real-time")
            carb.log_info("[Vision DT] ★ ColorSync ACTIVE on current stage")
        except Exception as e:
            self.logger.warning(f"Could not start color sync: {e}")
            carb.log_warn(f"[Vision DT] Could not start color sync: {e}")

        # Start the LED color sync to handle real-time wavelength changes
        try:
            from utils.led_color_sync import start_led_sync
            start_led_sync(stage)
            self.logger.info("LED color sync started - wavelength changes will update light color in real-time")
            carb.log_info("[Vision DT] ★ LEDColorSync ACTIVE on current stage")
        except Exception as e:
            self.logger.warning(f"Could not start LED color sync: {e}")
            carb.log_warn(f"[Vision DT] Could not start LED color sync: {e}")

        # Start the camera watcher to handle newly created cameras
        try:
            from utils.camera_watcher import start_watching as start_camera_watching
            start_camera_watching(stage)
            self.logger.info("Camera watcher started - new cameras will auto-receive Vision DT lens attributes")
            carb.log_info("[Vision DT] ★ CameraWatcher ACTIVE on current stage")
        except Exception as e:
            self.logger.warning(f"Could not start camera watcher: {e}")
            carb.log_warn(f"[Vision DT] Could not start camera watcher: {e}")

        # Start the lens sync to auto-apply lens profiles when libraryId changes
        try:
            from utils.lens_sync import start_lens_sync
            start_lens_sync(stage)
            self.logger.info("Lens sync started - changing libraryId will auto-apply lens profile")
            carb.log_info("[Vision DT] ★ LensSync ACTIVE on current stage")
        except Exception as e:
            self.logger.warning(f"Could not start lens sync: {e}")
            carb.log_warn(f"[Vision DT] Could not start lens sync: {e}")

        # Start the Zemax file watcher to auto-import .ZAR files
        try:
            from utils.zemax_file_watcher import start_watching as start_zemax_watching
            start_zemax_watching()
            self.logger.info("Zemax file watcher started - new .ZAR files will be auto-imported and applied to cameras")
            carb.log_info("[Vision DT] ★ ZemaxFileWatcher ACTIVE - monitoring for .ZAR files")
        except Exception as e:
            self.logger.warning(f"Could not start Zemax file watcher: {e}")
            carb.log_warn(f"[Vision DT] Could not start Zemax file watcher: {e}")

        return {
            "total": len(self.loaded_capabilities),
            "successful": successful,
            "failed": failed,
            "capabilities": self.loaded_capabilities
        }

    def get_status_message(self) -> str:
        """
        Get a formatted status message for display in UI.

        Returns:
            Formatted status string
        """
        if not self.loaded_capabilities:
            return "Bootstrap: Not initialized"

        successful = sum(1 for _, success, _ in self.loaded_capabilities if success)
        total = len(self.loaded_capabilities)

        if successful == total:
            return f"Bootstrap: All {total} capabilities loaded successfully ✓"
        else:
            failed = total - successful
            return f"Bootstrap: {successful}/{total} capabilities loaded ({failed} failed) ✗"


def initialize_bootstrap(capabilities_dir: Path = None, stage=None) -> Dict[str, Any]:
    """
    Convenience function to initialize the bootstrap system.

    Args:
        capabilities_dir: Path to capabilities directory
        stage: USD stage to operate on

    Returns:
        Dictionary with execution results
    """
    loader = BootstrapLoader(capabilities_dir)
    return loader.run_all_capabilities(stage)

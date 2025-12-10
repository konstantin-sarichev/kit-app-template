"""
Color Sync - Real-time synchronization of Vision DT temperature attributes to light color.

This module watches for changes to visiondt: temperature attributes and
automatically recalculates and applies the light color.

PRIORITY: Vision DT color settings ALWAYS override Omniverse's default color temperature.
When visiondt: attributes are present, inputs:enableColorTemperature is forced to False.
"""

import logging
import carb
import omni.usd
from pxr import Usd, Tf, Gf

from .lighting import calculate_multispectrum_color

logger = logging.getLogger("vision_dt.color_sync")

# Light types to monitor
LIGHT_TYPES = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]

# Attributes to watch
WATCHED_ATTRS = [
    "visiondt:overallTemperature",
    "visiondt:redTemperature",
    "visiondt:greenTemperature",
    "visiondt:blueTemperature"
]

# Singleton instance
_sync_instance = None


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb logger."""
    logger.info(message)
    carb.log_info(f"[Vision DT ColorSync] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb logger."""
    logger.warning(message)
    carb.log_warn(f"[Vision DT ColorSync] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb logger."""
    logger.error(message)
    carb.log_error(f"[Vision DT ColorSync] {message}")


class ColorSync:
    """
    Watches for changes to visiondt: temperature attributes and
    automatically updates the light's inputs:color.

    PRIORITY ENFORCEMENT:
    - Vision DT temperature settings ALWAYS take priority over Omniverse defaults
    - inputs:enableColorTemperature is forced to False when visiondt: attributes exist
    - This ensures consistent, predictable lighting for vision system simulation
    """

    def __init__(self):
        self._listener = None
        self._stage = None
        self._enabled = False
        _log_info("ColorSync module initialized")

    def start(self, stage: Usd.Stage = None):
        """Start watching for attribute changes."""
        if self._enabled:
            _log_info("ColorSync already running")
            return

        if stage is None:
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None

        if not stage:
            _log_warn("No stage available, cannot start ColorSync")
            return

        self._stage = stage

        # Register for attribute changes
        self._listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            stage
        )

        self._enabled = True
        _log_info("ColorSync ACTIVE - Vision DT temperatures will override Omniverse color temperature")
        _log_info("Monitoring attributes: " + ", ".join(WATCHED_ATTRS))

    def stop(self):
        """Stop watching for changes."""
        if self._listener:
            self._listener.Revoke()
            self._listener = None

        self._stage = None
        self._enabled = False
        _log_info("ColorSync stopped")

    def _on_objects_changed(self, notice, stage):
        """Called when objects in the stage change."""
        try:
            # Check changed info paths (attribute value changes)
            for path in notice.GetChangedInfoOnlyPaths():
                attr_path = str(path)

                # Check if this is one of our watched attributes
                for watched in WATCHED_ATTRS:
                    if watched in attr_path:
                        # Get the prim path (remove the attribute part)
                        prim_path = path.GetPrimPath()
                        prim = stage.GetPrimAtPath(prim_path)

                        if prim and prim.IsValid() and prim.GetTypeName() in LIGHT_TYPES:
                            _log_info(f"Detected change: {watched} on {prim_path}")
                            self._sync_light_color(prim)
                        break

        except Exception as e:
            _log_error(f"Error in ColorSync._on_objects_changed: {e}")

    def _sync_light_color(self, light_prim: Usd.Prim, force_override: bool = True):
        """
        Recalculate and apply color based on visiondt: temperature values.

        Args:
            light_prim: The light prim to sync
            force_override: If True, always disable Omniverse's color temperature (default: True)

        PRIORITY: Vision DT settings ALWAYS override Omniverse defaults when force_override=True
        """
        try:
            prim_path = str(light_prim.GetPath())

            # Get current temperature values
            def get_temp(name, default=6500.0):
                attr = light_prim.GetAttribute(f"visiondt:{name}")
                if attr and attr.IsValid():
                    val = attr.Get()
                    return val if val is not None else default
                return default

            overall_k = get_temp("overallTemperature")
            r_k = get_temp("redTemperature")
            g_k = get_temp("greenTemperature")
            b_k = get_temp("blueTemperature")

            _log_info(f"Syncing {prim_path}: Overall={overall_k}K, R={r_k}K, G={g_k}K, B={b_k}K")

            # Calculate final color using multi-spectrum algorithm
            final_color = calculate_multispectrum_color(overall_k, r_k, g_k, b_k)

            # PRIORITY ENFORCEMENT: Disable Omniverse's built-in color temperature
            # Vision DT settings MUST take precedence
            if force_override:
                ct_enable_attr = light_prim.GetAttribute("inputs:enableColorTemperature")
                if ct_enable_attr and ct_enable_attr.IsValid():
                    current_val = ct_enable_attr.Get()
                    if current_val != False:
                        ct_enable_attr.Set(False)
                        _log_info(f"  → OVERRIDE: Disabled Omniverse 'Enable Color Temperature' on {prim_path}")
                        _log_info(f"    (Vision DT temperature takes priority)")

            # Apply the calculated color to inputs:color
            color_attr = light_prim.GetAttribute("inputs:color")
            if color_attr and color_attr.IsValid():
                color_attr.Set(final_color)
                _log_info(f"  → Applied color: R={final_color[0]:.4f} G={final_color[1]:.4f} B={final_color[2]:.4f}")
            else:
                _log_warn(f"  → Could not find inputs:color attribute on {prim_path}")

        except Exception as e:
            _log_error(f"Failed to sync color for {light_prim.GetPath()}: {e}")
            import traceback
            _log_error(traceback.format_exc())


def get_color_sync() -> ColorSync:
    """Get or create the singleton ColorSync instance."""
    global _sync_instance
    if _sync_instance is None:
        _sync_instance = ColorSync()
    return _sync_instance


def start_color_sync(stage: Usd.Stage = None):
    """Start the color sync system."""
    _log_info("Starting Vision DT ColorSync system...")
    sync = get_color_sync()
    sync.start(stage)


def stop_color_sync():
    """Stop the color sync system."""
    global _sync_instance
    if _sync_instance:
        _sync_instance.stop()


def sync_all_lights(stage: Usd.Stage = None, force_override: bool = True):
    """
    Manually sync all lights in the stage.
    Useful for initial sync or after bulk changes.

    Args:
        stage: USD stage (uses current if None)
        force_override: If True, disable Omniverse color temperature on all lights

    Returns:
        Number of lights synced
    """
    if stage is None:
        context = omni.usd.get_context()
        stage = context.get_stage() if context else None

    if not stage:
        _log_warn("No stage available for sync_all_lights")
        return 0

    _log_info("=" * 60)
    _log_info("VISION DT: Syncing all lights (Priority Override Mode)")
    _log_info("=" * 60)

    sync = get_color_sync()
    count = 0
    skipped = 0

    for prim in stage.Traverse():
        if prim.GetTypeName() in LIGHT_TYPES:
            if prim.HasAttribute("visiondt:overallTemperature"):
                sync._sync_light_color(prim, force_override=force_override)
                count += 1
            else:
                skipped += 1
                _log_info(f"Skipped {prim.GetPath()} (no visiondt: attributes)")

    _log_info("=" * 60)
    _log_info(f"VISION DT: Sync complete - {count} light(s) updated, {skipped} skipped")
    _log_info("=" * 60)

    return count


def enforce_visiondt_priority(stage: Usd.Stage = None):
    """
    Enforce Vision DT priority on all lights.

    This function:
    1. Disables Omniverse's 'Enable Color Temperature' on all lights with visiondt: attributes
    2. Applies Vision DT calculated colors

    Call this to ensure Vision DT settings are not being overridden.
    """
    _log_info("Enforcing Vision DT priority over Omniverse defaults...")
    return sync_all_lights(stage, force_override=True)

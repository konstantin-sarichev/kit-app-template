"""
Light Watcher - Automatically applies Vision DT attributes to newly created lights.

This module subscribes to USD stage changes and detects when new light prims
are added, automatically configuring them with Vision DT attributes.

When active, ANY new light created will automatically receive:

  Vision DT Temperature Attributes:
  - visiondt:overallTemperature (default: 6500K)
  - visiondt:redTemperature (default: 6500K)
  - visiondt:greenTemperature (default: 6500K)
  - visiondt:blueTemperature (default: 6500K)
  - visiondt:iesProfile (default: empty)

  Vision DT LED Profile Attributes:
  - visiondt:led:enabled (default: False)
  - visiondt:led:peakWavelength (default: 0.0)
  - visiondt:led:dominantWavelength (default: 0.0)
  - visiondt:led:spectralBandwidth (default: 30.0)
  - visiondt:led:model, manufacturer, etc.
"""

import logging
import carb
import omni.usd
from pxr import Usd, Sdf, Tf, Vt, Gf

logger = logging.getLogger("vision_dt.light_watcher")

# Light types to watch for
LIGHT_TYPES = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]

# Default values
DEFAULT_TEMPERATURE = 6500.0

# Singleton watcher instance
_watcher_instance = None


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb logger."""
    logger.info(message)
    carb.log_info(f"[Vision DT LightWatcher] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb logger."""
    logger.warning(message)
    carb.log_warn(f"[Vision DT LightWatcher] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb logger."""
    logger.error(message)
    carb.log_error(f"[Vision DT LightWatcher] {message}")


class LightWatcher:
    """
    Watches for new light prims and applies Vision DT attributes automatically.

    When a new light is created in the stage, this watcher detects it and
    automatically adds all Vision DT temperature and IES profile attributes.
    """

    def __init__(self):
        self._stage_listener = None
        self._stage = None
        self._enabled = False
        _log_info("LightWatcher module initialized")

    def start(self, stage: Usd.Stage = None):
        """Start watching for new lights."""
        if self._enabled:
            _log_info("LightWatcher already running")
            return

        if stage is None:
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None

        if not stage:
            _log_warn("No stage available, cannot start LightWatcher")
            return

        self._stage = stage

        # Register for notice about objects changed
        self._stage_listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            stage
        )

        self._enabled = True
        _log_info("LightWatcher ACTIVE - new lights will auto-receive Vision DT attributes")
        _log_info(f"Monitoring light types: {', '.join(LIGHT_TYPES)}")

    def stop(self):
        """Stop watching for new lights."""
        if self._stage_listener:
            self._stage_listener.Revoke()
            self._stage_listener = None

        self._stage = None
        self._enabled = False
        _log_info("LightWatcher stopped")

    def _on_objects_changed(self, notice, stage):
        """Called when objects in the stage change."""
        try:
            # Check for newly added prims
            for path in notice.GetChangedInfoOnlyPaths():
                prim = stage.GetPrimAtPath(path.GetPrimPath())
                if prim and prim.IsValid():
                    self._check_and_configure_light(prim)

            # Also check resynced paths (for newly created prims)
            for path in notice.GetResyncedPaths():
                prim = stage.GetPrimAtPath(path)
                if prim and prim.IsValid():
                    self._check_and_configure_light(prim)

        except Exception as e:
            _log_error(f"Error in _on_objects_changed: {e}")

    def _check_and_configure_light(self, prim: Usd.Prim):
        """Check if prim is a light and configure it if needed."""
        if not prim.IsValid():
            return

        prim_type = prim.GetTypeName()
        if prim_type not in LIGHT_TYPES:
            return

        # Check if already has visiondt attributes
        if prim.HasAttribute("visiondt:overallTemperature"):
            return  # Already configured

        # Apply Vision DT attributes
        self._apply_visiondt_attributes(prim)

    def _apply_visiondt_attributes(self, light_prim: Usd.Prim):
        """Apply Vision DT custom attributes to a light prim."""
        try:
            prim_path = str(light_prim.GetPath())
            light_type = light_prim.GetTypeName()

            _log_info(f"NEW LIGHT DETECTED: {prim_path} ({light_type})")
            _log_info(f"  → Auto-applying Vision DT attributes...")

            # Temperature attributes (Vision DT group)
            temp_attrs = [
                ("visiondt:overallTemperature", "Overall Temperature (K)"),
                ("visiondt:redTemperature", "Red Temperature (K)"),
                ("visiondt:greenTemperature", "Green Temperature (K)"),
                ("visiondt:blueTemperature", "Blue Temperature (K)"),
            ]

            created_attrs = []
            for attr_name, display_name in temp_attrs:
                if not light_prim.HasAttribute(attr_name):
                    attr = light_prim.CreateAttribute(
                        attr_name,
                        Sdf.ValueTypeNames.Float,
                        custom=True
                    )
                    if attr:
                        attr.Set(DEFAULT_TEMPERATURE)
                        attr.SetCustomDataByKey("displayName", display_name)
                        attr.SetCustomDataByKey("displayGroup", "Vision DT")
                        created_attrs.append(attr_name.split(":")[-1])

            # IES Profile attribute (Vision DT group)
            if not light_prim.HasAttribute("visiondt:iesProfile"):
                attr = light_prim.CreateAttribute(
                    "visiondt:iesProfile",
                    Sdf.ValueTypeNames.Asset,
                    custom=True
                )
                if attr:
                    attr.SetCustomDataByKey("displayName", "IES Profile (.ies)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT")
                    created_attrs.append("iesProfile")

            # LED Profile attributes - SPECTRAL (Vision DT LED - Spectral group)
            led_spectral_attrs = [
                ("visiondt:led:enabled", Sdf.ValueTypeNames.Bool, False, "Enable LED Color Mode", "Vision DT LED - Spectral"),
                ("visiondt:led:spdMode", Sdf.ValueTypeNames.String, "gaussian", "SPD Mode (gaussian/manual/csv)", "Vision DT LED - Spectral"),
                ("visiondt:led:peakWavelength", Sdf.ValueTypeNames.Float, 0.0, "Peak Wavelength (nm)", "Vision DT LED - Spectral"),
                ("visiondt:led:dominantWavelength", Sdf.ValueTypeNames.Float, 0.0, "Dominant Wavelength (nm)", "Vision DT LED - Spectral"),
                ("visiondt:led:spectralBandwidth", Sdf.ValueTypeNames.Float, 30.0, "Spectral Bandwidth FWHM (nm)", "Vision DT LED - Spectral"),
                ("visiondt:led:whiteMix", Sdf.ValueTypeNames.Float, 0.0, "White Mix (0=saturated, 1=white)", "Vision DT LED - Spectral"),
            ]

            # LED Profile attributes - BRIGHTNESS (Vision DT LED - Brightness group)
            led_brightness_attrs = [
                ("visiondt:led:useLuminousIntensity", Sdf.ValueTypeNames.Bool, False, "Use Datasheet Brightness", "Vision DT LED - Brightness"),
                ("visiondt:led:luminousIntensity", Sdf.ValueTypeNames.Float, 0.0, "Luminous Intensity (mcd)", "Vision DT LED - Brightness"),
                ("visiondt:led:luminousFlux", Sdf.ValueTypeNames.Float, 0.0, "Luminous Flux (mlm)", "Vision DT LED - Brightness"),
                ("visiondt:led:emitterWidthMm", Sdf.ValueTypeNames.Float, 0.5, "Emitter Width (mm)", "Vision DT LED - Brightness"),
                ("visiondt:led:emitterHeightMm", Sdf.ValueTypeNames.Float, 0.3, "Emitter Height (mm)", "Vision DT LED - Brightness"),
                ("visiondt:led:currentRatio", Sdf.ValueTypeNames.Float, 1.0, "Current Ratio (0-1)", "Vision DT LED - Brightness"),
            ]

            # LED Profile attributes - DISTRIBUTION (Vision DT LED - Distribution group)
            led_distribution_attrs = [
                ("visiondt:led:viewingAngleH", Sdf.ValueTypeNames.Float, 120.0, "Viewing Angle Horizontal (°)", "Vision DT LED - Distribution"),
                ("visiondt:led:viewingAngleV", Sdf.ValueTypeNames.Float, 120.0, "Viewing Angle Vertical (°)", "Vision DT LED - Distribution"),
            ]

            # LED Profile attributes - ELECTRICAL (Vision DT LED - Electrical group)
            led_electrical_attrs = [
                ("visiondt:led:forwardCurrent", Sdf.ValueTypeNames.Float, 20.0, "Forward Current (mA)", "Vision DT LED - Electrical"),
                ("visiondt:led:forwardVoltage", Sdf.ValueTypeNames.Float, 3.0, "Forward Voltage (V)", "Vision DT LED - Electrical"),
            ]

            # LED Profile attributes - INFO (Vision DT LED - Info group)
            led_info_attrs = [
                ("visiondt:led:model", Sdf.ValueTypeNames.String, "", "LED Model", "Vision DT LED - Info"),
                ("visiondt:led:manufacturer", Sdf.ValueTypeNames.String, "", "Manufacturer", "Vision DT LED - Info"),
                ("visiondt:led:packageType", Sdf.ValueTypeNames.String, "", "Package Type (0402, etc.)", "Vision DT LED - Info"),
            ]

            # Combine all LED attributes
            all_led_attrs = (led_spectral_attrs + led_brightness_attrs +
                           led_distribution_attrs + led_electrical_attrs + led_info_attrs)

            led_created = []
            for attr_name, attr_type, default_val, display_name, display_group in all_led_attrs:
                if not light_prim.HasAttribute(attr_name):
                    attr = light_prim.CreateAttribute(
                        attr_name,
                        attr_type,
                        custom=True
                    )
                    if attr:
                        attr.Set(default_val)
                        attr.SetCustomDataByKey("displayName", display_name)
                        attr.SetCustomDataByKey("displayGroup", display_group)
                        led_created.append(attr_name.split(":")[-1])

            # SPD data attributes (arrays and file path)
            if not light_prim.HasAttribute("visiondt:led:spdWavelengths"):
                attr = light_prim.CreateAttribute("visiondt:led:spdWavelengths", Sdf.ValueTypeNames.FloatArray, custom=True)
                if attr:
                    attr.Set(Vt.FloatArray())
                    attr.SetCustomDataByKey("displayName", "SPD Wavelengths (nm)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - SPD Data")
                    led_created.append("spdWavelengths")

            if not light_prim.HasAttribute("visiondt:led:spdIntensities"):
                attr = light_prim.CreateAttribute("visiondt:led:spdIntensities", Sdf.ValueTypeNames.FloatArray, custom=True)
                if attr:
                    attr.Set(Vt.FloatArray())
                    attr.SetCustomDataByKey("displayName", "SPD Intensities (0-1)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - SPD Data")
                    led_created.append("spdIntensities")

            if not light_prim.HasAttribute("visiondt:led:spdCsvPath"):
                attr = light_prim.CreateAttribute("visiondt:led:spdCsvPath", Sdf.ValueTypeNames.Asset, custom=True)
                if attr:
                    attr.SetCustomDataByKey("displayName", "SPD CSV File Path")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - SPD Data")
                    led_created.append("spdCsvPath")

            if not light_prim.HasAttribute("visiondt:led:spdDataJson"):
                attr = light_prim.CreateAttribute("visiondt:led:spdDataJson", Sdf.ValueTypeNames.String, custom=True)
                if attr:
                    attr.Set("")
                    attr.SetCustomDataByKey("displayName", "SPD Data (JSON)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - SPD Data")
                    led_created.append("spdDataJson")

            if not light_prim.HasAttribute("visiondt:led:spdInfo"):
                attr = light_prim.CreateAttribute("visiondt:led:spdInfo", Sdf.ValueTypeNames.String, custom=True)
                if attr:
                    attr.Set("")
                    attr.SetCustomDataByKey("displayName", "SPD Info (read-only)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - SPD Data")
                    led_created.append("spdInfo")

            # Computed values (read-only)
            if not light_prim.HasAttribute("visiondt:led:computedColor"):
                attr = light_prim.CreateAttribute("visiondt:led:computedColor", Sdf.ValueTypeNames.Color3f, custom=True)
                if attr:
                    attr.Set(Gf.Vec3f(0.0, 0.0, 0.0))
                    attr.SetCustomDataByKey("displayName", "Computed RGB (read-only)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - Computed")
                    led_created.append("computedColor")

            if not light_prim.HasAttribute("visiondt:led:computedNits"):
                attr = light_prim.CreateAttribute("visiondt:led:computedNits", Sdf.ValueTypeNames.Float, custom=True)
                if attr:
                    attr.Set(0.0)
                    attr.SetCustomDataByKey("displayName", "Computed Nits (read-only)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - Computed")
                    led_created.append("computedNits")

            if not light_prim.HasAttribute("visiondt:led:computedIntensity"):
                attr = light_prim.CreateAttribute("visiondt:led:computedIntensity", Sdf.ValueTypeNames.Float, custom=True)
                if attr:
                    attr.Set(0.0)
                    attr.SetCustomDataByKey("displayName", "Computed Intensity (read-only)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - Computed")
                    led_created.append("computedIntensity")

            if not light_prim.HasAttribute("visiondt:led:computedExposure"):
                attr = light_prim.CreateAttribute("visiondt:led:computedExposure", Sdf.ValueTypeNames.Float, custom=True)
                if attr:
                    attr.Set(0.0)
                    attr.SetCustomDataByKey("displayName", "Computed Exposure (read-only)")
                    attr.SetCustomDataByKey("displayGroup", "Vision DT LED - Computed")
                    led_created.append("computedExposure")

            _log_info(f"  ✓ Vision DT: {', '.join(created_attrs)}")
            _log_info(f"  ✓ Vision DT LED: {len(led_created)} attributes added")
            _log_info(f"  ✓ Default temperature: {DEFAULT_TEMPERATURE}K (neutral daylight)")

        except Exception as e:
            _log_error(f"Failed to apply Vision DT attributes to {light_prim.GetPath()}: {e}")
            import traceback
            _log_error(traceback.format_exc())


def get_watcher() -> LightWatcher:
    """Get or create the singleton LightWatcher instance."""
    global _watcher_instance
    if _watcher_instance is None:
        _watcher_instance = LightWatcher()
    return _watcher_instance


def start_watching(stage: Usd.Stage = None):
    """Start the light watcher."""
    _log_info("Starting Vision DT LightWatcher...")
    watcher = get_watcher()
    watcher.start(stage)


def stop_watching():
    """Stop the light watcher."""
    global _watcher_instance
    if _watcher_instance:
        _watcher_instance.stop()


def apply_to_all_lights(stage: Usd.Stage = None):
    """
    Manually apply Vision DT attributes to ALL lights in the stage.
    Useful for applying to lights created before the watcher was started.
    """
    if stage is None:
        context = omni.usd.get_context()
        stage = context.get_stage() if context else None

    if not stage:
        _log_warn("No stage available")
        return 0

    _log_info("=" * 60)
    _log_info("Applying Vision DT attributes to all lights in stage...")
    _log_info("=" * 60)

    watcher = get_watcher()
    count = 0
    already_configured = 0

    for prim in stage.Traverse():
        if prim.GetTypeName() in LIGHT_TYPES:
            if not prim.HasAttribute("visiondt:overallTemperature"):
                watcher._apply_visiondt_attributes(prim)
                count += 1
            else:
                already_configured += 1

    _log_info("=" * 60)
    _log_info(f"Vision DT: {count} light(s) configured, {already_configured} already had attributes")
    _log_info("=" * 60)

    return count

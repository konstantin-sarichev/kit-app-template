"""
LED Color & Luminous Sync - Real-time synchronization of LED attributes to Omniverse.

This module watches for changes to visiondt:led: attributes and automatically
updates the light's color and intensity based on LED parameters.

COLOR SYNC (when visiondt:led:enabled is True):
  - Changes to peakWavelength, dominantWavelength, or spectralBandwidth
    trigger recalculation using FULL GAUSSIAN SPD integration
  - The calculated RGB is stored in visiondt:led:computedColor
  - The RGB is applied to inputs:color
  - inputs:enableColorTemperature is disabled to prevent conflicts

LUMINOUS SYNC (when visiondt:led:useLuminousIntensity is True):
  - Changes to luminousIntensity, luminousFlux, emitter dimensions, or viewing angles
    trigger recalculation of Omniverse intensity/exposure
  - Vision DT luminous values OVERRIDE Omniverse default brightness
  - Calculated values stored in computedNits, computedIntensity, computedExposure
  - inputs:intensity and inputs:exposure are set to match real-world luminance

This allows real-time preview of LED appearance as parameters are adjusted,
with physically accurate brightness from datasheet specifications.

Updated: 2025-12-05 - Added luminous intensity sync, full Gaussian SPD
"""

import logging
import carb
import omni.usd
from pxr import Usd, Sdf, Tf, Gf
import sys
from pathlib import Path

# Add bootstrap AND utils to path for imports
bootstrap_dir = Path(__file__).parent.parent
utils_dir = Path(__file__).parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))
if str(utils_dir) not in sys.path:
    sys.path.insert(0, str(utils_dir))

logger = logging.getLogger("vision_dt.led_color_sync")

# Pre-load spectral and luminous modules at import time to catch errors early
_spectral_module_loaded = False
_luminous_module_loaded = False
_led_wavelength_to_rgb_func = None
_led_spec_to_omniverse_func = None

try:
    from spectral import led_wavelength_to_rgb, spd_to_rgb, load_spd_from_csv, get_spd_info
    _led_wavelength_to_rgb_func = led_wavelength_to_rgb
    _spd_to_rgb_func = spd_to_rgb
    _load_spd_from_csv_func = load_spd_from_csv
    _get_spd_info_func = get_spd_info
    _spectral_module_loaded = True
    carb.log_info("[Vision DT LEDSync] Spectral module loaded successfully (with SPD support)")
except ImportError as e:
    carb.log_error(f"[Vision DT LEDSync] FAILED to load spectral module: {e}")
    # Try alternative import path
    try:
        from utils.spectral import led_wavelength_to_rgb, spd_to_rgb, load_spd_from_csv, get_spd_info
        _led_wavelength_to_rgb_func = led_wavelength_to_rgb
        _spd_to_rgb_func = spd_to_rgb
        _load_spd_from_csv_func = load_spd_from_csv
        _get_spd_info_func = get_spd_info
        _spectral_module_loaded = True
        carb.log_info("[Vision DT LEDSync] Spectral module loaded via utils path (with SPD support)")
    except ImportError as e2:
        carb.log_error(f"[Vision DT LEDSync] FAILED alternative spectral import: {e2}")
        _spd_to_rgb_func = None
        _load_spd_from_csv_func = None
        _get_spd_info_func = None

try:
    from luminous import led_spec_to_omniverse
    _led_spec_to_omniverse_func = led_spec_to_omniverse
    _luminous_module_loaded = True
    carb.log_info("[Vision DT LEDSync] Luminous module loaded successfully")
except ImportError as e:
    carb.log_error(f"[Vision DT LEDSync] FAILED to load luminous module: {e}")
    # Try alternative import path
    try:
        from utils.luminous import led_spec_to_omniverse
        _led_spec_to_omniverse_func = led_spec_to_omniverse
        _luminous_module_loaded = True
        carb.log_info("[Vision DT LEDSync] Luminous module loaded via utils path")
    except ImportError as e2:
        carb.log_error(f"[Vision DT LEDSync] FAILED alternative luminous import: {e2}")

# Singleton instance
_led_sync_instance = None

# Attributes that trigger COLOR recalculation
LED_COLOR_TRIGGER_ATTRS = [
    "visiondt:led:enabled",
    "visiondt:led:spdMode",              # SPD mode selection (gaussian/manual/csv)
    "visiondt:led:peakWavelength",        # Gaussian mode
    "visiondt:led:dominantWavelength",    # Gaussian mode
    "visiondt:led:spectralBandwidth",     # Gaussian mode
    "visiondt:led:spdWavelengths",        # Manual/CSV mode - wavelength array
    "visiondt:led:spdIntensities",        # Manual/CSV mode - intensity array
    "visiondt:led:spdCsvPath",            # CSV mode - file path
    "visiondt:led:spdDataJson",           # JSON import
    "visiondt:led:whiteMix",              # Controls blending with white (0=saturated, 1=white)
]

# Attributes that trigger LUMINOUS recalculation
LED_LUMINOUS_TRIGGER_ATTRS = [
    "visiondt:led:useLuminousIntensity",
    "visiondt:led:luminousIntensity",
    "visiondt:led:luminousFlux",
    "visiondt:led:emitterWidthMm",
    "visiondt:led:emitterHeightMm",
    "visiondt:led:viewingAngleH",
    "visiondt:led:viewingAngleV",
    "visiondt:led:currentRatio",
]

# Combined trigger list for backward compatibility
LED_TRIGGER_ATTRS = LED_COLOR_TRIGGER_ATTRS + LED_LUMINOUS_TRIGGER_ATTRS

# Light types to monitor
LIGHT_TYPES = ["DomeLight", "RectLight", "DiskLight", "SphereLight", "DistantLight", "CylinderLight"]


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb logger."""
    logger.info(message)
    carb.log_info(f"[Vision DT LEDSync] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb logger."""
    logger.warning(message)
    carb.log_warn(f"[Vision DT LEDSync] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb logger."""
    logger.error(message)
    carb.log_error(f"[Vision DT LEDSync] {message}")


class LEDColorSync:
    """
    Watches for LED attribute changes and syncs color AND luminous in real-time.

    When LED mode is enabled on a light, this class monitors for changes
    to wavelength and photometric parameters and automatically updates:
    - Light color (from wavelength using full Gaussian SPD)
    - Light intensity (from mcd/mlm using photometric conversion)

    Vision DT values OVERRIDE Omniverse defaults when enabled.
    """

    def __init__(self):
        self._stage_listener = None
        self._stage = None
        self._enabled = False
        self._spectral_module = None
        self._luminous_module = None
        _log_info("LEDColorSync module initialized (color + luminous)")

    def _get_spectral_module(self):
        """Get the spectral module (pre-loaded at import time)."""
        if self._spectral_module is None:
            # Use pre-loaded module from import time
            if _spectral_module_loaded and _led_wavelength_to_rgb_func is not None:
                self._spectral_module = _led_wavelength_to_rgb_func
                _log_info("Using pre-loaded spectral module")
            else:
                _log_error("Spectral module not available - wavelength sync disabled")
                _log_error("  Check that bootstrap/utils/spectral.py exists and has no errors")
                return None
        return self._spectral_module

    def _get_luminous_module(self):
        """Get the luminous module (pre-loaded at import time)."""
        if self._luminous_module is None:
            # Use pre-loaded module from import time
            if _luminous_module_loaded and _led_spec_to_omniverse_func is not None:
                self._luminous_module = _led_spec_to_omniverse_func
                _log_info("Using pre-loaded luminous module")
            else:
                _log_error("Luminous module not available - intensity sync disabled")
                _log_error("  Check that bootstrap/utils/luminous.py exists and has no errors")
                return None
        return self._luminous_module

    def start(self, stage: Usd.Stage = None):
        """Start watching for LED attribute changes."""
        _log_info("=" * 60)
        _log_info("LEDColorSync.start() called")
        _log_info("=" * 60)

        if self._enabled:
            _log_info("LEDColorSync already running - skipping")
            return

        if stage is None:
            _log_info("No stage provided, getting current stage...")
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None
            _log_info(f"  Got context: {context}")
            _log_info(f"  Got stage: {stage}")

        if not stage:
            _log_error("No stage available, cannot start LEDColorSync!")
            _log_error("  LED wavelength/luminosity changes will NOT sync to light!")
            return

        self._stage = stage
        _log_info(f"Stage: {stage.GetRootLayer().identifier}")

        # Check if modules are loaded
        _log_info(f"Module status:")
        _log_info(f"  Spectral module loaded: {_spectral_module_loaded}")
        _log_info(f"  Luminous module loaded: {_luminous_module_loaded}")

        if not _spectral_module_loaded:
            _log_error("  ⚠ Spectral module NOT loaded - wavelength → color will NOT work!")
        if not _luminous_module_loaded:
            _log_error("  ⚠ Luminous module NOT loaded - mcd/mlm → intensity will NOT work!")

        # Register for notice about objects changed
        _log_info("Registering Tf.Notice listener for Usd.Notice.ObjectsChanged...")
        self._stage_listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            stage
        )
        _log_info(f"  Listener registered: {self._stage_listener}")

        self._enabled = True
        _log_info("=" * 60)
        _log_info("★ LEDColorSync ACTIVE ★")
        _log_info("=" * 60)
        _log_info("LED changes will now auto-update light color AND intensity")
        _log_info("")
        _log_info("COLOR triggers (wavelength → RGB):")
        for attr in LED_COLOR_TRIGGER_ATTRS:
            _log_info(f"  - {attr}")
        _log_info("")
        _log_info("LUMINOUS triggers (mcd/mlm → intensity):")
        for attr in LED_LUMINOUS_TRIGGER_ATTRS:
            _log_info(f"  - {attr}")
        _log_info("=" * 60)

    def stop(self):
        """Stop watching for LED attribute changes."""
        if self._stage_listener:
            self._stage_listener.Revoke()
            self._stage_listener = None

        self._stage = None
        self._enabled = False
        _log_info("LEDColorSync stopped")

    def _on_objects_changed(self, notice, stage):
        """Called when objects in the stage change."""
        try:
            # Check both ChangedInfoOnlyPaths AND ResyncedPaths
            # Some attribute changes come through resync, not just info-only
            all_changed_paths = list(notice.GetChangedInfoOnlyPaths()) + list(notice.GetResyncedPaths())

            for path in all_changed_paths:
                path_str = str(path)

                # Check if this is a COLOR attribute we care about
                for trigger_attr in LED_COLOR_TRIGGER_ATTRS:
                    if trigger_attr in path_str:
                        prim_path = path.GetPrimPath()
                        prim = stage.GetPrimAtPath(prim_path)
                        if prim and prim.IsValid():
                            _log_info(f"★ Detected LED color trigger: {trigger_attr}")
                            _log_info(f"  Path: {prim_path}")
                            self._sync_led_color(prim)
                        else:
                            _log_warn(f"Could not find prim at {prim_path}")
                        break

                # Check if this is a LUMINOUS attribute we care about
                for trigger_attr in LED_LUMINOUS_TRIGGER_ATTRS:
                    if trigger_attr in path_str:
                        prim_path = path.GetPrimPath()
                        prim = stage.GetPrimAtPath(prim_path)
                        if prim and prim.IsValid():
                            _log_info(f"★ Detected LED luminous trigger: {trigger_attr}")
                            _log_info(f"  Path: {prim_path}")
                            self._sync_led_luminous(prim)
                        else:
                            _log_warn(f"Could not find prim at {prim_path}")
                        break

        except Exception as e:
            _log_error(f"Error in _on_objects_changed: {e}")
            import traceback
            _log_error(traceback.format_exc())

    def _sync_led_color(self, light_prim: Usd.Prim):
        """
        Sync LED SPD data to light color.

        Supports three SPD modes:
        - "gaussian": Uses peak wavelength + FWHM (traditional LED model)
        - "manual": Uses spdWavelengths + spdIntensities arrays (custom SPD)
        - "csv": Loads from spdCsvPath file (imported datasheet)

        All modes support white_mix parameter to blend between:
        - Pure saturated LED color (white_mix=0.0)
        - White light with spectral shift (white_mix=0.7-0.8)
        - Pure white (white_mix=1.0)
        """
        try:
            prim_path = str(light_prim.GetPath())
            _log_info(f"━━━ LED COLOR SYNC START: {prim_path} ━━━")

            # Check if LED mode is enabled
            enabled_attr = light_prim.GetAttribute("visiondt:led:enabled")
            enabled_val = enabled_attr.Get() if enabled_attr else None
            _log_info(f"  visiondt:led:enabled = {enabled_val}")

            if not enabled_attr or not enabled_val:
                _log_info(f"  ⊘ LED mode not enabled, skipping color sync")
                return

            # Get white mix (applies to all modes)
            white_mix_attr = light_prim.GetAttribute("visiondt:led:whiteMix")
            white_mix = white_mix_attr.Get() if white_mix_attr else 0.0

            # Get SPD mode
            mode_attr = light_prim.GetAttribute("visiondt:led:spdMode")
            spd_mode = mode_attr.Get() if mode_attr else "gaussian"
            spd_mode = spd_mode.lower() if spd_mode else "gaussian"
            _log_info(f"  SPD Mode: {spd_mode}, whiteMix={white_mix}")

            rgb = None

            # =================================================================
            # MODE: CSV - Load from file
            # =================================================================
            if spd_mode == "csv":
                _log_info(f"  Processing CSV mode...")
                csv_path_attr = light_prim.GetAttribute("visiondt:led:spdCsvPath")
                csv_path = csv_path_attr.Get() if csv_path_attr else None

                if csv_path:
                    # Handle AssetPath type
                    if hasattr(csv_path, 'path'):
                        csv_path = csv_path.path
                    csv_path = str(csv_path)

                if csv_path and _load_spd_from_csv_func:
                    _log_info(f"  Loading SPD from: {csv_path}")
                    result = _load_spd_from_csv_func(csv_path)

                    if result:
                        wavelengths, intensities = result

                        # Store in prim for future use
                        from pxr import Vt
                        wl_attr = light_prim.GetAttribute("visiondt:led:spdWavelengths")
                        int_attr = light_prim.GetAttribute("visiondt:led:spdIntensities")
                        if wl_attr and int_attr:
                            wl_attr.Set(Vt.FloatArray(wavelengths))
                            int_attr.Set(Vt.FloatArray(intensities))

                        # Update info
                        if _get_spd_info_func:
                            info = _get_spd_info_func(wavelengths, intensities)
                            info_attr = light_prim.GetAttribute("visiondt:led:spdInfo")
                            if info_attr:
                                info_str = f"CSV: {info['data_points']} pts, {info['wavelength_min']:.0f}-{info['wavelength_max']:.0f}nm, peak {info['peak_nm']:.0f}nm"
                                info_attr.Set(info_str)

                        # Calculate RGB
                        if _spd_to_rgb_func:
                            rgb = _spd_to_rgb_func(wavelengths, intensities, white_mix)
                            _log_info(f"  CSV SPD: {len(wavelengths)} points, peak={info['peak_nm']:.0f}nm")
                    else:
                        _log_warn(f"  ⊘ Failed to load CSV, falling back to gaussian mode")
                        spd_mode = "gaussian"
                else:
                    _log_warn(f"  ⊘ CSV mode but no valid path, falling back to gaussian mode")
                    spd_mode = "gaussian"

            # =================================================================
            # MODE: MANUAL - Use SPD arrays
            # =================================================================
            if spd_mode == "manual" and rgb is None:
                _log_info(f"  Processing Manual SPD mode...")
                wl_attr = light_prim.GetAttribute("visiondt:led:spdWavelengths")
                int_attr = light_prim.GetAttribute("visiondt:led:spdIntensities")

                wavelengths = list(wl_attr.Get()) if wl_attr and wl_attr.Get() else []
                intensities = list(int_attr.Get()) if int_attr and int_attr.Get() else []

                if wavelengths and intensities and len(wavelengths) == len(intensities):
                    if _spd_to_rgb_func:
                        rgb = _spd_to_rgb_func(wavelengths, intensities, white_mix)

                        if _get_spd_info_func:
                            info = _get_spd_info_func(wavelengths, intensities)
                            _log_info(f"  Manual SPD: {info['data_points']} points, peak={info['peak_nm']:.0f}nm")

                            # Update info attribute
                            info_attr = light_prim.GetAttribute("visiondt:led:spdInfo")
                            if info_attr:
                                info_str = f"Manual: {info['data_points']} pts, peak {info['peak_nm']:.0f}nm"
                                info_attr.Set(info_str)
                    else:
                        _log_warn(f"  ⊘ SPD functions not available")
                        spd_mode = "gaussian"
                else:
                    _log_warn(f"  ⊘ Manual mode but no valid SPD arrays (wl={len(wavelengths)}, int={len(intensities)})")
                    spd_mode = "gaussian"

            # =================================================================
            # MODE: GAUSSIAN - Traditional peak + FWHM
            # =================================================================
            if spd_mode == "gaussian" or rgb is None:
                _log_info(f"  Processing Gaussian SPD mode...")

                # Get wavelength parameters
                peak_attr = light_prim.GetAttribute("visiondt:led:peakWavelength")
                dominant_attr = light_prim.GetAttribute("visiondt:led:dominantWavelength")
                fwhm_attr = light_prim.GetAttribute("visiondt:led:spectralBandwidth")

                peak_nm = peak_attr.Get() if peak_attr else 0.0
                dominant_nm = dominant_attr.Get() if dominant_attr else 0.0
                fwhm_nm = fwhm_attr.Get() if fwhm_attr else 30.0

                _log_info(f"  Gaussian params: peak={peak_nm}nm, dominant={dominant_nm}nm, FWHM={fwhm_nm}nm")

                # Skip if no wavelength specified
                if peak_nm <= 0 and dominant_nm <= 0:
                    _log_warn(f"  ⊘ LED enabled but no wavelength set (peak={peak_nm}, dominant={dominant_nm})")
                    return

                # Use peak if dominant not specified
                if dominant_nm <= 0:
                    dominant_nm = peak_nm
                if peak_nm <= 0:
                    peak_nm = dominant_nm

                # Get spectral conversion function
                led_wavelength_to_rgb = self._get_spectral_module()
                if not led_wavelength_to_rgb:
                    _log_error("  ✗ Cannot calculate LED color - spectral module unavailable")
                    return

                # Calculate RGB from wavelength using FULL GAUSSIAN SPD
                rgb = led_wavelength_to_rgb(peak_nm, fwhm_nm, dominant_nm, use_full_spd=True, white_mix=white_mix)
                _log_info(f"  Gaussian SPD: λ={peak_nm}nm, FWHM={fwhm_nm}nm")

            # =================================================================
            # Apply color to light
            # =================================================================
            if rgb is None:
                _log_error("  ✗ Failed to calculate RGB color")
                return

            _log_info(f"  Calculated RGB = ({rgb[0]:.4f}, {rgb[1]:.4f}, {rgb[2]:.4f})")

            # Store computed color
            computed_attr = light_prim.GetAttribute("visiondt:led:computedColor")
            if computed_attr:
                computed_attr.Set(rgb)
                _log_info(f"  ✓ Stored computed color")

            # Apply to light's inputs:color
            color_attr = light_prim.GetAttribute("inputs:color")
            if color_attr:
                old_color = color_attr.Get()
                _log_info(f"  Current inputs:color = {old_color}")

                color_attr.Set(rgb)

                # Verify it was set
                new_color = color_attr.Get()
                _log_info(f"  ★ SET inputs:color = {new_color}")

                if new_color != rgb:
                    _log_warn(f"  ⚠ Color may not have been set correctly!")
                    _log_warn(f"    Expected: {rgb}")
                    _log_warn(f"    Got: {new_color}")

                # Disable Kelvin-based color temperature
                ct_enable = light_prim.GetAttribute("inputs:enableColorTemperature")
                if ct_enable:
                    ct_was = ct_enable.Get()
                    if ct_was:
                        ct_enable.Set(False)
                        _log_info(f"  → Disabled Omniverse 'enableColorTemperature' (was: {ct_was})")
                    else:
                        _log_info(f"  → Omniverse 'enableColorTemperature' already disabled")
            else:
                _log_error(f"  ✗ Could not find inputs:color attribute!")

            _log_info(f"━━━ LED COLOR SYNC END ━━━")

        except Exception as e:
            _log_error(f"Failed to sync LED color for {light_prim.GetPath()}: {e}")
            import traceback
            _log_error(traceback.format_exc())

    def _sync_led_luminous(self, light_prim: Usd.Prim):
        """
        Sync LED photometric values to Omniverse intensity/exposure.

        When enabled, Vision DT luminous values OVERRIDE Omniverse defaults.
        This allows using real datasheet mcd/mlm values for accurate brightness.
        """
        try:
            prim_path = str(light_prim.GetPath())
            _log_info(f"━━━ LED LUMINOUS SYNC START: {prim_path} ━━━")

            # Check if luminous mode is enabled
            use_luminous_attr = light_prim.GetAttribute("visiondt:led:useLuminousIntensity")
            use_luminous_val = use_luminous_attr.Get() if use_luminous_attr else None
            _log_info(f"  visiondt:led:useLuminousIntensity = {use_luminous_val}")

            if not use_luminous_attr or not use_luminous_val:
                _log_info(f"  ⊘ Luminous mode not enabled, skipping intensity sync")
                return

            # Get photometric parameters
            def get_attr(name, default=0.0):
                attr = light_prim.GetAttribute(f"visiondt:led:{name}")
                val = attr.Get() if attr and attr.IsValid() else default
                _log_info(f"    {name} = {val}")
                return val

            _log_info(f"  Reading photometric parameters:")
            mcd = get_attr("luminousIntensity", 0.0)
            mlm = get_attr("luminousFlux", 0.0)
            emitter_w = get_attr("emitterWidthMm", 0.5)
            emitter_h = get_attr("emitterHeightMm", 0.3)
            angle_h = get_attr("viewingAngleH", 120.0)
            angle_v = get_attr("viewingAngleV", 120.0)
            current_ratio = get_attr("currentRatio", 1.0)

            # Skip if no photometric data
            if mcd <= 0 and mlm <= 0:
                _log_warn(f"  ⊘ Luminous mode enabled but no mcd/mlm values set (mcd={mcd}, mlm={mlm})")
                return

            # Get luminous conversion function
            led_spec_to_omniverse = self._get_luminous_module()
            if not led_spec_to_omniverse:
                _log_error("  ✗ Cannot calculate luminous - luminous module unavailable")
                return

            # Calculate Omniverse values
            _log_info(f"  Calculating Omniverse intensity from photometric data...")
            intensity, exposure, nits = led_spec_to_omniverse(
                luminous_intensity_mcd=mcd,
                luminous_flux_mlm=mlm,
                emitter_width_mm=emitter_w,
                emitter_height_mm=emitter_h,
                viewing_angle_h_deg=angle_h,
                viewing_angle_v_deg=angle_v,
                current_ratio=current_ratio
            )

            _log_info(f"  Calculated: {nits:,.0f} nits → intensity={intensity:.2f}, exposure={exposure:.1f}")

            # Store computed values
            def set_attr(name, value):
                attr = light_prim.GetAttribute(f"visiondt:led:{name}")
                if attr and attr.IsValid():
                    attr.Set(value)
                    _log_info(f"  ✓ Stored {name} = {value}")

            set_attr("computedNits", nits)
            set_attr("computedIntensity", intensity)
            set_attr("computedExposure", exposure)

            # Apply to Omniverse light - THIS OVERRIDES DEFAULT INTENSITY
            intensity_attr = light_prim.GetAttribute("inputs:intensity")
            if intensity_attr:
                old_intensity = intensity_attr.Get()
                _log_info(f"  Current inputs:intensity = {old_intensity}")

                intensity_attr.Set(intensity)

                new_intensity = intensity_attr.Get()
                _log_info(f"  ★ SET inputs:intensity = {new_intensity}")

                if abs(new_intensity - intensity) > 0.001:
                    _log_warn(f"  ⚠ Intensity may not have been set correctly!")
            else:
                _log_error(f"  ✗ Could not find inputs:intensity attribute!")

            exposure_attr = light_prim.GetAttribute("inputs:exposure")
            if exposure_attr:
                old_exposure = exposure_attr.Get()
                _log_info(f"  Current inputs:exposure = {old_exposure}")

                exposure_attr.Set(exposure)

                new_exposure = exposure_attr.Get()
                _log_info(f"  ★ SET inputs:exposure = {new_exposure}")
            else:
                # Create exposure attribute if it doesn't exist
                _log_info(f"  Creating inputs:exposure attribute (doesn't exist)...")
                exposure_attr = light_prim.CreateAttribute(
                    "inputs:exposure",
                    Sdf.ValueTypeNames.Float,
                    custom=False
                )
                if exposure_attr:
                    exposure_attr.Set(exposure)
                    _log_info(f"  ✓ Created and set exposure={exposure:.1f}")
                else:
                    _log_error(f"  ✗ Failed to create exposure attribute!")

            _log_info(f"━━━ LED LUMINOUS SYNC END ━━━")

        except Exception as e:
            _log_error(f"Failed to sync LED luminous for {light_prim.GetPath()}: {e}")
            import traceback
            _log_error(traceback.format_exc())

    def sync_all_led_lights(self, stage: Usd.Stage = None):
        """
        Manually sync all lights with LED mode enabled.
        Syncs both COLOR and LUMINOUS values.
        Useful for initial sync or after loading a scene.
        """
        if stage is None:
            stage = self._stage
            if not stage:
                context = omni.usd.get_context()
                stage = context.get_stage() if context else None

        if not stage:
            _log_warn("No stage available")
            return 0

        _log_info("=" * 60)
        _log_info("Syncing all LED-enabled lights (color + luminous)...")
        _log_info("=" * 60)

        color_count = 0
        luminous_count = 0

        for prim in stage.Traverse():
            if prim.GetTypeName() not in LIGHT_TYPES:
                continue

            # Sync color if LED mode enabled
            enabled_attr = prim.GetAttribute("visiondt:led:enabled")
            if enabled_attr and enabled_attr.Get():
                self._sync_led_color(prim)
                color_count += 1

            # Sync luminous if luminous mode enabled
            use_luminous = prim.GetAttribute("visiondt:led:useLuminousIntensity")
            if use_luminous and use_luminous.Get():
                self._sync_led_luminous(prim)
                luminous_count += 1

        _log_info("=" * 60)
        _log_info(f"LED sync complete:")
        _log_info(f"  - Color (Gaussian SPD): {color_count} light(s)")
        _log_info(f"  - Luminous (mcd/mlm → nits): {luminous_count} light(s)")
        _log_info("=" * 60)

        return color_count + luminous_count


def get_led_sync() -> LEDColorSync:
    """Get or create the singleton LEDColorSync instance."""
    global _led_sync_instance
    if _led_sync_instance is None:
        _led_sync_instance = LEDColorSync()
    return _led_sync_instance


def start_led_sync(stage: Usd.Stage = None):
    """Start the LED color sync watcher."""
    _log_info("Starting Vision DT LEDColorSync...")
    sync = get_led_sync()
    sync.start(stage)


def stop_led_sync():
    """Stop the LED color sync watcher."""
    global _led_sync_instance
    if _led_sync_instance:
        _led_sync_instance.stop()


def sync_all_led_lights(stage: Usd.Stage = None):
    """Manually sync all LED-enabled lights."""
    sync = get_led_sync()
    return sync.sync_all_led_lights(stage)


def apply_led_preset(light_prim: Usd.Prim, preset_name: str, enable_luminous: bool = True) -> bool:
    """
    Apply a predefined LED preset to a light prim.

    Includes both spectral (color) AND photometric (brightness) data.

    Args:
        light_prim: The light prim to configure
        preset_name: Name of the preset (e.g., "osram_lt_qh9g", "blue_450", etc.)
        enable_luminous: If True, also enable datasheet brightness mode

    Returns:
        True if preset was applied
    """
    # LED presets with full specifications
    PRESETS = {
        # OSRAM test case - complete datasheet values
        "osram_lt_qh9g": {
            "peak": 525.0, "dominant": 530.0, "fwhm": 33.0,
            "model": "LT QH9G", "manufacturer": "OSRAM",
            "mcd": 90.0, "mlm": 300.0,  # Q2 group
            "emitterW": 0.5, "emitterH": 0.3,
            "angleH": 85.0, "angleV": 57.5
        },
        # Common machine vision LEDs
        "uv_365": {"peak": 365.0, "dominant": 365.0, "fwhm": 15.0, "model": "UV 365nm", "manufacturer": "Generic",
                   "mcd": 300.0, "mlm": 500.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "uv_385": {"peak": 385.0, "dominant": 385.0, "fwhm": 15.0, "model": "UV 385nm", "manufacturer": "Generic",
                   "mcd": 400.0, "mlm": 800.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "uv_405": {"peak": 405.0, "dominant": 405.0, "fwhm": 15.0, "model": "Violet 405nm", "manufacturer": "Generic",
                   "mcd": 500.0, "mlm": 1000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "blue_450": {"peak": 450.0, "dominant": 450.0, "fwhm": 20.0, "model": "Blue 450nm", "manufacturer": "Generic",
                     "mcd": 2000.0, "mlm": 5000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "cyan_505": {"peak": 505.0, "dominant": 505.0, "fwhm": 30.0, "model": "Cyan 505nm", "manufacturer": "Generic",
                     "mcd": 1200.0, "mlm": 3000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "green_520": {"peak": 520.0, "dominant": 520.0, "fwhm": 35.0, "model": "Green 520nm", "manufacturer": "Generic",
                      "mcd": 1500.0, "mlm": 4000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "green_530": {"peak": 525.0, "dominant": 530.0, "fwhm": 33.0, "model": "True Green 530nm", "manufacturer": "Generic",
                      "mcd": 1400.0, "mlm": 3500.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "lime_555": {"peak": 555.0, "dominant": 555.0, "fwhm": 30.0, "model": "Lime 555nm", "manufacturer": "Generic",
                     "mcd": 2000.0, "mlm": 5000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "amber_590": {"peak": 590.0, "dominant": 590.0, "fwhm": 15.0, "model": "Amber 590nm", "manufacturer": "Generic",
                      "mcd": 800.0, "mlm": 2000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "orange_605": {"peak": 605.0, "dominant": 605.0, "fwhm": 15.0, "model": "Orange 605nm", "manufacturer": "Generic",
                       "mcd": 1000.0, "mlm": 2500.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "red_625": {"peak": 625.0, "dominant": 625.0, "fwhm": 20.0, "model": "Red 625nm", "manufacturer": "Generic",
                    "mcd": 1200.0, "mlm": 3000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "red_660": {"peak": 660.0, "dominant": 660.0, "fwhm": 20.0, "model": "Deep Red 660nm", "manufacturer": "Generic",
                    "mcd": 800.0, "mlm": 2000.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "ir_850": {"peak": 850.0, "dominant": 850.0, "fwhm": 40.0, "model": "IR 850nm", "manufacturer": "Generic",
                   "mcd": 500.0, "mlm": 0.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
        "ir_940": {"peak": 940.0, "dominant": 940.0, "fwhm": 50.0, "model": "IR 940nm", "manufacturer": "Generic",
                   "mcd": 400.0, "mlm": 0.0, "emitterW": 2.0, "emitterH": 2.0, "angleH": 60.0, "angleV": 60.0},
    }

    preset = PRESETS.get(preset_name.lower())
    if not preset:
        _log_warn(f"Unknown LED preset: {preset_name}")
        _log_info(f"Available presets: {', '.join(sorted(PRESETS.keys()))}")
        return False

    try:
        # Set LED attributes
        def set_attr(name, value):
            attr = light_prim.GetAttribute(f"visiondt:led:{name}")
            if attr:
                attr.Set(value)
            else:
                _log_warn(f"Attribute visiondt:led:{name} not found")

        # Spectral parameters
        set_attr("peakWavelength", preset.get("peak", 0.0))
        set_attr("dominantWavelength", preset.get("dominant", 0.0))
        set_attr("spectralBandwidth", preset.get("fwhm", 30.0))
        set_attr("enabled", True)  # Enable LED color mode

        # Photometric parameters
        set_attr("luminousIntensity", preset.get("mcd", 0.0))
        set_attr("luminousFlux", preset.get("mlm", 0.0))
        set_attr("emitterWidthMm", preset.get("emitterW", 1.0))
        set_attr("emitterHeightMm", preset.get("emitterH", 1.0))
        set_attr("viewingAngleH", preset.get("angleH", 120.0))
        set_attr("viewingAngleV", preset.get("angleV", 120.0))
        set_attr("useLuminousIntensity", enable_luminous)

        # Metadata
        set_attr("model", preset.get("model", ""))
        set_attr("manufacturer", preset.get("manufacturer", ""))

        _log_info(f"Applied LED preset '{preset_name}' to {light_prim.GetPath()}")
        _log_info(f"  λpeak={preset.get('peak')}nm, λdom={preset.get('dominant')}nm, FWHM={preset.get('fwhm')}nm")
        _log_info(f"  {preset.get('mcd')} mcd, {preset.get('mlm')} mlm")
        _log_info(f"  Model: {preset.get('manufacturer')} {preset.get('model')}")

        # Trigger sync
        sync = get_led_sync()
        sync._sync_led_color(light_prim)
        if enable_luminous:
            sync._sync_led_luminous(light_prim)

        return True

    except Exception as e:
        _log_error(f"Failed to apply LED preset: {e}")
        return False

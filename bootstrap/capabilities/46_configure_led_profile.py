"""
Capability: LED Profile Configuration

Adds LED-specific attributes to light prims for wavelength-based color calculation.
Parameters appear in the "Vision DT LED" group below standard Vision DT attributes.

Supports:
- Peak wavelength (nm)
- Dominant wavelength (nm)
- Spectral bandwidth / FWHM (nm)
- LED model and manufacturer metadata
- Luminous flux and intensity
- Viewing angles (asymmetric)
- Automatic color calculation from wavelength

Priority: 46 (runs after advanced lighting configuration)
"""

import logging
import carb
from pxr import Usd, Sdf, UsdLux
import sys
from pathlib import Path

# Add bootstrap to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import (
    get_current_stage,
    find_prims_by_type,
    has_custom_attribute,
    set_prim_metadata
)
from utils.spectral import (
    led_wavelength_to_rgb,
    parse_spd_arrays,
    spd_to_rgb,
    load_spd_from_csv,
    get_spd_info,
    spd_arrays_to_json
)

# Required capability attributes
CAPABILITY_NAME = "LED Profile Configuration"
CAPABILITY_DESCRIPTION = "Adds LED wavelength parameters and calculates color from spectral data"

logger = logging.getLogger("vision_dt.capability.led_profile")


def _log_info(msg):
    """Log to both Python logger and Omniverse console."""
    logger.info(msg)
    carb.log_info(f"[Vision DT LED Profile] {msg}")


def _log_warn(msg):
    """Log warning to both Python logger and Omniverse console."""
    logger.warning(msg)
    carb.log_warn(f"[Vision DT LED Profile] {msg}")


def _log_error(msg):
    """Log error to both Python logger and Omniverse console."""
    logger.error(msg)
    carb.log_error(f"[Vision DT LED Profile] {msg}")


# LED Profile attribute definitions
# These appear BELOW the standard visiondt: attributes in property panel
LED_ATTRIBUTES = [
    # =========================================================================
    # SPD MODE SELECTION
    # =========================================================================
    {
        "name": "visiondt:led:spdMode",
        "type": Sdf.ValueTypeNames.String,
        "default": "gaussian",
        "displayName": "SPD Mode",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "Spectral data mode: 'gaussian' (peak+FWHM), 'manual' (array data), or 'csv' (file import)"
    },

    # =========================================================================
    # SPECTRAL PARAMETERS (Color) - Gaussian Mode
    # =========================================================================
    {
        "name": "visiondt:led:peakWavelength",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,  # 0 = not an LED / not specified
        "displayName": "Peak Wavelength (nm)",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "Peak emission wavelength in nanometers (Gaussian mode)"
    },
    {
        "name": "visiondt:led:dominantWavelength",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "Dominant Wavelength (nm)",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "Dominant wavelength for color perception (Gaussian mode)"
    },
    {
        "name": "visiondt:led:spectralBandwidth",
        "type": Sdf.ValueTypeNames.Float,
        "default": 30.0,
        "displayName": "Spectral Bandwidth FWHM (nm)",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "Full Width at Half Maximum of spectral output (Gaussian mode)"
    },

    # =========================================================================
    # SPD DATA - Manual/CSV Mode
    # =========================================================================
    {
        "name": "visiondt:led:spdCsvPath",
        "type": Sdf.ValueTypeNames.Asset,
        "default": "",
        "displayName": "SPD CSV File Path",
        "displayGroup": "Vision DT LED - SPD Data",
        "description": "Path to CSV file with wavelength,intensity columns (CSV mode)"
    },
    {
        "name": "visiondt:led:spdWavelengths",
        "type": Sdf.ValueTypeNames.FloatArray,
        "default": [],
        "displayName": "SPD Wavelengths (nm)",
        "displayGroup": "Vision DT LED - SPD Data",
        "description": "Array of wavelength values in nm (Manual mode)"
    },
    {
        "name": "visiondt:led:spdIntensities",
        "type": Sdf.ValueTypeNames.FloatArray,
        "default": [],
        "displayName": "SPD Intensities (0-1)",
        "displayGroup": "Vision DT LED - SPD Data",
        "description": "Array of relative intensity values 0-1 (Manual mode)"
    },
    {
        "name": "visiondt:led:spdDataJson",
        "type": Sdf.ValueTypeNames.String,
        "default": "",
        "displayName": "SPD Data (JSON)",
        "displayGroup": "Vision DT LED - SPD Data",
        "description": "JSON-encoded SPD data for import/export"
    },
    {
        "name": "visiondt:led:spdInfo",
        "type": Sdf.ValueTypeNames.String,
        "default": "",
        "displayName": "SPD Info (read-only)",
        "displayGroup": "Vision DT LED - SPD Data",
        "description": "Summary of loaded SPD data"
    },

    # =========================================================================
    # ENABLE/DISABLE AND WHITE MIX
    # =========================================================================
    # Enable/disable LED color mode
    {
        "name": "visiondt:led:enabled",
        "type": Sdf.ValueTypeNames.Bool,
        "default": False,
        "displayName": "Enable LED Color Mode",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "When enabled, calculates color from SPD instead of Kelvin"
    },
    # White mix - controls how much to blend with white (D65)
    {
        "name": "visiondt:led:whiteMix",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "White Mix (0=saturated, 1=white)",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "Blend factor: 0.0=pure saturated LED color, 0.7=white with color tint, 1.0=pure white"
    },
    # Computed color (read-only, for reference)
    {
        "name": "visiondt:led:computedColor",
        "type": Sdf.ValueTypeNames.Color3f,
        "default": (0.0, 0.0, 0.0),
        "displayName": "Computed RGB (read-only)",
        "displayGroup": "Vision DT LED - Spectral",
        "description": "RGB color calculated from SPD integration"
    },

    # =========================================================================
    # PHOTOMETRIC PARAMETERS (Brightness)
    # These OVERRIDE Omniverse's default intensity when enabled
    # =========================================================================
    {
        "name": "visiondt:led:useLuminousIntensity",
        "type": Sdf.ValueTypeNames.Bool,
        "default": False,
        "displayName": "Use Datasheet Brightness",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Enable to use mcd/mlm values from datasheet instead of Omniverse intensity"
    },
    {
        "name": "visiondt:led:luminousIntensity",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "Luminous Intensity (mcd)",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Luminous intensity in millicandelas (from datasheet)"
    },
    {
        "name": "visiondt:led:luminousFlux",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "Luminous Flux (mlm)",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Luminous flux in millilumens at rated current (from datasheet)"
    },
    {
        "name": "visiondt:led:emitterWidthMm",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.5,
        "displayName": "Emitter Width (mm)",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "LED die/emitter width in millimeters (for luminance calculation)"
    },
    {
        "name": "visiondt:led:emitterHeightMm",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.3,
        "displayName": "Emitter Height (mm)",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "LED die/emitter height in millimeters (for luminance calculation)"
    },
    {
        "name": "visiondt:led:currentRatio",
        "type": Sdf.ValueTypeNames.Float,
        "default": 1.0,
        "displayName": "Current Ratio (0-1)",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Ratio of actual current to rated current (for dimming, 1.0 = full brightness)"
    },
    {
        "name": "visiondt:led:computedNits",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "Computed Luminance (nits)",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Calculated luminance in cd/m² (read-only)"
    },
    {
        "name": "visiondt:led:computedIntensity",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "Computed Omni Intensity",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Calculated Omniverse intensity value (read-only)"
    },
    {
        "name": "visiondt:led:computedExposure",
        "type": Sdf.ValueTypeNames.Float,
        "default": 0.0,
        "displayName": "Computed Omni Exposure",
        "displayGroup": "Vision DT LED - Brightness",
        "description": "Calculated Omniverse exposure value (read-only)"
    },

    # =========================================================================
    # ANGULAR DISTRIBUTION
    # =========================================================================
    {
        "name": "visiondt:led:viewingAngleH",
        "type": Sdf.ValueTypeNames.Float,
        "default": 120.0,
        "displayName": "Viewing Angle H (°)",
        "displayGroup": "Vision DT LED - Distribution",
        "description": "Half viewing angle in horizontal direction"
    },
    {
        "name": "visiondt:led:viewingAngleV",
        "type": Sdf.ValueTypeNames.Float,
        "default": 120.0,
        "displayName": "Viewing Angle V (°)",
        "displayGroup": "Vision DT LED - Distribution",
        "description": "Half viewing angle in vertical direction"
    },

    # =========================================================================
    # ELECTRICAL PARAMETERS
    # =========================================================================
    {
        "name": "visiondt:led:forwardCurrent",
        "type": Sdf.ValueTypeNames.Float,
        "default": 20.0,
        "displayName": "Rated Forward Current (mA)",
        "displayGroup": "Vision DT LED - Electrical",
        "description": "Rated forward current in milliamps"
    },
    {
        "name": "visiondt:led:forwardVoltage",
        "type": Sdf.ValueTypeNames.Float,
        "default": 3.0,
        "displayName": "Rated Forward Voltage (V)",
        "displayGroup": "Vision DT LED - Electrical",
        "description": "Forward voltage at rated current"
    },

    # =========================================================================
    # METADATA
    # =========================================================================
    {
        "name": "visiondt:led:model",
        "type": Sdf.ValueTypeNames.String,
        "default": "",
        "displayName": "LED Model",
        "displayGroup": "Vision DT LED - Info",
        "description": "Manufacturer part number"
    },
    {
        "name": "visiondt:led:manufacturer",
        "type": Sdf.ValueTypeNames.String,
        "default": "",
        "displayName": "Manufacturer",
        "displayGroup": "Vision DT LED - Info",
        "description": "LED manufacturer name"
    },
    {
        "name": "visiondt:led:packageType",
        "type": Sdf.ValueTypeNames.String,
        "default": "",
        "displayName": "Package Type",
        "displayGroup": "Vision DT LED - Info",
        "description": "Package designator (e.g., 0402, 0603, 5050)"
    },
]


def add_led_attributes(light_prim: Usd.Prim) -> int:
    """
    Add LED profile attributes to a light prim.

    Args:
        light_prim: The light prim to configure

    Returns:
        Number of attributes added
    """
    added_count = 0
    from pxr import Gf, Vt

    for attr_def in LED_ATTRIBUTES:
        attr_name = attr_def["name"]

        # Skip if already exists
        if light_prim.HasAttribute(attr_name):
            continue

        # Create attribute
        attr = light_prim.CreateAttribute(
            attr_name,
            attr_def["type"],
            custom=True  # IMPORTANT: Must be True for custom attributes
        )

        if attr:
            # Set default value based on type
            default_val = attr_def["default"]
            if attr_def["type"] == Sdf.ValueTypeNames.Color3f:
                attr.Set(Gf.Vec3f(*default_val))
            elif attr_def["type"] == Sdf.ValueTypeNames.FloatArray:
                # FloatArray needs Vt.FloatArray
                attr.Set(Vt.FloatArray(default_val) if default_val else Vt.FloatArray())
            elif attr_def["type"] == Sdf.ValueTypeNames.Asset:
                # Asset type for file paths
                attr.Set(Sdf.AssetPath(default_val) if default_val else Sdf.AssetPath())
            else:
                attr.Set(default_val)

            # Set display metadata (correct USD API)
            attr.SetCustomDataByKey("displayName", attr_def["displayName"])
            attr.SetCustomDataByKey("displayGroup", attr_def["displayGroup"])

            if "description" in attr_def:
                attr.SetCustomDataByKey("description", attr_def["description"])

            added_count += 1
            _log_info(f"  Added: {attr_name}")

    return added_count


def load_spd_from_csv_to_prim(light_prim: Usd.Prim) -> bool:
    """
    Load SPD data from CSV file specified in spdCsvPath attribute.

    Reads the CSV file and populates spdWavelengths and spdIntensities arrays.

    Args:
        light_prim: The light prim with spdCsvPath attribute

    Returns:
        True if successful
    """
    try:
        from pxr import Vt

        csv_path_attr = light_prim.GetAttribute("visiondt:led:spdCsvPath")
        if not csv_path_attr:
            return False

        csv_path = csv_path_attr.Get()
        if not csv_path:
            return False

        # Handle AssetPath type
        if hasattr(csv_path, 'path'):
            csv_path = csv_path.path
        csv_path = str(csv_path)

        if not csv_path:
            return False

        # Load SPD data
        result = load_spd_from_csv(csv_path)
        if result is None:
            _log_error(f"Failed to load SPD from {csv_path}")
            return False

        wavelengths, intensities = result

        # Store in prim attributes
        wl_attr = light_prim.GetAttribute("visiondt:led:spdWavelengths")
        int_attr = light_prim.GetAttribute("visiondt:led:spdIntensities")

        if wl_attr and int_attr:
            wl_attr.Set(Vt.FloatArray(wavelengths))
            int_attr.Set(Vt.FloatArray(intensities))

            # Update info attribute
            info = get_spd_info(wavelengths, intensities)
            info_attr = light_prim.GetAttribute("visiondt:led:spdInfo")
            if info_attr:
                info_str = f"Points: {info['data_points']}, Range: {info['wavelength_min']:.0f}-{info['wavelength_max']:.0f}nm, Peak: {info['peak_nm']:.0f}nm"
                info_attr.Set(info_str)

            _log_info(f"Loaded SPD from CSV: {csv_path}")
            _log_info(f"  {len(wavelengths)} data points, peak at {info['peak_nm']:.0f}nm")
            return True

        return False

    except Exception as e:
        _log_error(f"Failed to load SPD from CSV: {e}")
        return False


def set_spd_data(
    light_prim: Usd.Prim,
    wavelengths: list,
    intensities: list,
    name: str = "Custom SPD"
) -> bool:
    """
    Set SPD data directly on a light prim.

    This is the programmatic way to set manual SPD data.

    Args:
        light_prim: The light prim to configure
        wavelengths: List of wavelengths in nm
        intensities: List of relative intensities (0-1)
        name: Name for the SPD data

    Returns:
        True if successful
    """
    try:
        from pxr import Vt

        if len(wavelengths) != len(intensities):
            _log_error("Wavelengths and intensities arrays must have same length")
            return False

        # Set mode to manual
        mode_attr = light_prim.GetAttribute("visiondt:led:spdMode")
        if mode_attr:
            mode_attr.Set("manual")

        # Set arrays
        wl_attr = light_prim.GetAttribute("visiondt:led:spdWavelengths")
        int_attr = light_prim.GetAttribute("visiondt:led:spdIntensities")

        if wl_attr and int_attr:
            wl_attr.Set(Vt.FloatArray(wavelengths))
            int_attr.Set(Vt.FloatArray(intensities))

            # Update info
            info = get_spd_info(wavelengths, intensities)
            info_attr = light_prim.GetAttribute("visiondt:led:spdInfo")
            if info_attr:
                info_str = f"{name}: {info['data_points']} pts, {info['wavelength_min']:.0f}-{info['wavelength_max']:.0f}nm, peak {info['peak_nm']:.0f}nm"
                info_attr.Set(info_str)

            # Also store as JSON for export
            json_attr = light_prim.GetAttribute("visiondt:led:spdDataJson")
            if json_attr:
                json_str = spd_arrays_to_json(wavelengths, intensities, name)
                json_attr.Set(json_str)

            _log_info(f"Set manual SPD data on {light_prim.GetPath()}")
            _log_info(f"  {len(wavelengths)} data points")
            return True

        return False

    except Exception as e:
        _log_error(f"Failed to set SPD data: {e}")
        return False


def sync_led_color(light_prim: Usd.Prim, force_apply: bool = False) -> bool:
    """
    Calculate and apply color from LED SPD data.

    Supports three SPD modes:
    - "gaussian": Uses peak wavelength + FWHM (traditional LED model)
    - "manual": Uses spdWavelengths + spdIntensities arrays (custom SPD)
    - "csv": Loads from spdCsvPath file (imported datasheet)

    All modes support white_mix to blend between:
    - Pure saturated LED color (white_mix=0.0)
    - White light with spectral shift (white_mix=0.7-0.8)
    - Pure white (white_mix=1.0)

    Only applies if visiondt:led:enabled is True OR force_apply is True.

    Args:
        light_prim: The light prim to update
        force_apply: If True, apply color regardless of enabled state

    Returns:
        True if color was updated, False otherwise
    """
    try:
        from pxr import Gf

        # Check if LED mode is enabled
        enabled_attr = light_prim.GetAttribute("visiondt:led:enabled")
        if not force_apply and (not enabled_attr or not enabled_attr.Get()):
            return False

        # Get white mix (applies to all modes)
        white_mix_attr = light_prim.GetAttribute("visiondt:led:whiteMix")
        white_mix = white_mix_attr.Get() if white_mix_attr else 0.0

        # Get SPD mode
        mode_attr = light_prim.GetAttribute("visiondt:led:spdMode")
        spd_mode = mode_attr.Get() if mode_attr else "gaussian"
        spd_mode = spd_mode.lower() if spd_mode else "gaussian"

        rgb = None

        # =================================================================
        # MODE: CSV - Load from file
        # =================================================================
        if spd_mode == "csv":
            csv_path_attr = light_prim.GetAttribute("visiondt:led:spdCsvPath")
            csv_path = csv_path_attr.Get() if csv_path_attr else None

            if csv_path:
                # Handle AssetPath type
                if hasattr(csv_path, 'path'):
                    csv_path = csv_path.path
                csv_path = str(csv_path)

            if csv_path:
                # Load CSV and update arrays
                load_spd_from_csv_to_prim(light_prim)

                # Now use the loaded arrays
                spd_mode = "manual"  # Fall through to manual mode
            else:
                _log_warn(f"CSV mode but no spdCsvPath set for {light_prim.GetPath()}")
                return False

        # =================================================================
        # MODE: MANUAL - Use SPD arrays
        # =================================================================
        if spd_mode == "manual":
            wl_attr = light_prim.GetAttribute("visiondt:led:spdWavelengths")
            int_attr = light_prim.GetAttribute("visiondt:led:spdIntensities")

            wavelengths = list(wl_attr.Get()) if wl_attr and wl_attr.Get() else []
            intensities = list(int_attr.Get()) if int_attr and int_attr.Get() else []

            if wavelengths and intensities and len(wavelengths) == len(intensities):
                # Calculate RGB from SPD arrays
                rgb = spd_to_rgb(wavelengths, intensities, white_mix)

                # Update info
                info = get_spd_info(wavelengths, intensities)
                _log_info(f"LED color (Manual SPD): {light_prim.GetPath()}")
                _log_info(f"  SPD: {info['data_points']} points, peak={info['peak_nm']:.0f}nm, white_mix={white_mix:.2f}")
                _log_info(f"  → RGB=({rgb[0]:.4f}, {rgb[1]:.4f}, {rgb[2]:.4f})")
            else:
                _log_warn(f"Manual SPD mode but no valid array data for {light_prim.GetPath()}")
                # Fall back to gaussian mode
                spd_mode = "gaussian"

        # =================================================================
        # MODE: GAUSSIAN - Traditional peak + FWHM
        # =================================================================
        if spd_mode == "gaussian" or rgb is None:
            # Get wavelength parameters
            peak_attr = light_prim.GetAttribute("visiondt:led:peakWavelength")
            dominant_attr = light_prim.GetAttribute("visiondt:led:dominantWavelength")
            fwhm_attr = light_prim.GetAttribute("visiondt:led:spectralBandwidth")

            peak_nm = peak_attr.Get() if peak_attr else 0.0
            dominant_nm = dominant_attr.Get() if dominant_attr else 0.0
            fwhm_nm = fwhm_attr.Get() if fwhm_attr else 30.0

            # Skip if no wavelength specified
            if peak_nm <= 0 and dominant_nm <= 0:
                _log_warn(f"Gaussian mode but no wavelength set for {light_prim.GetPath()}")
                return False

            # Use peak if dominant not specified
            if dominant_nm <= 0:
                dominant_nm = peak_nm
            if peak_nm <= 0:
                peak_nm = dominant_nm

            # Calculate RGB from wavelength using FULL GAUSSIAN SPD
            rgb = led_wavelength_to_rgb(peak_nm, fwhm_nm, dominant_nm, use_full_spd=True, white_mix=white_mix)

            _log_info(f"LED color (Gaussian SPD): {light_prim.GetPath()}")
            _log_info(f"  λpeak={peak_nm}nm, λdom={dominant_nm}nm, FWHM={fwhm_nm}nm, white_mix={white_mix:.2f}")
            _log_info(f"  → RGB=({rgb[0]:.4f}, {rgb[1]:.4f}, {rgb[2]:.4f})")

        # =================================================================
        # Apply color to light
        # =================================================================
        if rgb is None:
            return False

        # Store computed color
        computed_attr = light_prim.GetAttribute("visiondt:led:computedColor")
        if computed_attr:
            computed_attr.Set(rgb)

        # Apply to light's inputs:color
        color_attr = light_prim.GetAttribute("inputs:color")
        if color_attr:
            color_attr.Set(rgb)

            # Disable Kelvin-based color temperature (would override our SPD color)
            ct_enable = light_prim.GetAttribute("inputs:enableColorTemperature")
            if ct_enable:
                ct_enable.Set(False)

            return True

        return False

    except Exception as e:
        _log_error(f"Failed to sync LED color for {light_prim.GetPath()}: {e}")
        import traceback
        _log_error(traceback.format_exc())
        return False


def sync_led_luminous(light_prim: Usd.Prim, force_apply: bool = False) -> bool:
    """
    Calculate and apply Omniverse intensity/exposure from LED photometric data.

    This allows using real datasheet values (mcd, mlm) instead of arbitrary
    intensity values. Vision DT luminous values OVERRIDE Omniverse defaults.

    Only applies if visiondt:led:useLuminousIntensity is True OR force_apply is True.

    Args:
        light_prim: The light prim to update
        force_apply: If True, apply regardless of enabled state

    Returns:
        True if luminous values were updated, False otherwise
    """
    try:
        # Import luminous utilities
        from utils.luminous import led_spec_to_omniverse

        # Check if luminous mode is enabled
        use_luminous_attr = light_prim.GetAttribute("visiondt:led:useLuminousIntensity")
        if not force_apply and (not use_luminous_attr or not use_luminous_attr.Get()):
            return False

        # Get photometric parameters
        def get_attr(name, default=0.0):
            attr = light_prim.GetAttribute(f"visiondt:led:{name}")
            return attr.Get() if attr and attr.IsValid() else default

        mcd = get_attr("luminousIntensity", 0.0)
        mlm = get_attr("luminousFlux", 0.0)
        emitter_w = get_attr("emitterWidthMm", 0.5)
        emitter_h = get_attr("emitterHeightMm", 0.3)
        angle_h = get_attr("viewingAngleH", 120.0)
        angle_v = get_attr("viewingAngleV", 120.0)
        current_ratio = get_attr("currentRatio", 1.0)

        # Skip if no photometric data
        if mcd <= 0 and mlm <= 0:
            _log_warn(f"{light_prim.GetPath()}: Luminous mode enabled but no mcd/mlm values set")
            return False

        # Calculate Omniverse values
        intensity, exposure, nits = led_spec_to_omniverse(
            luminous_intensity_mcd=mcd,
            luminous_flux_mlm=mlm,
            emitter_width_mm=emitter_w,
            emitter_height_mm=emitter_h,
            viewing_angle_h_deg=angle_h,
            viewing_angle_v_deg=angle_v,
            current_ratio=current_ratio
        )

        # Store computed values (for reference/debugging)
        def set_attr(name, value):
            attr = light_prim.GetAttribute(f"visiondt:led:{name}")
            if attr and attr.IsValid():
                attr.Set(value)

        set_attr("computedNits", nits)
        set_attr("computedIntensity", intensity)
        set_attr("computedExposure", exposure)

        # Apply to Omniverse light - THIS OVERRIDES DEFAULT INTENSITY
        intensity_attr = light_prim.GetAttribute("inputs:intensity")
        if intensity_attr:
            intensity_attr.Set(intensity)

        exposure_attr = light_prim.GetAttribute("inputs:exposure")
        if exposure_attr:
            exposure_attr.Set(exposure)
        else:
            # Create exposure attribute if it doesn't exist
            exposure_attr = light_prim.CreateAttribute(
                "inputs:exposure",
                Sdf.ValueTypeNames.Float,
                custom=False
            )
            if exposure_attr:
                exposure_attr.Set(exposure)

        _log_info(f"LED luminous applied (OVERRIDES Omniverse): {light_prim.GetPath()}")
        _log_info(f"  mcd={mcd}, mlm={mlm}, emitter={emitter_w}x{emitter_h}mm")
        _log_info(f"  → {nits:,.0f} nits = intensity={intensity:.2f}, exposure={exposure:.1f}")

        return True

    except Exception as e:
        _log_error(f"Failed to sync LED luminous for {light_prim.GetPath()}: {e}")
        return False


def configure_led_profile(light_prim: Usd.Prim) -> bool:
    """
    Configure a single light prim with LED profile attributes.

    Adds all Vision DT LED attributes for:
    - Spectral parameters (wavelength, bandwidth for color)
    - Photometric parameters (mcd, mlm for brightness)
    - Angular distribution (viewing angles)
    - Electrical parameters (current, voltage)
    - Metadata (model, manufacturer, package)

    Args:
        light_prim: The light prim to configure

    Returns:
        True if successful
    """
    try:
        prim_path = light_prim.GetPath()
        _log_info(f"Configuring LED profile for {prim_path}")

        # Add LED attributes
        added = add_led_attributes(light_prim)

        # Sync color if LED mode was already enabled (from saved scene)
        color_synced = sync_led_color(light_prim)

        # Sync luminous intensity if enabled (from saved scene)
        luminous_synced = sync_led_luminous(light_prim)

        # Set metadata
        set_prim_metadata(light_prim, "vision_dt:led_profile", "configured")

        if added > 0:
            _log_info(f"  Added {added} LED attributes to {prim_path}")
        if color_synced:
            _log_info(f"  Synced LED color (full Gaussian SPD)")
        if luminous_synced:
            _log_info(f"  Synced LED luminous intensity (overrides Omniverse)")

        return True

    except Exception as e:
        _log_error(f"Failed to configure LED profile for {light_prim.GetPath()}: {e}")
        return False


def apply_led_preset(light_prim: Usd.Prim, preset_name: str, enable_luminous: bool = True) -> bool:
    """
    Apply a predefined LED preset to a light prim.

    Available presets match common industrial LED types with full specifications:
    - Spectral: peak wavelength, FWHM, dominant wavelength
    - Photometric: luminous intensity (mcd), luminous flux (mlm)
    - Angular: viewing angles (horizontal, vertical)
    - Electrical: forward current, forward voltage
    - Physical: emitter dimensions, package type

    Args:
        light_prim: The light prim to configure
        preset_name: Name of the preset (e.g., "osram_lt_qh9g", "blue_450", etc.)
        enable_luminous: If True, also enable datasheet brightness mode

    Returns:
        True if preset was applied
    """
    # LED presets with complete specifications
    # All values from manufacturer datasheets where available
    PRESETS = {
        # =====================================================================
        # OSRAM LT QH9G - True Green 0402 (test case)
        # Datasheet values at IF=5mA, Q2 brightness group
        # =====================================================================
        "osram_lt_qh9g": {
            "peak": 525.0,
            "dominant": 530.0,
            "fwhm": 33.0,
            "model": "LT QH9G",
            "manufacturer": "OSRAM",
            "package": "0402",
            "flux": 300.0,      # Q2 group: 300 mlm
            "intensity": 90.0,  # Q2 group: 90 mcd
            "emitterW": 0.5,    # Estimated die width
            "emitterH": 0.3,    # Estimated die height
            "angleH": 85.0,     # 170° full = 85° half
            "angleV": 57.5,     # 115° full = 57.5° half
            "current": 5.0,     # Rated current
            "voltage": 2.85     # Typical VF
        },

        # =====================================================================
        # OSRAM LT QH9G Brightness Groups (same LED, different bins)
        # =====================================================================
        "osram_lt_qh9g_r1": {
            "peak": 525.0, "dominant": 530.0, "fwhm": 33.0,
            "model": "LT QH9G-R1", "manufacturer": "OSRAM", "package": "0402",
            "flux": 420.0, "intensity": 126.0,  # R1 group
            "emitterW": 0.5, "emitterH": 0.3,
            "angleH": 85.0, "angleV": 57.5,
            "current": 5.0, "voltage": 2.85
        },
        "osram_lt_qh9g_s1": {
            "peak": 525.0, "dominant": 530.0, "fwhm": 33.0,
            "model": "LT QH9G-S1", "manufacturer": "OSRAM", "package": "0402",
            "flux": 670.0, "intensity": 200.0,  # S1 group
            "emitterW": 0.5, "emitterH": 0.3,
            "angleH": 85.0, "angleV": 57.5,
            "current": 5.0, "voltage": 2.85
        },
        "osram_lt_qh9g_t2": {
            "peak": 525.0, "dominant": 530.0, "fwhm": 33.0,
            "model": "LT QH9G-T2", "manufacturer": "OSRAM", "package": "0402",
            "flux": 1100.0, "intensity": 400.0,  # T2 group (brightest)
            "emitterW": 0.5, "emitterH": 0.3,
            "angleH": 85.0, "angleV": 57.5,
            "current": 5.0, "voltage": 2.85
        },

        # =====================================================================
        # Common Machine Vision LEDs
        # =====================================================================
        "uv_365": {
            "peak": 365.0, "dominant": 365.0, "fwhm": 15.0,
            "model": "UV 365nm", "manufacturer": "Generic", "package": "3535",
            "flux": 500.0, "intensity": 300.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 350.0, "voltage": 3.5
        },
        "uv_385": {
            "peak": 385.0, "dominant": 385.0, "fwhm": 15.0,
            "model": "UV 385nm", "manufacturer": "Generic", "package": "3535",
            "flux": 800.0, "intensity": 400.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 350.0, "voltage": 3.4
        },
        "uv_405": {
            "peak": 405.0, "dominant": 405.0, "fwhm": 15.0,
            "model": "Violet 405nm", "manufacturer": "Generic", "package": "3535",
            "flux": 1000.0, "intensity": 500.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 350.0, "voltage": 3.3
        },
        "blue_450": {
            "peak": 450.0, "dominant": 450.0, "fwhm": 20.0,
            "model": "Blue 450nm", "manufacturer": "Generic", "package": "3528",
            "flux": 5000.0, "intensity": 2000.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 3.2
        },
        "cyan_505": {
            "peak": 505.0, "dominant": 505.0, "fwhm": 30.0,
            "model": "Cyan 505nm", "manufacturer": "Generic", "package": "3528",
            "flux": 3000.0, "intensity": 1200.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 3.4
        },
        "green_520": {
            "peak": 520.0, "dominant": 520.0, "fwhm": 35.0,
            "model": "Green 520nm", "manufacturer": "Generic", "package": "3528",
            "flux": 4000.0, "intensity": 1500.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 3.4
        },
        "green_530": {
            "peak": 525.0, "dominant": 530.0, "fwhm": 33.0,
            "model": "True Green 530nm", "manufacturer": "Generic", "package": "3528",
            "flux": 3500.0, "intensity": 1400.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 3.4
        },
        "lime_555": {
            "peak": 555.0, "dominant": 555.0, "fwhm": 30.0,
            "model": "Lime 555nm", "manufacturer": "Generic", "package": "3528",
            "flux": 5000.0, "intensity": 2000.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 3.2
        },
        "amber_590": {
            "peak": 590.0, "dominant": 590.0, "fwhm": 15.0,
            "model": "Amber 590nm", "manufacturer": "Generic", "package": "3528",
            "flux": 2000.0, "intensity": 800.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 2.1
        },
        "orange_605": {
            "peak": 605.0, "dominant": 605.0, "fwhm": 15.0,
            "model": "Orange 605nm", "manufacturer": "Generic", "package": "3528",
            "flux": 2500.0, "intensity": 1000.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 2.0
        },
        "red_625": {
            "peak": 625.0, "dominant": 625.0, "fwhm": 20.0,
            "model": "Red 625nm", "manufacturer": "Generic", "package": "3528",
            "flux": 3000.0, "intensity": 1200.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 2.0
        },
        "red_660": {
            "peak": 660.0, "dominant": 660.0, "fwhm": 20.0,
            "model": "Deep Red 660nm", "manufacturer": "Generic", "package": "3528",
            "flux": 2000.0, "intensity": 800.0,
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 60.0, "voltage": 2.1
        },
        "ir_850": {
            "peak": 850.0, "dominant": 850.0, "fwhm": 40.0,
            "model": "IR 850nm", "manufacturer": "Generic", "package": "3535",
            "flux": 0.0, "intensity": 500.0,  # IR uses radiant intensity
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 350.0, "voltage": 1.5
        },
        "ir_940": {
            "peak": 940.0, "dominant": 940.0, "fwhm": 50.0,
            "model": "IR 940nm", "manufacturer": "Generic", "package": "3535",
            "flux": 0.0, "intensity": 400.0,  # IR uses radiant intensity
            "emitterW": 2.0, "emitterH": 2.0,
            "angleH": 60.0, "angleV": 60.0,
            "current": 350.0, "voltage": 1.4
        },
    }

    preset = PRESETS.get(preset_name.lower())
    if not preset:
        _log_warn(f"Unknown LED preset: {preset_name}")
        _log_info(f"Available presets: {', '.join(sorted(PRESETS.keys()))}")
        return False

    try:
        # Set all LED parameters
        def set_attr(name, value):
            attr = light_prim.GetAttribute(f"visiondt:led:{name}")
            if attr:
                attr.Set(value)

        # Spectral parameters
        set_attr("peakWavelength", preset.get("peak", 0.0))
        set_attr("dominantWavelength", preset.get("dominant", 0.0))
        set_attr("spectralBandwidth", preset.get("fwhm", 30.0))
        set_attr("enabled", True)  # Enable LED color mode

        # Photometric parameters
        set_attr("luminousFlux", preset.get("flux", 0.0))
        set_attr("luminousIntensity", preset.get("intensity", 0.0))
        set_attr("emitterWidthMm", preset.get("emitterW", 1.0))
        set_attr("emitterHeightMm", preset.get("emitterH", 1.0))
        set_attr("useLuminousIntensity", enable_luminous)  # Enable brightness override

        # Angular parameters
        set_attr("viewingAngleH", preset.get("angleH", 120.0))
        set_attr("viewingAngleV", preset.get("angleV", 120.0))

        # Electrical parameters
        set_attr("forwardCurrent", preset.get("current", 20.0))
        set_attr("forwardVoltage", preset.get("voltage", 3.0))

        # Metadata
        set_attr("model", preset.get("model", ""))
        set_attr("manufacturer", preset.get("manufacturer", ""))
        set_attr("packageType", preset.get("package", ""))

        # Sync color using full Gaussian SPD
        sync_led_color(light_prim, force_apply=True)

        # Sync luminous intensity (overrides Omniverse defaults)
        if enable_luminous:
            sync_led_luminous(light_prim, force_apply=True)

        _log_info(f"Applied LED preset '{preset_name}' to {light_prim.GetPath()}")
        _log_info(f"  Model: {preset.get('manufacturer')} {preset.get('model')}")
        _log_info(f"  λpeak={preset.get('peak')}nm, FWHM={preset.get('fwhm')}nm")
        _log_info(f"  {preset.get('intensity')}mcd, {preset.get('flux')}mlm")

        return True

    except Exception as e:
        _log_error(f"Failed to apply LED preset: {e}")
        return False


def run(stage: Usd.Stage = None) -> tuple:
    """
    Run LED profile configuration on all lights.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if stage is None:
            stage = get_current_stage()

        if not stage:
            return True, "No stage (skipped)"

        # Find all lights
        light_types = [
            "DomeLight", "RectLight", "DiskLight", "SphereLight",
            "DistantLight", "CylinderLight"
        ]

        all_lights = []
        for light_type in light_types:
            all_lights.extend(find_prims_by_type(stage, light_type))

        if not all_lights:
            return True, "No lights found (skipped)"

        configured_count = 0
        for light in all_lights:
            if configure_led_profile(light):
                configured_count += 1

        msg = f"Configured LED profile for {configured_count} light(s)"
        _log_info(msg)
        return True, msg

    except Exception as e:
        _log_error(f"LED Profile configuration failed: {e}")
        return False, str(e)

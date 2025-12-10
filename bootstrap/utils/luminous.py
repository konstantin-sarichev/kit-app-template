"""
Luminous Utility Functions for Photometric Conversion

Provides functions for converting real-world photometric values (lumens, candelas)
to Omniverse intensity/exposure values.

Vision DT Priority System:
- Vision DT luminous values ALWAYS override Omniverse default brightness
- When visiondt:led:useLuminousIntensity is True, the calculated intensity is applied
- Omniverse's default intensity slider is overridden

Key Conversions:
- millicandelas (mcd) → Omniverse intensity
- millilumens (mlm) → Omniverse intensity
- lumens (lm) → Omniverse intensity

Omniverse Light Units:
- UsdLux intensity of 1.0 = 1 nit (candela per square meter, cd/m²)
- exposure provides exponential scaling: effective = intensity × 2^exposure
- For physically accurate simulation, we need to map real LED specs to these units

Reference: OSRAM LT QH9G (test case)
- Luminous intensity: 90-450 mcd at IF=5mA
- Package: 0402 (1.0mm × 0.5mm)
- This gives luminance of ~540,000 nits for a 0.5mm² source!

Updated: 2025-12-05 - Initial creation with photometric conversion utilities
"""

import math
import logging
from typing import Tuple, Optional
from pxr import Gf

logger = logging.getLogger("vision_dt.luminous")


# =============================================================================
# CONSTANTS
# =============================================================================

# Omniverse intensity unit: 1 nit = 1 cd/m²
OMNI_INTENSITY_UNIT = "nit"

# Maximum photopic luminous efficacy (at 555nm)
MAX_LUMINOUS_EFFICACY = 683.0  # lm/W

# Common reference values
CANDLE_LUMINOUS_INTENSITY = 1.0  # 1 candela (definition)
TYPICAL_LCD_LUMINANCE = 300.0  # nits
SUNLIGHT_LUMINANCE = 1_600_000_000.0  # ~1.6 billion nits
TYPICAL_LED_LUMINANCE = 100_000.0  # ~100k nits for typical SMD LED


# =============================================================================
# PHOTOMETRIC CONVERSION FUNCTIONS
# =============================================================================

def millicandelas_to_nits(
    mcd: float,
    emitter_area_mm2: float = 0.5,
    viewing_angle_h_deg: float = 120.0,
    viewing_angle_v_deg: float = 120.0
) -> float:
    """
    Convert millicandelas to nits (cd/m²) for an area light source.

    Luminance (nits) = Luminous Intensity (cd) / Emitter Area (m²)

    For LEDs, the emitter area is typically the die size, not the package size.

    Args:
        mcd: Luminous intensity in millicandelas
        emitter_area_mm2: Emitting area in square millimeters
                         Default 0.5mm² (typical for 0402 die)
        viewing_angle_h_deg: Horizontal viewing half-angle (degrees)
        viewing_angle_v_deg: Vertical viewing half-angle (degrees)

    Returns:
        Luminance in nits (cd/m²)

    Example:
        OSRAM LT QH9G: 270 mcd, ~0.3mm² die
        >>> millicandelas_to_nits(270, 0.3)
        900000.0  # 900,000 nits
    """
    if mcd <= 0 or emitter_area_mm2 <= 0:
        logger.warning("Invalid mcd or area value")
        return 0.0

    # Convert mcd to cd
    cd = mcd / 1000.0

    # Convert mm² to m²
    area_m2 = emitter_area_mm2 * 1e-6

    # Calculate luminance (nits = cd/m²)
    nits = cd / area_m2

    logger.debug(f"mcd_to_nits: {mcd}mcd / {emitter_area_mm2}mm² = {nits:.0f} nits")

    return nits


def millilumens_to_nits(
    mlm: float,
    emitter_area_mm2: float = 0.5,
    viewing_angle_h_deg: float = 120.0,
    viewing_angle_v_deg: float = 120.0
) -> float:
    """
    Convert millilumens to nits (cd/m²) for an area light source.

    For a Lambertian emitter, luminance = flux / (π × area)

    Args:
        mlm: Luminous flux in millilumens
        emitter_area_mm2: Emitting area in square millimeters
        viewing_angle_h_deg: Horizontal viewing half-angle (degrees)
        viewing_angle_v_deg: Vertical viewing half-angle (degrees)

    Returns:
        Luminance in nits (cd/m²)
    """
    if mlm <= 0 or emitter_area_mm2 <= 0:
        return 0.0

    # Convert mlm to lm
    lm = mlm / 1000.0

    # Convert mm² to m²
    area_m2 = emitter_area_mm2 * 1e-6

    # For Lambertian emitter: L = Φ / (π × A)
    # where Φ is flux in lumens, A is area in m²
    nits = lm / (math.pi * area_m2)

    # Adjust for non-Lambertian emission (narrower beam = higher on-axis luminance)
    # For typical LED viewing angles < 180°, the on-axis luminance is higher
    beam_factor = calculate_beam_factor(viewing_angle_h_deg, viewing_angle_v_deg)
    nits *= beam_factor

    logger.debug(f"mlm_to_nits: {mlm}mlm / {emitter_area_mm2}mm² = {nits:.0f} nits (beam factor: {beam_factor:.2f})")

    return nits


def calculate_beam_factor(
    viewing_angle_h_deg: float,
    viewing_angle_v_deg: float
) -> float:
    """
    Calculate beam concentration factor for non-Lambertian emitters.

    Lambertian (180° half-angle) has factor 1.0.
    Narrower beams concentrate light, increasing on-axis luminance.

    Uses approximation based on solid angle ratio.

    Args:
        viewing_angle_h_deg: Horizontal viewing half-angle (degrees)
        viewing_angle_v_deg: Vertical viewing half-angle (degrees)

    Returns:
        Beam concentration factor (1.0 for Lambertian)
    """
    # Clamp angles
    angle_h = max(1.0, min(180.0, viewing_angle_h_deg))
    angle_v = max(1.0, min(180.0, viewing_angle_v_deg))

    # Convert to radians
    theta_h = math.radians(angle_h)
    theta_v = math.radians(angle_v)

    # Solid angle approximation for rectangular emission pattern
    # Full hemisphere = 2π steradians
    # For angles << 180°, solid angle ≈ π × sin²(θ)

    # Lambertian solid angle
    lambertian_solid_angle = 2 * math.pi  # Full hemisphere

    # Actual solid angle (approximate for rectangular pattern)
    actual_solid_angle = math.pi * math.sin(theta_h) * math.sin(theta_v)

    if actual_solid_angle <= 0:
        return 1.0

    # Beam factor: how much brighter the on-axis luminance is
    # compared to if the same flux were spread over a hemisphere
    factor = lambertian_solid_angle / (2 * actual_solid_angle)

    # Clamp to reasonable range
    return max(1.0, min(factor, 100.0))


def nits_to_omniverse_intensity(
    nits: float,
    target_exposure: float = 0.0
) -> Tuple[float, float]:
    """
    Convert luminance in nits to Omniverse intensity + exposure values.

    Since LEDs can be extremely bright (100,000+ nits), we use both
    intensity and exposure to represent the value accurately.

    Strategy:
    - If user specifies a target exposure, adjust intensity to match
    - Otherwise, choose exposure to keep intensity in 0.1 - 1000 range

    Omniverse formula: effective_nits = intensity × 2^exposure

    Args:
        nits: Target luminance in nits (cd/m²)
        target_exposure: If specified, use this exposure value

    Returns:
        Tuple of (intensity, exposure) for Omniverse light
    """
    if nits <= 0:
        return (0.0, 0.0)

    if target_exposure != 0.0:
        # User specified exposure, calculate intensity
        intensity = nits / (2 ** target_exposure)
        return (intensity, target_exposure)

    # Auto-calculate exposure to keep intensity reasonable
    # Target intensity range: 0.1 to 100
    # exposure = log2(nits / intensity)

    if nits <= 100:
        # Low luminance: use intensity only
        return (nits, 0.0)
    elif nits <= 10000:
        # Medium: use some exposure
        exposure = math.floor(math.log2(nits / 10))
        intensity = nits / (2 ** exposure)
        return (intensity, exposure)
    else:
        # High luminance: need more exposure
        exposure = math.floor(math.log2(nits / 100))
        intensity = nits / (2 ** exposure)
        return (intensity, exposure)


def omniverse_intensity_to_nits(intensity: float, exposure: float = 0.0) -> float:
    """
    Convert Omniverse intensity + exposure to luminance in nits.

    Args:
        intensity: Omniverse intensity value
        exposure: Omniverse exposure value

    Returns:
        Luminance in nits (cd/m²)
    """
    return intensity * (2 ** exposure)


# =============================================================================
# LED-SPECIFIC CONVERSION FUNCTIONS
# =============================================================================

def led_spec_to_omniverse(
    luminous_intensity_mcd: float = 0.0,
    luminous_flux_mlm: float = 0.0,
    emitter_width_mm: float = 0.5,
    emitter_height_mm: float = 0.3,
    viewing_angle_h_deg: float = 120.0,
    viewing_angle_v_deg: float = 120.0,
    current_ratio: float = 1.0
) -> Tuple[float, float, float]:
    """
    Convert LED datasheet specifications to Omniverse light parameters.

    Accepts either luminous intensity (mcd) OR luminous flux (mlm).
    If both provided, uses luminous intensity (more accurate for directional).

    Args:
        luminous_intensity_mcd: Luminous intensity in millicandelas
        luminous_flux_mlm: Luminous flux in millilumens
        emitter_width_mm: LED die/emitter width in mm
        emitter_height_mm: LED die/emitter height in mm
        viewing_angle_h_deg: Horizontal viewing half-angle in degrees
        viewing_angle_v_deg: Vertical viewing half-angle in degrees
        current_ratio: Ratio of actual current to rated current (for dimming)

    Returns:
        Tuple of (intensity, exposure, nits) for Omniverse RectLight

    Example:
        OSRAM LT QH9G at rated current:
        >>> led_spec_to_omniverse(
        ...     luminous_intensity_mcd=270,
        ...     emitter_width_mm=0.5,
        ...     emitter_height_mm=0.3
        ... )
        (100.0, 13.0, 900000.0)  # intensity=100, exposure=13 → ~820k nits
    """
    emitter_area_mm2 = emitter_width_mm * emitter_height_mm

    if luminous_intensity_mcd > 0:
        # Use intensity-based calculation (preferred)
        base_nits = millicandelas_to_nits(
            luminous_intensity_mcd,
            emitter_area_mm2,
            viewing_angle_h_deg,
            viewing_angle_v_deg
        )
    elif luminous_flux_mlm > 0:
        # Fallback to flux-based calculation
        base_nits = millilumens_to_nits(
            luminous_flux_mlm,
            emitter_area_mm2,
            viewing_angle_h_deg,
            viewing_angle_v_deg
        )
    else:
        logger.warning("No luminous data provided, using default")
        base_nits = 10000.0  # Typical LED fallback

    # Apply current ratio (LED brightness roughly linear with current)
    actual_nits = base_nits * current_ratio

    # Convert to Omniverse values
    intensity, exposure = nits_to_omniverse_intensity(actual_nits)

    logger.info(f"LED -> Omniverse: {actual_nits:.0f} nits → intensity={intensity:.2f}, exposure={exposure:.0f}")

    return (intensity, exposure, actual_nits)


def estimate_led_emitter_area(package_type: str) -> Tuple[float, float]:
    """
    Estimate LED emitter (die) dimensions based on package type.

    Die size is typically smaller than package size.
    These are typical estimates - actual values vary by manufacturer.

    Args:
        package_type: LED package designator (e.g., "0402", "0603", "3528")

    Returns:
        Tuple of (width_mm, height_mm) for the emitter area
    """
    # Common LED package sizes and estimated die dimensions
    # Format: package -> (die_width, die_height) in mm
    packages = {
        # Chip LEDs
        "0201": (0.2, 0.1),    # 0.6 × 0.3mm package
        "0402": (0.5, 0.3),    # 1.0 × 0.5mm package (LT QH9G)
        "0603": (0.8, 0.5),    # 1.6 × 0.8mm package
        "0805": (1.2, 0.8),    # 2.0 × 1.25mm package
        "1206": (2.0, 1.2),    # 3.2 × 1.6mm package

        # SMD LEDs
        "2835": (2.0, 2.0),    # 2.8 × 3.5mm package
        "3528": (2.5, 2.5),    # 3.5 × 2.8mm package
        "5050": (4.0, 4.0),    # 5.0 × 5.0mm package
        "5730": (4.5, 2.5),    # 5.7 × 3.0mm package

        # Through-hole
        "3mm": (0.5, 0.5),     # 3mm dome LED
        "5mm": (1.0, 1.0),     # 5mm dome LED
        "10mm": (2.0, 2.0),    # 10mm dome LED

        # COB (Chip-on-Board)
        "cob_small": (5.0, 5.0),
        "cob_medium": (10.0, 10.0),
        "cob_large": (20.0, 20.0),
    }

    result = packages.get(package_type.lower(), (1.0, 1.0))
    logger.debug(f"Package {package_type} → estimated emitter: {result[0]}mm × {result[1]}mm")
    return result


# =============================================================================
# VISION DT ATTRIBUTE HELPERS
# =============================================================================

def calculate_visiondt_luminous_intensity(
    light_prim,
    use_mcd: bool = True
) -> Tuple[float, float]:
    """
    Calculate Omniverse intensity/exposure from Vision DT LED attributes.

    Reads visiondt:led: attributes from the light prim and calculates
    the appropriate Omniverse intensity and exposure values.

    Args:
        light_prim: USD Prim with Vision DT LED attributes
        use_mcd: If True, prefer mcd over mlm for calculation

    Returns:
        Tuple of (intensity, exposure) for Omniverse light
    """
    try:
        # Get LED attributes
        def get_attr(name, default=0.0):
            attr = light_prim.GetAttribute(f"visiondt:led:{name}")
            return attr.Get() if attr and attr.IsValid() else default

        # Check if luminous mode is enabled
        use_luminous = get_attr("useLuminousIntensity", False)
        if not use_luminous:
            return None  # Not using Vision DT luminous control

        mcd = get_attr("luminousIntensity", 0.0)
        mlm = get_attr("luminousFlux", 0.0)
        angle_h = get_attr("viewingAngleH", 120.0)
        angle_v = get_attr("viewingAngleV", 120.0)

        # Estimate emitter area from RectLight dimensions
        width_attr = light_prim.GetAttribute("inputs:width")
        height_attr = light_prim.GetAttribute("inputs:height")

        emitter_width = width_attr.Get() if width_attr else 1.0
        emitter_height = height_attr.Get() if height_attr else 1.0

        # Calculate Omniverse values
        intensity, exposure, nits = led_spec_to_omniverse(
            luminous_intensity_mcd=mcd if use_mcd else 0.0,
            luminous_flux_mlm=mlm if not use_mcd or mcd <= 0 else 0.0,
            emitter_width_mm=emitter_width,
            emitter_height_mm=emitter_height,
            viewing_angle_h_deg=angle_h,
            viewing_angle_v_deg=angle_v
        )

        return (intensity, exposure)

    except Exception as e:
        logger.error(f"Failed to calculate luminous intensity: {e}")
        return None


def apply_visiondt_luminous_to_light(
    light_prim,
    intensity: float,
    exposure: float
) -> bool:
    """
    Apply calculated intensity/exposure to a light prim.

    This overrides Omniverse's default intensity with Vision DT values.

    Args:
        light_prim: USD light prim
        intensity: Calculated intensity value
        exposure: Calculated exposure value

    Returns:
        True if successfully applied
    """
    try:
        # Set intensity
        intensity_attr = light_prim.GetAttribute("inputs:intensity")
        if intensity_attr:
            intensity_attr.Set(intensity)
            logger.debug(f"Set intensity={intensity:.2f} on {light_prim.GetPath()}")

        # Set exposure
        exposure_attr = light_prim.GetAttribute("inputs:exposure")
        if exposure_attr:
            exposure_attr.Set(exposure)
            logger.debug(f"Set exposure={exposure:.1f} on {light_prim.GetPath()}")
        else:
            # Create exposure attribute if it doesn't exist
            from pxr import Sdf
            exposure_attr = light_prim.CreateAttribute(
                "inputs:exposure",
                Sdf.ValueTypeNames.Float,
                custom=False  # This is a standard UsdLux attribute
            )
            if exposure_attr:
                exposure_attr.Set(exposure)

        return True

    except Exception as e:
        logger.error(f"Failed to apply luminous values: {e}")
        return False


# =============================================================================
# REFERENCE DATA
# =============================================================================

# Common LED luminous intensity values for reference (at rated current)
LED_REFERENCE_VALUES = {
    "osram_lt_qh9g": {
        "description": "OSRAM True Green 0402",
        "mcd_min": 90,
        "mcd_typ": 270,
        "mcd_max": 450,
        "mlm_min": 300,
        "mlm_typ": 600,
        "mlm_max": 1210,
        "current_ma": 5,
        "package": "0402"
    },
    "typical_indicator": {
        "description": "Typical indicator LED",
        "mcd_typ": 50,
        "mlm_typ": 150,
        "current_ma": 20,
        "package": "0603"
    },
    "high_power_white": {
        "description": "High-power white LED",
        "mcd_typ": 5000,
        "mlm_typ": 100000,  # 100 lm
        "current_ma": 350,
        "package": "3535"
    }
}


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("Luminous Conversion Utilities Test")
    print("=" * 60)

    # Test with OSRAM LT QH9G
    print("\nTest Case: OSRAM LT QH9G")
    print("  Luminous Intensity: 270 mcd (typical)")
    print("  Package: 0402 (die ~0.5mm × 0.3mm)")
    print("  Viewing Angle: 170° × 115° (half: 85° × 57.5°)")

    intensity, exposure, nits = led_spec_to_omniverse(
        luminous_intensity_mcd=270,
        emitter_width_mm=0.5,
        emitter_height_mm=0.3,
        viewing_angle_h_deg=85,
        viewing_angle_v_deg=57.5
    )

    print(f"\nResult:")
    print(f"  Luminance: {nits:,.0f} nits")
    print(f"  Omniverse intensity: {intensity:.2f}")
    print(f"  Omniverse exposure: {exposure:.1f}")
    print(f"  Effective: {intensity * (2**exposure):,.0f} nits")

    # Test different LED brightness groups
    print("\n" + "=" * 60)
    print("OSRAM LT QH9G Brightness Groups")
    print("=" * 60)

    groups = [
        ("Q2", 90, 300),
        ("R1", 126, 420),
        ("S1", 200, 670),
        ("T2", 400, 1100),
    ]

    for group, mcd, mlm in groups:
        intensity, exposure, nits = led_spec_to_omniverse(
            luminous_intensity_mcd=mcd,
            emitter_width_mm=0.5,
            emitter_height_mm=0.3,
            viewing_angle_h_deg=85,
            viewing_angle_v_deg=57.5
        )
        print(f"  {group}: {mcd}mcd → intensity={intensity:.1f}, exp={exposure:.0f} ({nits:,.0f} nits)")

    print("\n" + "=" * 60)
    print("Test complete")
    print("=" * 60)




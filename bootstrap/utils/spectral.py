"""
Spectral Utility Functions for LED Wavelength Processing

Provides functions for converting LED wavelength/spectral data to RGB colors
for use in Omniverse rendering.

Key Features:
- Full Gaussian SPD integration (not just peak wavelength)
- SpectralCurve class for importing raw spectral data
- Normal distribution around peak wavelength as default
- Future-ready architecture for raw curve matching

Key Functions:
- wavelength_to_xyz(): Single wavelength to CIE XYZ
- gaussian_spd(): Generate Gaussian spectral power distribution
- spd_to_xyz(): Integrate SPD to CIE XYZ
- xyz_to_linear_rgb(): Convert XYZ to linear sRGB
- led_wavelength_to_rgb(): All-in-one LED parameters to RGB

Classes:
- SpectralCurve: Represents an LED spectral emission curve
  - Supports Gaussian approximation (default)
  - Supports raw imported data points
  - Future: curve matching from datasheet images

Based on CIE 1931 2° Standard Observer color matching functions.

Updated: 2025-12-05 - Always use full Gaussian SPD, added SpectralCurve class
"""

import math
import logging
from typing import Optional, List, Tuple, Callable, Dict, Any
from pxr import Gf

logger = logging.getLogger("vision_dt.spectral")


# =============================================================================
# SPECTRAL CURVE CLASS - For future raw curve imports
# =============================================================================

class SpectralCurve:
    """
    Represents an LED spectral emission curve.

    Supports two modes:
    1. Gaussian approximation (default) - uses peak wavelength and FWHM
    2. Raw data points - for imported spectral curves from datasheets

    The curve can be evaluated at any wavelength to get relative intensity.

    Future: Add methods for:
    - Importing from CSV/JSON files
    - Extracting curves from datasheet images
    - Curve fitting and matching

    Usage:
        # Gaussian mode (default)
        curve = SpectralCurve.from_gaussian(peak_nm=530, fwhm_nm=33)
        intensity = curve.evaluate(520)  # Get intensity at 520nm
        rgb = curve.to_rgb()  # Get RGB color

        # Raw data mode (future)
        curve = SpectralCurve.from_data_points(wavelengths, intensities)
    """

    # Curve types
    TYPE_GAUSSIAN = "gaussian"
    TYPE_RAW_DATA = "raw_data"
    TYPE_MULTI_PEAK = "multi_peak"  # For phosphor-converted LEDs

    def __init__(
        self,
        curve_type: str = TYPE_GAUSSIAN,
        peak_nm: float = 550.0,
        fwhm_nm: float = 30.0,
        dominant_nm: Optional[float] = None,
        data_points: Optional[List[Tuple[float, float]]] = None,
        name: str = "Unknown",
        manufacturer: str = "",
        model: str = ""
    ):
        """
        Initialize a SpectralCurve.

        Args:
            curve_type: Type of curve representation
            peak_nm: Peak emission wavelength (nm)
            fwhm_nm: Full Width at Half Maximum (nm)
            dominant_nm: Dominant wavelength for color perception (nm)
            data_points: List of (wavelength, relative_intensity) tuples
            name: Display name for the curve
            manufacturer: LED manufacturer
            model: LED model/part number
        """
        self.curve_type = curve_type
        self.peak_nm = peak_nm
        self.fwhm_nm = max(1.0, fwhm_nm)  # Minimum 1nm to avoid division by zero
        self.dominant_nm = dominant_nm if dominant_nm else peak_nm
        self.data_points = data_points or []
        self.name = name
        self.manufacturer = manufacturer
        self.model = model

        # Cached values
        self._xyz_cache: Optional[Tuple[float, float, float]] = None
        self._rgb_cache: Optional[Gf.Vec3f] = None

        # For Gaussian curves, calculate sigma from FWHM
        # FWHM = 2 * sqrt(2 * ln(2)) * sigma ≈ 2.355 * sigma
        self._sigma = self.fwhm_nm / 2.355

        # If raw data provided, build interpolation lookup
        if data_points and len(data_points) >= 2:
            self._build_interpolation_tables()

    def _build_interpolation_tables(self):
        """Build lookup tables for fast interpolation of raw data."""
        if not self.data_points:
            return

        # Sort by wavelength
        sorted_points = sorted(self.data_points, key=lambda x: x[0])
        self._wavelengths = [p[0] for p in sorted_points]
        self._intensities = [p[1] for p in sorted_points]

        # Normalize to max = 1.0
        max_intensity = max(self._intensities) if self._intensities else 1.0
        if max_intensity > 0:
            self._intensities = [i / max_intensity for i in self._intensities]

    @classmethod
    def from_gaussian(
        cls,
        peak_nm: float,
        fwhm_nm: float = 30.0,
        dominant_nm: Optional[float] = None,
        name: str = "Gaussian LED",
        manufacturer: str = "",
        model: str = ""
    ) -> "SpectralCurve":
        """
        Create a SpectralCurve with Gaussian distribution.

        This is the default and most common mode for LEDs.

        Args:
            peak_nm: Peak emission wavelength (nm)
            fwhm_nm: Full Width at Half Maximum (nm), default 30nm
            dominant_nm: Dominant wavelength (nm), defaults to peak
            name: Display name
            manufacturer: LED manufacturer
            model: LED model/part number

        Returns:
            SpectralCurve instance
        """
        return cls(
            curve_type=cls.TYPE_GAUSSIAN,
            peak_nm=peak_nm,
            fwhm_nm=fwhm_nm,
            dominant_nm=dominant_nm,
            name=name,
            manufacturer=manufacturer,
            model=model
        )

    @classmethod
    def from_data_points(
        cls,
        wavelengths: List[float],
        intensities: List[float],
        name: str = "Imported Curve",
        manufacturer: str = "",
        model: str = ""
    ) -> "SpectralCurve":
        """
        Create a SpectralCurve from raw data points.

        Use this when you have actual spectral measurements or
        data extracted from datasheets.

        Args:
            wavelengths: List of wavelengths in nm
            intensities: List of relative intensities (0-1 or will be normalized)
            name: Display name
            manufacturer: LED manufacturer
            model: LED model/part number

        Returns:
            SpectralCurve instance
        """
        if len(wavelengths) != len(intensities):
            raise ValueError("wavelengths and intensities must have same length")

        data_points = list(zip(wavelengths, intensities))

        # Find peak from data
        max_idx = intensities.index(max(intensities))
        peak_nm = wavelengths[max_idx]

        # Estimate FWHM from data
        fwhm_nm = cls._estimate_fwhm(wavelengths, intensities)

        return cls(
            curve_type=cls.TYPE_RAW_DATA,
            peak_nm=peak_nm,
            fwhm_nm=fwhm_nm,
            dominant_nm=None,  # Would need CIE calculation
            data_points=data_points,
            name=name,
            manufacturer=manufacturer,
            model=model
        )

    @staticmethod
    def _estimate_fwhm(wavelengths: List[float], intensities: List[float]) -> float:
        """Estimate FWHM from raw data points."""
        if not intensities:
            return 30.0

        max_intensity = max(intensities)
        half_max = max_intensity / 2.0

        # Find wavelengths where intensity crosses half-max
        above_half = [w for w, i in zip(wavelengths, intensities) if i >= half_max]

        if len(above_half) >= 2:
            return max(above_half) - min(above_half)

        return 30.0  # Default fallback

    def evaluate(self, wavelength_nm: float) -> float:
        """
        Evaluate the spectral curve at a given wavelength.

        Args:
            wavelength_nm: Wavelength in nanometers

        Returns:
            Relative intensity (0.0 to 1.0)
        """
        if self.curve_type == self.TYPE_GAUSSIAN:
            return self._evaluate_gaussian(wavelength_nm)
        elif self.curve_type == self.TYPE_RAW_DATA:
            return self._evaluate_raw(wavelength_nm)
        else:
            return self._evaluate_gaussian(wavelength_nm)

    def _evaluate_gaussian(self, wavelength_nm: float) -> float:
        """Evaluate Gaussian distribution at wavelength."""
        if self._sigma <= 0:
            return 1.0 if abs(wavelength_nm - self.peak_nm) < 0.5 else 0.0

        exponent = -0.5 * ((wavelength_nm - self.peak_nm) / self._sigma) ** 2
        return math.exp(exponent)

    def _evaluate_raw(self, wavelength_nm: float) -> float:
        """Evaluate raw data curve using linear interpolation."""
        if not hasattr(self, '_wavelengths') or not self._wavelengths:
            return self._evaluate_gaussian(wavelength_nm)

        # Handle out of range
        if wavelength_nm <= self._wavelengths[0]:
            return self._intensities[0]
        if wavelength_nm >= self._wavelengths[-1]:
            return self._intensities[-1]

        # Find surrounding points and interpolate
        for i in range(len(self._wavelengths) - 1):
            if self._wavelengths[i] <= wavelength_nm <= self._wavelengths[i + 1]:
                t = (wavelength_nm - self._wavelengths[i]) / (
                    self._wavelengths[i + 1] - self._wavelengths[i]
                )
                return (
                    self._intensities[i] +
                    t * (self._intensities[i + 1] - self._intensities[i])
                )

        return 0.0

    def to_xyz(
        self,
        wavelength_start: float = 380.0,
        wavelength_end: float = 780.0,
        step: float = 5.0
    ) -> Tuple[float, float, float]:
        """
        Convert spectral curve to CIE XYZ coordinates.

        Integrates the spectral curve weighted by CIE color matching functions.

        Args:
            wavelength_start: Start of integration range (nm)
            wavelength_end: End of integration range (nm)
            step: Integration step size (nm)

        Returns:
            Tuple (X, Y, Z) - CIE XYZ coordinates (normalized so Y=1)
        """
        if self._xyz_cache is not None:
            return self._xyz_cache

        X, Y, Z = 0.0, 0.0, 0.0

        wavelength = wavelength_start
        while wavelength <= wavelength_end:
            # Get SPD value at this wavelength
            spd_value = self.evaluate(wavelength)

            # Get color matching function values
            x_bar, y_bar, z_bar = interpolate_cmf(wavelength)

            # Accumulate (numerical integration)
            X += spd_value * x_bar * step
            Y += spd_value * y_bar * step
            Z += spd_value * z_bar * step

            wavelength += step

        # Normalize so Y = 1
        if Y > 0:
            scale = 1.0 / Y
            X *= scale
            Y = 1.0
            Z *= scale

        self._xyz_cache = (X, Y, Z)
        return (X, Y, Z)

    def to_rgb(self) -> Gf.Vec3f:
        """
        Convert spectral curve to linear RGB color.

        Returns:
            Gf.Vec3f: Linear RGB values (normalized to 0-1)
        """
        if self._rgb_cache is not None:
            return self._rgb_cache

        X, Y, Z = self.to_xyz()
        rgb = xyz_to_linear_rgb(X, Y, Z)
        rgb = normalize_rgb(rgb, preserve_hue=True)

        self._rgb_cache = rgb
        return rgb

    def get_color_data(self) -> Dict[str, Any]:
        """
        Get comprehensive color data for this curve.

        Returns:
            Dict with XYZ, RGB, and curve parameters
        """
        X, Y, Z = self.to_xyz()
        rgb = self.to_rgb()

        return {
            "curve_type": self.curve_type,
            "peak_nm": self.peak_nm,
            "dominant_nm": self.dominant_nm,
            "fwhm_nm": self.fwhm_nm,
            "xyz": {"X": X, "Y": Y, "Z": Z},
            "rgb": {"r": rgb[0], "g": rgb[1], "b": rgb[2]},
            "manufacturer": self.manufacturer,
            "model": self.model,
            "name": self.name
        }

    def invalidate_cache(self):
        """Clear cached values (call after modifying curve parameters)."""
        self._xyz_cache = None
        self._rgb_cache = None

    def __repr__(self):
        return (
            f"SpectralCurve({self.name}, "
            f"λpeak={self.peak_nm}nm, "
            f"FWHM={self.fwhm_nm}nm, "
            f"type={self.curve_type})"
        )

# CIE 1931 2° Standard Observer Color Matching Functions
# Wavelength range: 380-780 nm in 5 nm steps
# Data from CIE standards (abbreviated for common visible range)
# Format: wavelength_nm: (x_bar, y_bar, z_bar)
CIE_1931_CMF = {
    380: (0.001368, 0.000039, 0.006450),
    385: (0.002236, 0.000064, 0.010550),
    390: (0.004243, 0.000120, 0.020050),
    395: (0.007650, 0.000217, 0.036210),
    400: (0.014310, 0.000396, 0.067850),
    405: (0.023190, 0.000640, 0.110200),
    410: (0.043510, 0.001210, 0.207400),
    415: (0.077630, 0.002180, 0.371300),
    420: (0.134380, 0.004000, 0.645600),
    425: (0.214770, 0.007300, 1.039050),
    430: (0.283900, 0.011600, 1.385600),
    435: (0.328500, 0.016840, 1.622960),
    440: (0.348280, 0.023000, 1.747060),
    445: (0.348060, 0.029800, 1.782600),
    450: (0.336200, 0.038000, 1.772110),
    455: (0.318700, 0.048000, 1.744100),
    460: (0.290800, 0.060000, 1.669200),
    465: (0.251100, 0.073900, 1.528100),
    470: (0.195360, 0.090980, 1.287640),
    475: (0.142100, 0.112600, 1.041900),
    480: (0.095640, 0.139020, 0.812950),
    485: (0.058010, 0.169300, 0.616200),
    490: (0.032010, 0.208020, 0.465180),
    495: (0.014700, 0.258600, 0.353300),
    500: (0.004900, 0.323000, 0.272000),
    505: (0.002400, 0.407300, 0.212300),
    510: (0.009300, 0.503000, 0.158200),
    515: (0.029100, 0.608200, 0.111700),
    520: (0.063270, 0.710000, 0.078250),
    525: (0.109600, 0.793200, 0.057250),
    530: (0.165500, 0.862000, 0.042160),
    535: (0.225750, 0.914850, 0.029840),
    540: (0.290400, 0.954000, 0.020300),
    545: (0.359700, 0.980300, 0.013400),
    550: (0.433450, 0.994950, 0.008750),
    555: (0.512050, 1.000000, 0.005750),
    560: (0.594500, 0.995000, 0.003900),
    565: (0.678400, 0.978600, 0.002750),
    570: (0.762100, 0.952000, 0.002100),
    575: (0.842500, 0.915400, 0.001800),
    580: (0.916300, 0.870000, 0.001650),
    585: (0.978600, 0.816300, 0.001400),
    590: (1.026300, 0.757000, 0.001100),
    595: (1.056700, 0.694900, 0.001000),
    600: (1.062200, 0.631000, 0.000800),
    605: (1.045600, 0.566800, 0.000600),
    610: (1.002600, 0.503000, 0.000340),
    615: (0.938400, 0.441200, 0.000240),
    620: (0.854450, 0.381000, 0.000190),
    625: (0.751400, 0.321000, 0.000100),
    630: (0.642400, 0.265000, 0.000050),
    635: (0.541900, 0.217000, 0.000030),
    640: (0.447900, 0.175000, 0.000020),
    645: (0.360800, 0.138200, 0.000010),
    650: (0.283500, 0.107000, 0.000000),
    655: (0.218700, 0.081600, 0.000000),
    660: (0.164900, 0.061000, 0.000000),
    665: (0.121200, 0.044580, 0.000000),
    670: (0.087400, 0.032000, 0.000000),
    675: (0.063600, 0.023200, 0.000000),
    680: (0.046770, 0.017000, 0.000000),
    685: (0.032900, 0.011920, 0.000000),
    690: (0.022700, 0.008210, 0.000000),
    695: (0.015840, 0.005723, 0.000000),
    700: (0.011359, 0.004102, 0.000000),
    705: (0.008111, 0.002929, 0.000000),
    710: (0.005790, 0.002091, 0.000000),
    715: (0.004109, 0.001484, 0.000000),
    720: (0.002899, 0.001047, 0.000000),
    725: (0.002049, 0.000740, 0.000000),
    730: (0.001440, 0.000520, 0.000000),
    735: (0.001000, 0.000361, 0.000000),
    740: (0.000690, 0.000249, 0.000000),
    745: (0.000476, 0.000172, 0.000000),
    750: (0.000332, 0.000120, 0.000000),
    755: (0.000235, 0.000085, 0.000000),
    760: (0.000166, 0.000060, 0.000000),
    765: (0.000117, 0.000042, 0.000000),
    770: (0.000083, 0.000030, 0.000000),
    775: (0.000059, 0.000021, 0.000000),
    780: (0.000042, 0.000015, 0.000000),
}

# sRGB to XYZ conversion matrix (D65 illuminant)
# Inverse of XYZ to sRGB matrix
SRGB_TO_XYZ = [
    [0.4124564, 0.3575761, 0.1804375],
    [0.2126729, 0.7151522, 0.0721750],
    [0.0193339, 0.1191920, 0.9503041]
]

# XYZ to sRGB conversion matrix (D65 illuminant)
XYZ_TO_SRGB = [
    [ 3.2404542, -1.5371385, -0.4985314],
    [-0.9692660,  1.8760108,  0.0415560],
    [ 0.0556434, -0.2040259,  1.0572252]
]


def clamp(x, min_val=0.0, max_val=1.0):
    """Clamp a value to a range."""
    return max(min_val, min(x, max_val))


def interpolate_cmf(wavelength_nm):
    """
    Interpolate CIE 1931 color matching functions for any wavelength.

    Args:
        wavelength_nm: Wavelength in nanometers (380-780)

    Returns:
        Tuple (x_bar, y_bar, z_bar) or (0, 0, 0) if out of range
    """
    if wavelength_nm < 380 or wavelength_nm > 780:
        return (0.0, 0.0, 0.0)

    # Find surrounding data points
    lower_wl = int(wavelength_nm // 5) * 5
    upper_wl = lower_wl + 5

    # Clamp to data range
    lower_wl = max(380, min(lower_wl, 780))
    upper_wl = max(380, min(upper_wl, 780))

    if lower_wl == upper_wl:
        return CIE_1931_CMF.get(lower_wl, (0.0, 0.0, 0.0))

    # Linear interpolation
    t = (wavelength_nm - lower_wl) / (upper_wl - lower_wl)

    lower_vals = CIE_1931_CMF.get(lower_wl, (0.0, 0.0, 0.0))
    upper_vals = CIE_1931_CMF.get(upper_wl, (0.0, 0.0, 0.0))

    x = lower_vals[0] + t * (upper_vals[0] - lower_vals[0])
    y = lower_vals[1] + t * (upper_vals[1] - lower_vals[1])
    z = lower_vals[2] + t * (upper_vals[2] - lower_vals[2])

    return (x, y, z)


def wavelength_to_xyz(wavelength_nm):
    """
    Convert a single wavelength to CIE XYZ coordinates.

    For monochromatic light, the chromaticity is determined by the
    color matching functions at that wavelength.

    Args:
        wavelength_nm: Wavelength in nanometers

    Returns:
        Tuple (X, Y, Z) - CIE XYZ coordinates (normalized)
    """
    x, y, z = interpolate_cmf(wavelength_nm)

    # Normalize so Y = 1 (for relative colorimetry)
    if y > 0:
        scale = 1.0 / y
        return (x * scale, 1.0, z * scale)

    return (x, y, z)


def gaussian_spd(wavelength_nm, peak_nm, fwhm_nm):
    """
    Calculate Gaussian spectral power distribution value at a wavelength.

    LEDs have approximately Gaussian spectral output. This function
    generates the relative power at a given wavelength.

    Args:
        wavelength_nm: Wavelength to evaluate
        peak_nm: Peak wavelength of LED
        fwhm_nm: Full Width at Half Maximum (bandwidth)

    Returns:
        Relative spectral power (0.0 to 1.0)
    """
    # Convert FWHM to standard deviation
    # FWHM = 2 * sqrt(2 * ln(2)) * sigma ≈ 2.355 * sigma
    sigma = fwhm_nm / 2.355

    if sigma <= 0:
        # If no bandwidth specified, treat as monochromatic
        return 1.0 if abs(wavelength_nm - peak_nm) < 0.5 else 0.0

    # Gaussian function
    exponent = -0.5 * ((wavelength_nm - peak_nm) / sigma) ** 2
    return math.exp(exponent)


def spd_to_xyz(peak_nm, fwhm_nm, wavelength_start=380, wavelength_end=780, step=5):
    """
    Integrate a Gaussian SPD to get CIE XYZ coordinates.

    Args:
        peak_nm: Peak wavelength of LED
        fwhm_nm: Full Width at Half Maximum (bandwidth)
        wavelength_start: Start of integration range (nm)
        wavelength_end: End of integration range (nm)
        step: Integration step size (nm)

    Returns:
        Tuple (X, Y, Z) - CIE XYZ coordinates
    """
    X, Y, Z = 0.0, 0.0, 0.0

    wavelength = wavelength_start
    while wavelength <= wavelength_end:
        # Get SPD value at this wavelength
        spd_value = gaussian_spd(wavelength, peak_nm, fwhm_nm)

        # Get color matching function values
        x_bar, y_bar, z_bar = interpolate_cmf(wavelength)

        # Accumulate (numerical integration)
        X += spd_value * x_bar * step
        Y += spd_value * y_bar * step
        Z += spd_value * z_bar * step

        wavelength += step

    return (X, Y, Z)


def xyz_to_linear_rgb(X, Y, Z):
    """
    Convert CIE XYZ to linear sRGB.

    Uses the standard XYZ to sRGB matrix for D65 illuminant.

    Args:
        X, Y, Z: CIE XYZ coordinates

    Returns:
        Gf.Vec3f: Linear RGB values (may exceed 0-1 for out-of-gamut colors)
    """
    # Matrix multiplication
    r = XYZ_TO_SRGB[0][0] * X + XYZ_TO_SRGB[0][1] * Y + XYZ_TO_SRGB[0][2] * Z
    g = XYZ_TO_SRGB[1][0] * X + XYZ_TO_SRGB[1][1] * Y + XYZ_TO_SRGB[1][2] * Z
    b = XYZ_TO_SRGB[2][0] * X + XYZ_TO_SRGB[2][1] * Y + XYZ_TO_SRGB[2][2] * Z

    return Gf.Vec3f(r, g, b)


def normalize_rgb(rgb, preserve_hue=True):
    """
    Normalize RGB values to 0-1 range.

    Args:
        rgb: Gf.Vec3f RGB values
        preserve_hue: If True, scale all channels equally to preserve hue
                      If False, clamp each channel independently

    Returns:
        Gf.Vec3f: Normalized RGB values (0-1)
    """
    r, g, b = rgb[0], rgb[1], rgb[2]

    if preserve_hue:
        # Scale all channels by the maximum to preserve hue
        max_val = max(r, g, b)
        if max_val > 1.0:
            r /= max_val
            g /= max_val
            b /= max_val
        # Also handle negative values (out of gamut)
        min_val = min(r, g, b)
        if min_val < 0:
            # Shift to positive (desaturates the color)
            r -= min_val
            g -= min_val
            b -= min_val
            # Re-normalize if needed
            max_val = max(r, g, b)
            if max_val > 1.0:
                r /= max_val
                g /= max_val
                b /= max_val
    else:
        # Simple clamp
        r = clamp(r)
        g = clamp(g)
        b = clamp(b)

    return Gf.Vec3f(r, g, b)


def led_wavelength_to_rgb(peak_nm, fwhm_nm=30.0, dominant_nm=None, use_full_spd=True, white_mix=0.0):
    """
    Convert LED wavelength parameters to linear RGB color.

    Supports two modes:
    1. Pure monochromatic LED (white_mix=0.0): Saturated color from Gaussian SPD
    2. White with spectral peak (white_mix>0): Blends with D65 white for realistic lighting

    Args:
        peak_nm: Peak emission wavelength (nm)
        fwhm_nm: Full Width at Half Maximum bandwidth (nm)
                 Default 30nm (typical for LEDs)
                 If 0 or very small, uses minimum 5nm bandwidth
        dominant_nm: Dominant wavelength (nm) - optional
                     If provided, uses this for color calculation
        use_full_spd: If True (default), ALWAYS integrate full Gaussian SPD
                      If False, use single wavelength for very narrow bands
        white_mix: How much to blend with white (D65 illuminant)
                   0.0 = pure monochromatic LED color (saturated)
                   0.5 = 50% white, 50% LED color (tinted white)
                   0.8 = mostly white with slight color shift (default for realistic lighting)
                   1.0 = pure white (ignores wavelength)

    Returns:
        Gf.Vec3f: Linear RGB color (normalized to 0-1)

    Examples:
        # Pure green LED (saturated)
        led_wavelength_to_rgb(530, 33, white_mix=0.0)  # → bright green

        # White light with green peak (realistic)
        led_wavelength_to_rgb(530, 33, white_mix=0.7)  # → white with green tint

        # Vision DT default: white light shifted by peak wavelength
        led_wavelength_to_rgb(500, 30, white_mix=0.8)  # → white with slight cyan
    """
    # Validate inputs
    if peak_nm is None or peak_nm <= 0:
        logger.warning("Invalid peak wavelength, defaulting to 550nm (green)")
        peak_nm = 550.0

    # Use dominant wavelength if provided (more perceptually accurate)
    color_wavelength = dominant_nm if dominant_nm and dominant_nm > 0 else peak_nm

    # Clamp to visible range (allow some UV/IR for sensor simulation)
    color_wavelength = clamp(color_wavelength, 350.0, 800.0)

    # Ensure minimum bandwidth - LEDs always have some spectral width
    # Even "monochromatic" laser LEDs have ~1-5nm bandwidth
    if fwhm_nm is None or fwhm_nm <= 0:
        fwhm_nm = 5.0  # Minimum realistic bandwidth
    else:
        fwhm_nm = max(5.0, fwhm_nm)  # Enforce minimum

    # Clamp white_mix to valid range
    if white_mix is None:
        white_mix = 0.0
    white_mix = clamp(white_mix, 0.0, 1.0)

    # Calculate the spectral (saturated) color
    if use_full_spd:
        # Create SpectralCurve and get RGB
        curve = SpectralCurve.from_gaussian(
            peak_nm=color_wavelength,
            fwhm_nm=fwhm_nm,
            dominant_nm=dominant_nm
        )
        spectral_rgb = curve.to_rgb()
    else:
        # Fallback: single wavelength (less accurate, but faster)
        X, Y, Z = wavelength_to_xyz(color_wavelength)
        spectral_rgb = xyz_to_linear_rgb(X, Y, Z)
        spectral_rgb = normalize_rgb(spectral_rgb, preserve_hue=True)

    # If white_mix is 0, return pure spectral color (saturated LED)
    if white_mix <= 0.0:
        logger.debug(
            f"LED Pure Spectral: λ={color_wavelength}nm, FWHM={fwhm_nm}nm "
            f"-> RGB=({spectral_rgb[0]:.4f}, {spectral_rgb[1]:.4f}, {spectral_rgb[2]:.4f})"
        )
        return spectral_rgb

    # If white_mix is 1, return pure white (D65)
    if white_mix >= 1.0:
        return Gf.Vec3f(1.0, 1.0, 1.0)

    # Blend spectral color with white (D65 illuminant = 1.0, 1.0, 1.0 in linear sRGB)
    # This creates a "white light with spectral peak" effect
    white = Gf.Vec3f(1.0, 1.0, 1.0)

    # Linear interpolation: result = white * white_mix + spectral * (1 - white_mix)
    r = white[0] * white_mix + spectral_rgb[0] * (1.0 - white_mix)
    g = white[1] * white_mix + spectral_rgb[1] * (1.0 - white_mix)
    b = white[2] * white_mix + spectral_rgb[2] * (1.0 - white_mix)

    # Normalize to ensure max = 1.0 (preserve hue)
    rgb = Gf.Vec3f(r, g, b)
    rgb = normalize_rgb(rgb, preserve_hue=True)

    logger.debug(
        f"LED White-Mixed: λ={color_wavelength}nm, FWHM={fwhm_nm}nm, white_mix={white_mix:.2f} "
        f"-> RGB=({rgb[0]:.4f}, {rgb[1]:.4f}, {rgb[2]:.4f})"
    )

    return rgb


def led_wavelength_to_rgb_from_curve(curve: SpectralCurve) -> Gf.Vec3f:
    """
    Convert a SpectralCurve to linear RGB color.

    Use this when you have a SpectralCurve object (either Gaussian
    or imported raw data).

    Args:
        curve: SpectralCurve instance

    Returns:
        Gf.Vec3f: Linear RGB color (normalized to 0-1)
    """
    return curve.to_rgb()


def create_led_curve_from_datasheet(
    peak_nm: float,
    fwhm_nm: float = 30.0,
    dominant_nm: Optional[float] = None,
    manufacturer: str = "",
    model: str = ""
) -> SpectralCurve:
    """
    Create a SpectralCurve from typical datasheet parameters.

    Most LED datasheets provide:
    - Peak wavelength (λpeak)
    - Spectral bandwidth (FWHM or Δλ at 50%)
    - Dominant wavelength (λd)

    This function creates a Gaussian approximation that matches
    these parameters.

    Args:
        peak_nm: Peak emission wavelength from datasheet
        fwhm_nm: Spectral bandwidth (FWHM) from datasheet
        dominant_nm: Dominant wavelength from datasheet
        manufacturer: LED manufacturer name
        model: LED model/part number

    Returns:
        SpectralCurve configured to match datasheet parameters
    """
    return SpectralCurve.from_gaussian(
        peak_nm=peak_nm,
        fwhm_nm=fwhm_nm,
        dominant_nm=dominant_nm,
        name=f"{manufacturer} {model}".strip() or "LED",
        manufacturer=manufacturer,
        model=model
    )


def get_common_led_colors():
    """
    Return a dictionary of common LED wavelengths and their approximate colors.
    Useful for UI presets or validation.

    Returns:
        Dict mapping LED type to (peak_nm, fwhm_nm, name)
    """
    return {
        "uv_365": (365, 15, "UV 365nm"),
        "uv_385": (385, 15, "UV 385nm"),
        "uv_405": (405, 15, "Violet 405nm"),
        "blue_450": (450, 20, "Blue 450nm"),
        "cyan_505": (505, 30, "Cyan 505nm"),
        "green_520": (520, 35, "Green 520nm"),
        "true_green_530": (530, 33, "True Green 530nm"),  # LT QH9G
        "lime_555": (555, 30, "Lime 555nm"),
        "amber_590": (590, 15, "Amber 590nm"),
        "orange_605": (605, 15, "Orange 605nm"),
        "red_625": (625, 20, "Red 625nm"),
        "deep_red_660": (660, 20, "Deep Red 660nm"),
        "ir_850": (850, 40, "IR 850nm"),  # Outside visible, will appear black
        "ir_940": (940, 50, "IR 940nm"),  # Outside visible, will appear black
    }


def calculate_luminous_efficacy(wavelength_nm):
    """
    Calculate the luminous efficacy at a given wavelength.

    The photopic luminous efficacy function V(λ) peaks at 555nm with 683 lm/W.

    Args:
        wavelength_nm: Wavelength in nanometers

    Returns:
        Luminous efficacy in lm/W
    """
    # V(λ) is proportional to y_bar from color matching functions
    _, y_bar, _ = interpolate_cmf(wavelength_nm)

    # Maximum luminous efficacy is 683 lm/W at 555nm
    return 683.0 * y_bar


def flux_to_intensity(luminous_flux_lm, wavelength_nm):
    """
    Convert luminous flux to radiometric intensity for a given wavelength.

    Args:
        luminous_flux_lm: Luminous flux in lumens
        wavelength_nm: Peak wavelength in nm

    Returns:
        Radiometric power in Watts
    """
    efficacy = calculate_luminous_efficacy(wavelength_nm)
    if efficacy <= 0:
        return 0.0
    return luminous_flux_lm / efficacy


# =============================================================================
# SPECTRAL CURVE PRESETS - Common LED configurations
# =============================================================================

def get_led_curve_preset(preset_name: str) -> Optional[SpectralCurve]:
    """
    Get a predefined SpectralCurve for common LEDs.

    Available presets:
    - osram_lt_qh9g: OSRAM True Green 530nm
    - uv_365, uv_385, uv_405: UV LEDs
    - blue_450, cyan_505: Blue/Cyan LEDs
    - green_520, green_530: Green LEDs
    - lime_555: Lime/Yellow-green LED
    - amber_590, orange_605: Amber/Orange LEDs
    - red_625, red_660: Red LEDs
    - ir_850, ir_940: Infrared LEDs

    Args:
        preset_name: Name of the preset (case insensitive)

    Returns:
        SpectralCurve or None if preset not found
    """
    presets = {
        # OSRAM test case
        "osram_lt_qh9g": (525.0, 33.0, 530.0, "OSRAM", "LT QH9G"),

        # UV and violet
        "uv_365": (365.0, 15.0, 365.0, "Generic", "UV 365nm"),
        "uv_385": (385.0, 15.0, 385.0, "Generic", "UV 385nm"),
        "uv_405": (405.0, 15.0, 405.0, "Generic", "Violet 405nm"),

        # Blue and cyan
        "blue_450": (450.0, 20.0, 450.0, "Generic", "Blue 450nm"),
        "cyan_505": (505.0, 30.0, 505.0, "Generic", "Cyan 505nm"),

        # Green variants
        "green_520": (520.0, 35.0, 520.0, "Generic", "Green 520nm"),
        "green_530": (525.0, 33.0, 530.0, "Generic", "True Green 530nm"),

        # Yellow-green
        "lime_555": (555.0, 30.0, 555.0, "Generic", "Lime 555nm"),

        # Amber and orange
        "amber_590": (590.0, 15.0, 590.0, "Generic", "Amber 590nm"),
        "orange_605": (605.0, 15.0, 605.0, "Generic", "Orange 605nm"),

        # Red variants
        "red_625": (625.0, 20.0, 625.0, "Generic", "Red 625nm"),
        "red_660": (660.0, 20.0, 660.0, "Generic", "Deep Red 660nm"),

        # Infrared (will appear black in visible rendering)
        "ir_850": (850.0, 40.0, 850.0, "Generic", "IR 850nm"),
        "ir_940": (940.0, 50.0, 940.0, "Generic", "IR 940nm"),
    }

    preset = presets.get(preset_name.lower())
    if not preset:
        logger.warning(f"Unknown LED preset: {preset_name}")
        return None

    peak, fwhm, dominant, manufacturer, model = preset
    return SpectralCurve.from_gaussian(
        peak_nm=peak,
        fwhm_nm=fwhm,
        dominant_nm=dominant,
        name=model,
        manufacturer=manufacturer,
        model=model
    )


def import_spectral_data_csv(
    csv_path: str,
    wavelength_column: int = 0,
    intensity_column: int = 1,
    skip_header: bool = True,
    delimiter: str = ","
) -> Optional[SpectralCurve]:
    """
    Import spectral data from a CSV file.

    FUTURE: This function provides the interface for importing
    raw spectral curves from measurement data or digitized datasheets.

    Expected CSV format:
    wavelength_nm,relative_intensity
    380,0.01
    385,0.02
    ...

    Args:
        csv_path: Path to CSV file
        wavelength_column: Column index for wavelength data (0-based)
        intensity_column: Column index for intensity data (0-based)
        skip_header: Whether to skip the first row
        delimiter: CSV delimiter character

    Returns:
        SpectralCurve with imported data, or None on error
    """
    try:
        wavelengths = []
        intensities = []

        with open(csv_path, 'r') as f:
            lines = f.readlines()

        start_idx = 1 if skip_header else 0

        for line in lines[start_idx:]:
            parts = line.strip().split(delimiter)
            if len(parts) > max(wavelength_column, intensity_column):
                try:
                    wl = float(parts[wavelength_column])
                    intensity = float(parts[intensity_column])
                    wavelengths.append(wl)
                    intensities.append(intensity)
                except ValueError:
                    continue

        if not wavelengths:
            logger.error(f"No valid data found in {csv_path}")
            return None

        return SpectralCurve.from_data_points(
            wavelengths=wavelengths,
            intensities=intensities,
            name=f"Imported: {csv_path}"
        )

    except Exception as e:
        logger.error(f"Failed to import spectral data from {csv_path}: {e}")
        return None


# =============================================================================
# SPD DATA HANDLING - For manual entry and CSV import
# =============================================================================

def parse_spd_json(spd_json: str) -> Optional[SpectralCurve]:
    """
    Parse SPD data from a JSON string.

    JSON format:
    {
        "wavelengths": [380, 390, 400, ...],
        "intensities": [0.01, 0.02, 0.05, ...],
        "name": "My LED",
        "manufacturer": "ACME",
        "model": "LED-123"
    }

    Args:
        spd_json: JSON string containing SPD data

    Returns:
        SpectralCurve or None on error
    """
    try:
        import json
        data = json.loads(spd_json)

        wavelengths = data.get("wavelengths", [])
        intensities = data.get("intensities", [])

        if not wavelengths or not intensities:
            logger.error("SPD JSON missing wavelengths or intensities")
            return None

        if len(wavelengths) != len(intensities):
            logger.error("SPD wavelengths and intensities must have same length")
            return None

        return SpectralCurve.from_data_points(
            wavelengths=wavelengths,
            intensities=intensities,
            name=data.get("name", "JSON SPD"),
            manufacturer=data.get("manufacturer", ""),
            model=data.get("model", "")
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid SPD JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to parse SPD JSON: {e}")
        return None


def parse_spd_arrays(
    wavelengths: list,
    intensities: list,
    name: str = "Manual SPD"
) -> Optional[SpectralCurve]:
    """
    Create SpectralCurve from wavelength and intensity arrays.

    This is used when SPD data is stored as separate USD array attributes.

    Args:
        wavelengths: List of wavelengths in nm
        intensities: List of relative intensities
        name: Display name for the curve

    Returns:
        SpectralCurve or None on error
    """
    try:
        if not wavelengths or not intensities:
            logger.warning("Empty SPD arrays provided")
            return None

        if len(wavelengths) != len(intensities):
            logger.error(f"SPD array length mismatch: {len(wavelengths)} wavelengths vs {len(intensities)} intensities")
            return None

        # Convert to lists if numpy arrays or tuples
        wl_list = list(wavelengths)
        int_list = list(intensities)

        return SpectralCurve.from_data_points(
            wavelengths=wl_list,
            intensities=int_list,
            name=name
        )

    except Exception as e:
        logger.error(f"Failed to create SPD from arrays: {e}")
        return None


def spd_to_rgb(
    wavelengths: list,
    intensities: list,
    white_mix: float = 0.0
) -> Gf.Vec3f:
    """
    Convert SPD data directly to RGB color.

    This is a convenience function that combines parse_spd_arrays and to_rgb.

    Args:
        wavelengths: List of wavelengths in nm
        intensities: List of relative intensities
        white_mix: Blend factor with white (0=pure SPD color, 1=white)

    Returns:
        Gf.Vec3f: Linear RGB color (normalized to 0-1)
    """
    curve = parse_spd_arrays(wavelengths, intensities)

    if curve is None:
        # Fallback to white if SPD is invalid
        logger.warning("Invalid SPD data, returning white")
        return Gf.Vec3f(1.0, 1.0, 1.0)

    # Get RGB from SPD
    spectral_rgb = curve.to_rgb()

    # Apply white mix if specified
    if white_mix is None:
        white_mix = 0.0
    white_mix = clamp(white_mix, 0.0, 1.0)

    if white_mix <= 0.0:
        return spectral_rgb
    if white_mix >= 1.0:
        return Gf.Vec3f(1.0, 1.0, 1.0)

    # Blend with white
    white = Gf.Vec3f(1.0, 1.0, 1.0)
    r = white[0] * white_mix + spectral_rgb[0] * (1.0 - white_mix)
    g = white[1] * white_mix + spectral_rgb[1] * (1.0 - white_mix)
    b = white[2] * white_mix + spectral_rgb[2] * (1.0 - white_mix)

    rgb = Gf.Vec3f(r, g, b)
    return normalize_rgb(rgb, preserve_hue=True)


def load_spd_from_csv(csv_path: str) -> Optional[Tuple[list, list]]:
    """
    Load SPD data from a CSV file and return raw arrays.

    Expected CSV format:
    wavelength_nm,relative_intensity
    380,0.01
    385,0.02
    ...

    Args:
        csv_path: Path to CSV file

    Returns:
        Tuple of (wavelengths, intensities) lists, or None on error
    """
    try:
        wavelengths = []
        intensities = []

        with open(csv_path, 'r') as f:
            lines = f.readlines()

        # Skip header if present
        start_idx = 0
        if lines and not lines[0].strip()[0].isdigit():
            start_idx = 1

        for line in lines[start_idx:]:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            # Support comma, tab, or semicolon delimiters
            for delimiter in [',', '\t', ';']:
                if delimiter in line:
                    parts = line.split(delimiter)
                    break
            else:
                parts = line.split()  # Fallback to whitespace

            if len(parts) >= 2:
                try:
                    wl = float(parts[0])
                    intensity = float(parts[1])
                    wavelengths.append(wl)
                    intensities.append(intensity)
                except ValueError:
                    continue

        if not wavelengths:
            logger.error(f"No valid data found in {csv_path}")
            return None

        # Normalize intensities to max = 1.0
        max_intensity = max(intensities) if intensities else 1.0
        if max_intensity > 0:
            intensities = [i / max_intensity for i in intensities]

        logger.info(f"Loaded SPD from {csv_path}: {len(wavelengths)} data points")
        logger.info(f"  Wavelength range: {min(wavelengths):.0f} - {max(wavelengths):.0f} nm")

        return wavelengths, intensities

    except FileNotFoundError:
        logger.error(f"SPD CSV file not found: {csv_path}")
        return None
    except Exception as e:
        logger.error(f"Failed to load SPD from {csv_path}: {e}")
        return None


def spd_arrays_to_json(wavelengths: list, intensities: list, name: str = "") -> str:
    """
    Convert SPD arrays to JSON string for storage.

    Args:
        wavelengths: List of wavelengths in nm
        intensities: List of relative intensities
        name: Optional name for the SPD

    Returns:
        JSON string
    """
    import json
    data = {
        "wavelengths": list(wavelengths),
        "intensities": list(intensities),
        "name": name
    }
    return json.dumps(data)


def get_spd_info(wavelengths: list, intensities: list) -> dict:
    """
    Get information about an SPD dataset.

    Args:
        wavelengths: List of wavelengths in nm
        intensities: List of relative intensities

    Returns:
        Dict with peak wavelength, range, estimated FWHM, etc.
    """
    if not wavelengths or not intensities:
        return {"error": "No data"}

    # Find peak
    max_idx = intensities.index(max(intensities))
    peak_nm = wavelengths[max_idx]

    # Estimate FWHM
    max_intensity = max(intensities)
    half_max = max_intensity / 2.0
    above_half = [w for w, i in zip(wavelengths, intensities) if i >= half_max]
    fwhm = max(above_half) - min(above_half) if len(above_half) >= 2 else 30.0

    # Calculate RGB
    curve = parse_spd_arrays(wavelengths, intensities)
    rgb = curve.to_rgb() if curve else Gf.Vec3f(1, 1, 1)

    return {
        "data_points": len(wavelengths),
        "wavelength_min": min(wavelengths),
        "wavelength_max": max(wavelengths),
        "peak_nm": peak_nm,
        "estimated_fwhm": fwhm,
        "rgb": (rgb[0], rgb[1], rgb[2])
    }


# Quick test
if __name__ == "__main__":
    print("=" * 60)
    print("LED Spectral Processing - Full SPD Integration Test")
    print("=" * 60)

    # Test with LT QH9G parameters
    peak = 525  # nm
    dominant = 530  # nm
    fwhm = 33  # nm

    print(f"\nTest Case: OSRAM LT QH9G")
    print(f"  Peak λ: {peak} nm")
    print(f"  Dominant λ: {dominant} nm")
    print(f"  FWHM: {fwhm} nm")

    # Test with SpectralCurve class
    curve = SpectralCurve.from_gaussian(
        peak_nm=peak,
        fwhm_nm=fwhm,
        dominant_nm=dominant,
        name="OSRAM LT QH9G",
        manufacturer="OSRAM",
        model="LT QH9G"
    )

    rgb = curve.to_rgb()
    print(f"\nUsing SpectralCurve class:")
    print(f"  RGB = ({rgb[0]:.4f}, {rgb[1]:.4f}, {rgb[2]:.4f})")

    # Test spectral distribution at different wavelengths
    print(f"\nGaussian SPD values around peak:")
    for wl in [500, 510, 520, 525, 530, 540, 550, 560]:
        intensity = curve.evaluate(wl)
        print(f"  {wl}nm: {intensity:.4f}")

    # Test direct function (backward compatible)
    rgb2 = led_wavelength_to_rgb(peak, fwhm, dominant)
    print(f"\nUsing led_wavelength_to_rgb():")
    print(f"  RGB = ({rgb2[0]:.4f}, {rgb2[1]:.4f}, {rgb2[2]:.4f})")

    # Test presets
    print("\n" + "=" * 60)
    print("LED Preset Colors (Full SPD Integration)")
    print("=" * 60)

    for led_type, (peak_nm, fwhm_nm, name) in get_common_led_colors().items():
        curve = SpectralCurve.from_gaussian(peak_nm, fwhm_nm)
        rgb = curve.to_rgb()
        print(f"  {name:20s}: RGB = ({rgb[0]:.4f}, {rgb[1]:.4f}, {rgb[2]:.4f})")

    print("\n" + "=" * 60)
    print("Test complete - Full Gaussian SPD integration verified")
    print("=" * 60)

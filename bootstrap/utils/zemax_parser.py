"""
Zemax File Parser for Vision Digital Twin

Parses Zemax lens design files (.ZMX and .ZAR) to extract optical parameters
for use in Omniverse camera and lens simulation.

This module provides the foundation for the lens library system, extracting:
- Optical parameters (focal length, FOV, F-number, etc.)
- Distortion coefficients (radial and tangential)
- MTF data (spatial frequencies, contrast curves)
- Lens metadata (model, manufacturer, version)

Supported formats:
- .ZMX: Native Zemax OpticStudio text-based lens design files
- .ZAR: Zemax Archive files (compressed, extracted via zmxtools if available)

Reference: bootstrap/documentation/ZEMAX_LENS_INTEGRATION.md
"""

import re
import json
import logging
import math
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Setup logging
logger = logging.getLogger(__name__)

# Try to import Omniverse carb for logging
try:
    import carb
    CARB_AVAILABLE = True
except ImportError:
    CARB_AVAILABLE = False


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb if available."""
    logger.info(message)
    if CARB_AVAILABLE:
        carb.log_info(f"[Vision DT ZemaxParser] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb if available."""
    logger.warning(message)
    if CARB_AVAILABLE:
        carb.log_warn(f"[Vision DT ZemaxParser] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb if available."""
    logger.error(message)
    if CARB_AVAILABLE:
        carb.log_error(f"[Vision DT ZemaxParser] {message}")


# Try to import zmxtools for .ZAR archive support
try:
    from zmxtools import zar
    ZMXTOOLS_AVAILABLE = True
    _log_info("zmxtools available - .ZAR archive support enabled")
except ImportError:
    ZMXTOOLS_AVAILABLE = False
    _log_warn("zmxtools not available - .ZAR archive support disabled. Install with: pip install zmxtools")


class ZemaxParseError(Exception):
    """Exception raised for Zemax file parsing errors."""
    pass


class ZemaxLensData:
    """
    Container for parsed Zemax lens data.

    Provides structured access to optical parameters, distortion,
    MTF data, and metadata extracted from Zemax files.
    """

    def __init__(self):
        self.metadata: Dict[str, Any] = {
            "model": "",
            "manufacturer": "",
            "zemax_file": "",
            "zemax_version": "",
            "notes": "",
            "parse_version": "1.0"
        }

        self.optical: Dict[str, Any] = {
            "focal_length_mm": 0.0,
            "effective_focal_length_mm": 0.0,
            "back_focal_length_mm": 0.0,
            "working_distance_mm": 0.0,
            "f_number": 0.0,
            "numerical_aperture": 0.0,
            "field_of_view_deg": 0.0,
            "half_field_angle_deg": 0.0,
            "magnification": 0.0,
            "entrance_pupil_diameter_mm": 0.0,
            "entrance_pupil_position_mm": 0.0,
            "exit_pupil_diameter_mm": 0.0,
            "exit_pupil_position_mm": 0.0,
            "is_telecentric": False,
            "telecentric_type": "",  # "object-space", "image-space", or "double"
            "total_track_length_mm": 0.0,
            "image_height_mm": 0.0,
            "object_height_mm": 0.0
        }

        self.distortion: Dict[str, Any] = {
            "model": "brown-conrady",  # "brown-conrady", "fisheye", "polynomial"
            "k1": 0.0,  # Radial distortion coefficients
            "k2": 0.0,
            "k3": 0.0,
            "k4": 0.0,
            "k5": 0.0,
            "k6": 0.0,
            "p1": 0.0,  # Tangential distortion coefficients
            "p2": 0.0,
            "max_distortion_percent": 0.0,
            "distortion_at_edge_percent": 0.0
        }

        self.mtf: Dict[str, Any] = {
            "spatial_frequencies": [],  # lp/mm
            "contrast_sagittal": [],    # 0.0-1.0
            "contrast_tangential": [],  # 0.0-1.0
            "field_positions": [0.0],   # Normalized field (0=center, 1=edge)
            "wavelength_nm": 550.0,     # Measurement wavelength
            "f_stop": 0.0,              # F-stop at measurement
            "field_dependent": False,
            "mtf_at_50lpmm": 0.0,
            "mtf_at_100lpmm": 0.0,
            "field_dependent_data": {}  # Dict of field_pos -> {sagittal: [], tangential: []}
        }

        self.chromatic: Dict[str, Any] = {
            "lateral_ca_red_um": 0.0,
            "lateral_ca_blue_um": 0.0,
            "longitudinal_ca_mm": 0.0,
            "wavelengths_nm": [486.1, 546.1, 656.3]  # F, d, C lines
        }

        self.surfaces: List[Dict[str, Any]] = []  # Raw surface data

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": self.metadata,
            "optical": self.optical,
            "distortion": self.distortion,
            "mtf": self.mtf,
            "chromatic": self.chromatic,
            "surface_count": len(self.surfaces)
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save_json(self, path: str) -> bool:
        """Save lens data to JSON file."""
        try:
            with open(path, 'w') as f:
                f.write(self.to_json())
            _log_info(f"Saved lens data to {path}")
            return True
        except Exception as e:
            _log_error(f"Failed to save lens data to {path}: {e}")
            return False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ZemaxLensData':
        """Create ZemaxLensData from dictionary."""
        lens = cls()
        if "metadata" in data:
            lens.metadata.update(data["metadata"])
        if "optical" in data:
            lens.optical.update(data["optical"])
        if "distortion" in data:
            lens.distortion.update(data["distortion"])
        if "mtf" in data:
            lens.mtf.update(data["mtf"])
        if "chromatic" in data:
            lens.chromatic.update(data["chromatic"])
        return lens

    @classmethod
    def from_json(cls, json_str: str) -> 'ZemaxLensData':
        """Create ZemaxLensData from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def load_json(cls, path: str) -> 'ZemaxLensData':
        """Load lens data from JSON file."""
        with open(path, 'r') as f:
            return cls.from_json(f.read())


class ZemaxParser:
    """
    Parser for Zemax lens design files.

    Supports .ZMX (text-based) and .ZAR (archive) formats.
    Extracts optical parameters, distortion, and MTF data.
    """

    # ZMX file section patterns
    # Note: Zemax files may have extra parameters after values, so patterns are flexible
    PATTERNS = {
        'version': re.compile(r'VERS\s+(\d+)'),  # Version may be just an integer
        'mode': re.compile(r'MODE\s+(\w+)'),
        'name': re.compile(r'NAME\s+"?([^"\n]+)"?'),
        'note': re.compile(r'NOTE\s+\d+\s+"?([^"\n]*)"?'),
        'units': re.compile(r'UNIT\s+(\w+)'),

        # System data - patterns allow extra trailing parameters
        'effl': re.compile(r'EFFL\s+([-\d.eE+]+)'),
        'bfl': re.compile(r'BFLD?\s+([-\d.eE+]+)'),
        'fnum': re.compile(r'FNUM\s+([-\d.eE+]+)'),  # F-number (may have trailing params)
        'wfno': re.compile(r'WFNO\s+([-\d.eE+]+)'),
        'envd': re.compile(r'ENVD\s+([-\d.eE+]+)'),  # Entrance pupil diameter (ENVD not ENPD)
        'enpp': re.compile(r'ENPP\s+([-\d.eE+]+)'),  # Entrance pupil position
        'enpd': re.compile(r'ENPD\s+([-\d.eE+]+)'),  # Entrance pupil diameter (alternate)
        'expp': re.compile(r'EXPP\s+([-\d.eE+]+)'),  # Exit pupil position
        'expd': re.compile(r'EXPD\s+([-\d.eE+]+)'),  # Exit pupil diameter
        'objht': re.compile(r'OBJH\s+([-\d.eE+]+)'),  # Object height
        'imght': re.compile(r'IMGH\s+([-\d.eE+]+)'),  # Image height
        'ttl': re.compile(r'TOTR\s+([-\d.eE+]+)'),  # Total track length

        # Field definitions
        'ftyp': re.compile(r'FTYP\s+(\d+)'),  # Field type
        'yfln': re.compile(r'YFLN\s+([-\d.eE+\s]+)'),  # Y field values (space-separated)
        'fwgn': re.compile(r'FWGN\s+([-\d.eE+\s]+)'),  # Field weights
        'hfov': re.compile(r'AFLD\s+([-\d.eE+]+)'),  # Half field of view

        # Wavelength - WAVM format: WAVM index wavelength weight
        'wavm': re.compile(r'WAVM\s+(\d+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)'),
        'pwav': re.compile(r'PWAV\s+(\d+)'),  # Primary wavelength index

        # Aperture
        'aper': re.compile(r'APER\s+([-\d.eE+]+)'),
        'floa': re.compile(r'FLOA'),  # Float by aperture

        # Surface definitions
        'surf': re.compile(r'SURF\s+(\d+)'),
        'type': re.compile(r'TYPE\s+(\w+)'),
        'curv': re.compile(r'CURV\s+([-\d.eE+]+)'),
        'disz': re.compile(r'DISZ\s+([-\d.eE+]+)'),
        'glas': re.compile(r'GLAS\s+(\S+)'),
        'diam': re.compile(r'DIAM\s+([-\d.eE+]+)'),
        'sqap': re.compile(r'SQAP\s+([-\d.eE+]+)\s+([-\d.eE+]+)'),  # Rectangular aperture
        'clap': re.compile(r'CLAP\s+\d+\s+([-\d.eE+]+)'),  # Circular aperture (CLAP flag radius flag)

        # Distortion - various formats
        'dist': re.compile(r'DIST\s+([-\d.eE+]+)'),
        'dstx': re.compile(r'DSTX\s+([-\d.eE+]+)\s+([-\d.eE+]+)\s*([-\d.eE+]+)?'),
    }

    def __init__(self):
        self.lens_data = ZemaxLensData()
        self._current_surface = {}
        self._wavelengths = []
        self._fields = []

    def parse_file(self, file_path: str) -> ZemaxLensData:
        """
        Parse a Zemax file and return extracted lens data.

        Args:
            file_path: Path to .ZMX or .ZAR file

        Returns:
            ZemaxLensData object with extracted parameters

        Raises:
            ZemaxParseError: If file cannot be parsed
        """
        path = Path(file_path)

        _log_info(f"parse_file() called with: {file_path}")

        if not path.exists():
            error_msg = f"File not found: {file_path}"
            _log_error(error_msg)
            raise ZemaxParseError(error_msg)

        suffix = path.suffix.lower()
        _log_info(f"Detected file type: {suffix}")

        if suffix == '.zmx':
            _log_info("Parsing as .ZMX text file...")
            return self._parse_zmx(path)
        elif suffix == '.zar':
            _log_info("Parsing as .ZAR archive file...")
            return self._parse_zar(path)
        else:
            error_msg = f"Unsupported file format: {suffix} (expected .zmx or .zar)"
            _log_error(error_msg)
            raise ZemaxParseError(error_msg)

    def _parse_zar(self, path: Path) -> ZemaxLensData:
        """Parse a .ZAR archive file."""
        _log_info(f"Starting .ZAR archive import: {path}")

        if not ZMXTOOLS_AVAILABLE:
            error_msg = ".ZAR archive support requires zmxtools. Install with: pip install zmxtools"
            _log_error(error_msg)
            raise ZemaxParseError(error_msg)

        _log_info("zmxtools available - proceeding with extraction")

        try:
            # Extract .ZAR contents to temp directory
            import tempfile
            _log_info(f"Creating temporary directory for extraction...")
            with tempfile.TemporaryDirectory() as temp_dir:
                _log_info(f"Extracting .ZAR archive to: {temp_dir}")
                try:
                    zar.extract(str(path), temp_dir)
                    _log_info(f"Archive extraction completed successfully")
                except Exception as extract_error:
                    _log_error(f"Failed to extract archive: {extract_error}")
                    raise ZemaxParseError(f"Archive extraction failed: {extract_error}")

                # Find .ZMX file in extracted contents
                _log_info(f"Searching for .ZMX files in extracted contents...")
                zmx_files = list(Path(temp_dir).rglob("*.zmx")) + \
                           list(Path(temp_dir).rglob("*.ZMX"))

                _log_info(f"Found {len(zmx_files)} .ZMX file(s) in archive")

                if not zmx_files:
                    error_msg = f"No .ZMX file found in archive: {path}"
                    _log_error(error_msg)
                    _log_info(f"Listing extracted files for debugging:")
                    try:
                        for extracted_file in Path(temp_dir).rglob("*"):
                            if extracted_file.is_file():
                                _log_info(f"  - {extracted_file.name} ({extracted_file.suffix})")
                    except Exception as list_error:
                        _log_warn(f"Could not list extracted files: {list_error}")
                    raise ZemaxParseError(error_msg)

                # Log which .ZMX file will be parsed
                zmx_to_parse = zmx_files[0]
                _log_info(f"Parsing .ZMX file: {zmx_to_parse}")
                if len(zmx_files) > 1:
                    _log_warn(f"Multiple .ZMX files found, using first: {zmx_to_parse}")
                    _log_info(f"Other .ZMX files in archive:")
                    for other_zmx in zmx_files[1:]:
                        _log_info(f"  - {other_zmx}")

                # Parse the first .ZMX file found
                try:
                    lens_data = self._parse_zmx(zmx_to_parse)
                    _log_info(f"Successfully parsed .ZMX file")
                    _log_info(f"Extracted lens model: {lens_data.metadata.get('model', 'Unknown')}")
                    _log_info(f"Focal length: {lens_data.optical.get('focal_length_mm', 0)}mm")
                    _log_info(f"F-number: f/{lens_data.optical.get('f_number', 0)}")
                    _log_info(f"FOV: {lens_data.optical.get('field_of_view_deg', 0)} deg")
                    _log_info(f"Working distance: {lens_data.optical.get('working_distance_mm', 0)}mm")
                    _log_info(f"Telecentric: {lens_data.optical.get('is_telecentric', False)}")
                    _log_info(f"Surfaces parsed: {len(lens_data.surfaces)}")
                    lens_data.metadata["zemax_file"] = str(path)
                    _log_info(f".ZAR archive import completed successfully")
                    return lens_data
                except Exception as parse_error:
                    _log_error(f"Failed to parse .ZMX file {zmx_to_parse}: {parse_error}")
                    import traceback
                    _log_error(f"Parse error traceback:\n{traceback.format_exc()}")
                    raise ZemaxParseError(f"Failed to parse .ZMX file from archive: {parse_error}")

        except ZemaxParseError:
            # Re-raise ZemaxParseError as-is (already logged)
            raise
        except Exception as e:
            error_msg = f"Failed to parse .ZAR archive: {e}"
            _log_error(error_msg)
            import traceback
            _log_error(f"Archive parse error traceback:\n{traceback.format_exc()}")
            raise ZemaxParseError(error_msg)

    def _parse_zmx(self, path: Path) -> ZemaxLensData:
        """Parse a .ZMX text file."""
        _log_info(f"Parsing .ZMX file: {path.name}")
        try:
            # Try different encodings - UTF-16 first (common for Zemax files)
            content = None
            for encoding in ['utf-16', 'utf-16-le', 'utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(path, 'r', encoding=encoding) as f:
                        content = f.read()
                    _log_info(f"Successfully read file with encoding: {encoding}")
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue

            if content is None:
                raise ZemaxParseError(f"Unable to decode file: {path}")

            _log_info(f"File size: {len(content):,} characters")

            # Reset state
            self.lens_data = ZemaxLensData()
            self._current_surface = {}
            self._wavelengths = []
            self._fields = []

            # Store source file path
            self.lens_data.metadata["zemax_file"] = str(path)

            # Parse sections
            _log_info("Parsing header...")
            self._parse_header(content)
            _log_info(f"  Model: {self.lens_data.metadata.get('model', 'Unknown')}")
            _log_info(f"  Zemax version: {self.lens_data.metadata.get('zemax_version', 'Unknown')}")

            _log_info("Parsing system data...")
            self._parse_system_data(content)
            _log_info(f"  Focal length: {self.lens_data.optical.get('focal_length_mm', 0)}mm")
            _log_info(f"  F-number: f/{self.lens_data.optical.get('f_number', 0)}")
            _log_info(f"  FOV: {self.lens_data.optical.get('field_of_view_deg', 0)} deg")

            _log_info("Parsing fields...")
            self._parse_fields(content)
            _log_info(f"  Found {len(self._fields)} field points")

            _log_info("Parsing wavelengths...")
            self._parse_wavelengths(content)
            _log_info(f"  Found {len(self._wavelengths)} wavelengths: {self._wavelengths}")

            _log_info("Parsing surfaces...")
            self._parse_surfaces(content)
            _log_info(f"  Found {len(self.lens_data.surfaces)} surfaces")

            _log_info("Calculating derived parameters...")
            self._calculate_derived_parameters()
            _log_info(f"  Working distance: {self.lens_data.optical.get('working_distance_mm', 0)}mm")
            _log_info(f"  Magnification: {self.lens_data.optical.get('magnification', 0)}x")
            _log_info(f"  NA: {self.lens_data.optical.get('numerical_aperture', 0)}")
            _log_info(f"  Telecentric: {self.lens_data.optical.get('is_telecentric', False)}")

            return self.lens_data

        except Exception as e:
            _log_error(f"Failed to parse .ZMX file: {e}")
            import traceback
            _log_error(f"Traceback:\n{traceback.format_exc()}")
            raise ZemaxParseError(f"Failed to parse .ZMX file: {e}")

    def _parse_header(self, content: str):
        """Parse file header information."""
        # Version
        match = self.PATTERNS['version'].search(content)
        if match:
            self.lens_data.metadata["zemax_version"] = match.group(1)

        # Name
        match = self.PATTERNS['name'].search(content)
        if match:
            self.lens_data.metadata["model"] = match.group(1).strip()

        # Notes
        notes = []
        for match in self.PATTERNS['note'].finditer(content):
            note = match.group(1).strip()
            if note:
                notes.append(note)
        if notes:
            self.lens_data.metadata["notes"] = "; ".join(notes)

    def _parse_system_data(self, content: str):
        """Parse system-level optical data."""
        optical = self.lens_data.optical

        # Effective focal length
        match = self.PATTERNS['effl'].search(content)
        if match:
            optical["effective_focal_length_mm"] = float(match.group(1))
            optical["focal_length_mm"] = float(match.group(1))

        # Back focal length
        match = self.PATTERNS['bfl'].search(content)
        if match:
            optical["back_focal_length_mm"] = float(match.group(1))

        # F-number
        match = self.PATTERNS['fnum'].search(content)
        if match:
            optical["f_number"] = float(match.group(1))

        # Working F-number
        match = self.PATTERNS['wfno'].search(content)
        if match:
            wfno = float(match.group(1))
            if optical["f_number"] == 0:
                optical["f_number"] = wfno

        # Entrance pupil diameter (try ENVD first, then ENPD)
        match = self.PATTERNS['envd'].search(content)
        if match:
            optical["entrance_pupil_diameter_mm"] = float(match.group(1))
            _log_info(f"  ENVD found: {optical['entrance_pupil_diameter_mm']}mm")
        else:
            match = self.PATTERNS['enpd'].search(content)
            if match:
                optical["entrance_pupil_diameter_mm"] = float(match.group(1))
                _log_info(f"  ENPD found: {optical['entrance_pupil_diameter_mm']}mm")

        match = self.PATTERNS['enpp'].search(content)
        if match:
            optical["entrance_pupil_position_mm"] = float(match.group(1))

        # Exit pupil
        match = self.PATTERNS['expd'].search(content)
        if match:
            optical["exit_pupil_diameter_mm"] = float(match.group(1))

        match = self.PATTERNS['expp'].search(content)
        if match:
            optical["exit_pupil_position_mm"] = float(match.group(1))

        # Image/object height
        match = self.PATTERNS['imght'].search(content)
        if match:
            optical["image_height_mm"] = float(match.group(1))

        match = self.PATTERNS['objht'].search(content)
        if match:
            optical["object_height_mm"] = float(match.group(1))

        # Total track length
        match = self.PATTERNS['ttl'].search(content)
        if match:
            optical["total_track_length_mm"] = float(match.group(1))

        # Half field of view
        match = self.PATTERNS['hfov'].search(content)
        if match:
            half_fov = float(match.group(1))
            optical["half_field_angle_deg"] = half_fov
            optical["field_of_view_deg"] = half_fov * 2

    def _parse_fields(self, content: str):
        """Parse field definitions."""
        # Field values can be on a single line: YFLN 0 3.0 4.0 -4. 0 0 0 0 0 0 0 0
        # Or indexed: XFLN 1 0.0

        # Try single-line format first (all values after XFLN/YFLN)
        xfln_single = re.search(r'XFLN\s+([-\d.eE+\s]+)', content)
        yfln_single = re.search(r'YFLN\s+([-\d.eE+\s]+)', content)

        x_values = []
        y_values = []

        if xfln_single:
            x_str = xfln_single.group(1).strip()
            x_values = [float(x) for x in x_str.split() if x.strip()]
            _log_info(f"  X field values: {x_values[:4]}...")  # Log first 4

        if yfln_single:
            y_str = yfln_single.group(1).strip()
            y_values = [float(y) for y in y_str.split() if y.strip()]
            _log_info(f"  Y field values: {y_values[:4]}...")  # Log first 4

        # Combine X and Y fields
        max_len = max(len(x_values), len(y_values)) if (x_values or y_values) else 0
        for i in range(max_len):
            x = x_values[i] if i < len(x_values) else 0.0
            y = y_values[i] if i < len(y_values) else 0.0
            self._fields.append((x, y))

        # Calculate max field height for FOV estimation
        if y_values:
            max_field = max(abs(y) for y in y_values if y != 0)
            if max_field > 0:
                # Store for later FOV calculation (field height in mm or degrees depending on FTYP)
                self.lens_data.optical["image_height_mm"] = max_field
                _log_info(f"  Max field height: {max_field}")

    def _parse_wavelengths(self, content: str):
        """Parse wavelength definitions."""
        # Look for WAVM entries (wavelength with weight)
        # Format: WAVM index wavelength weight
        # Wavelength is in micrometers, e.g., 5.5E-1 = 0.55 um = 550 nm
        wavm_pattern = re.compile(r'WAVM\s+(\d+)\s+([-\d.eE+]+)\s+([-\d.eE+]+)')

        wavelengths = {}
        for match in wavm_pattern.finditer(content):
            idx = int(match.group(1))
            wavelength_um = float(match.group(2))  # Value is in micrometers
            weight = float(match.group(3))

            # Convert from micrometers to nanometers
            wavelength_nm = wavelength_um * 1000.0

            if wavelength_nm > 0 and wavelength_nm < 2000:  # Valid visible/IR range
                wavelengths[idx] = (wavelength_nm, weight)
                _log_info(f"  WAVM {idx}: {wavelength_um} um = {wavelength_nm} nm (weight={weight})")

        # Sort by index and extract wavelengths
        for idx in sorted(wavelengths.keys()):
            self._wavelengths.append(wavelengths[idx][0])

        # Primary wavelength for MTF
        match = self.PATTERNS['pwav'].search(content)
        if match:
            pwav_idx = int(match.group(1))
            _log_info(f"  Primary wavelength index: {pwav_idx}")
            if pwav_idx <= len(self._wavelengths):
                self.lens_data.mtf["wavelength_nm"] = self._wavelengths[pwav_idx - 1]
                _log_info(f"  Primary wavelength: {self._wavelengths[pwav_idx - 1]} nm")
        elif self._wavelengths:
            self.lens_data.mtf["wavelength_nm"] = self._wavelengths[len(self._wavelengths) // 2]

    def _parse_surfaces(self, content: str):
        """Parse surface definitions."""
        # Split content by SURF markers
        surf_pattern = re.compile(r'SURF\s+(\d+)')

        # Find all surface starts
        surf_starts = [(m.start(), int(m.group(1))) for m in surf_pattern.finditer(content)]

        if not surf_starts:
            return

        # Parse each surface
        for i, (start, surf_num) in enumerate(surf_starts):
            # Get content until next surface or end
            if i + 1 < len(surf_starts):
                end = surf_starts[i + 1][0]
            else:
                end = len(content)

            surf_content = content[start:end]
            surface = self._parse_single_surface(surf_num, surf_content)
            self.lens_data.surfaces.append(surface)

    def _parse_single_surface(self, surf_num: int, content: str) -> Dict[str, Any]:
        """Parse a single surface definition."""
        surface = {
            "number": surf_num,
            "type": "STANDARD",
            "curvature": 0.0,
            "radius": float('inf'),
            "thickness": 0.0,
            "glass": "",
            "diameter": 0.0,
            "is_stop": False
        }

        # Type
        match = self.PATTERNS['type'].search(content)
        if match:
            surface["type"] = match.group(1)

        # Curvature and radius
        match = self.PATTERNS['curv'].search(content)
        if match:
            curv = float(match.group(1))
            surface["curvature"] = curv
            if abs(curv) > 1e-10:
                surface["radius"] = 1.0 / curv

        # Thickness
        match = self.PATTERNS['disz'].search(content)
        if match:
            surface["thickness"] = float(match.group(1))

        # Glass
        match = self.PATTERNS['glas'].search(content)
        if match:
            surface["glass"] = match.group(1)

        # Diameter
        match = self.PATTERNS['diam'].search(content)
        if match:
            surface["diameter"] = float(match.group(1))

        # Check for aperture stop
        if "STOP" in content:
            surface["is_stop"] = True

        return surface

    def _calculate_derived_parameters(self):
        """Calculate derived parameters from parsed data."""
        optical = self.lens_data.optical
        distortion = self.lens_data.distortion

        _log_info("Calculating derived parameters...")

        # Calculate numerical aperture from F-number
        if optical["f_number"] > 0:
            optical["numerical_aperture"] = 1.0 / (2.0 * optical["f_number"])
            _log_info(f"  NA calculated from f/{optical['f_number']}: {optical['numerical_aperture']:.4f}")

        # Calculate magnification from object/image heights
        if optical["object_height_mm"] != 0:
            optical["magnification"] = abs(
                optical["image_height_mm"] / optical["object_height_mm"]
            )

        # Calculate working distance and total track from surfaces
        if self.lens_data.surfaces:
            first_surface = self.lens_data.surfaces[0]
            thickness = first_surface.get("thickness", 0)
            # In Zemax, infinity is often represented as very large values
            if abs(thickness) < 1e10 and thickness > 0:
                optical["working_distance_mm"] = abs(thickness)
                _log_info(f"  Working distance from SURF 0 DISZ: {optical['working_distance_mm']}mm")

            # Calculate total track length (sum of all positive thicknesses)
            total_track = 0.0
            for surf in self.lens_data.surfaces:
                t = surf.get("thickness", 0)
                if 0 < t < 1e10:
                    total_track += t
            if total_track > 0:
                optical["total_track_length_mm"] = total_track
                _log_info(f"  Total track length: {total_track:.2f}mm")

        # Telecentric detection
        # Object-space telecentric: entrance pupil at infinity
        if optical["entrance_pupil_position_mm"] > 1e6:
            optical["is_telecentric"] = True
            optical["telecentric_type"] = "object-space"
            _log_info("  Detected: Object-space telecentric (entrance pupil at infinity)")
        # Image-space telecentric: exit pupil at infinity
        elif optical["exit_pupil_position_mm"] > 1e6:
            optical["is_telecentric"] = True
            optical["telecentric_type"] = "image-space"
            _log_info("  Detected: Image-space telecentric (exit pupil at infinity)")
        else:
            # Heuristic: model/notes mention telecentric OR narrow FOV with near-1x magnification
            model_lower = self.lens_data.metadata.get("model", "").lower()
            notes_lower = self.lens_data.metadata.get("notes", "").lower()
            fov = optical.get("field_of_view_deg", 0.0)
            mag = optical.get("magnification", 0.0)

            name_implies_telecentric = "telecentric" in model_lower or "telecentric" in notes_lower
            narrow_fov_1x = fov > 0 and fov < 8.0 and 0.4 <= mag <= 1.6

            if name_implies_telecentric or narrow_fov_1x:
                optical["is_telecentric"] = True
                if not optical.get("telecentric_type"):
                    optical["telecentric_type"] = "object-space"
                _log_info(
                    "  Heuristic telecentric detection: "
                    f"name_hint={name_implies_telecentric}, fov={fov:.2f}, mag={mag:.2f}"
                )

        # Set F-stop for MTF
        self.lens_data.mtf["f_stop"] = optical["f_number"]

        # Calculate focal length from entrance pupil diameter and F-number if not set
        # Formula: focal_length = entrance_pupil_diameter × F-number
        if optical["focal_length_mm"] == 0:
            if optical["entrance_pupil_diameter_mm"] > 0 and optical["f_number"] > 0:
                estimated_fl = optical["entrance_pupil_diameter_mm"] * optical["f_number"]
                optical["focal_length_mm"] = estimated_fl
                optical["effective_focal_length_mm"] = estimated_fl
                _log_info(f"  Focal length estimated from ENPD×F#: {estimated_fl:.1f}mm")
            elif optical["working_distance_mm"] > 0:
                # This is a rough approximation - actual EFL requires ray tracing
                _log_info("  Note: Focal length not found in file - would require ray tracing to calculate")

        # Estimate distortion from field data if available
        # Note: Real distortion coefficients require ray tracing or Zemax API
        # This is a placeholder for manual entry or ZOSPy extraction
        distortion["model"] = "brown-conrady"

        _log_info("Derived parameters calculation complete")


def parse_zmx_file(file_path: str) -> Dict[str, Any]:
    """
    Convenience function to parse a Zemax file and return dictionary.

    Args:
        file_path: Path to .ZMX or .ZAR file

    Returns:
        Dictionary containing lens parameters
    """
    parser = ZemaxParser()
    lens_data = parser.parse_file(file_path)
    return lens_data.to_dict()


def extract_zar_contents(zar_path: str, output_dir: str) -> List[str]:
    """
    Extract contents of a .ZAR archive.

    Args:
        zar_path: Path to .ZAR file
        output_dir: Directory to extract to

    Returns:
        List of extracted file paths
    """
    if not ZMXTOOLS_AVAILABLE:
        raise ZemaxParseError(
            ".ZAR archive support requires zmxtools. "
            "Install with: pip install zmxtools"
        )

    zar.extract(zar_path, output_dir)

    # Return list of extracted files
    output_path = Path(output_dir)
    return [str(p) for p in output_path.rglob("*") if p.is_file()]


def create_lens_data_from_specs(
    model: str,
    manufacturer: str,
    focal_length_mm: float,
    f_number: float,
    working_distance_mm: float = 0.0,
    field_of_view_deg: float = 0.0,
    magnification: float = 0.0,
    is_telecentric: bool = False,
    distortion_k1: float = 0.0,
    distortion_k2: float = 0.0,
    distortion_k3: float = 0.0,
    distortion_p1: float = 0.0,
    distortion_p2: float = 0.0,
    mtf_at_50lpmm: float = 0.0,
    mtf_at_100lpmm: float = 0.0
) -> ZemaxLensData:
    """
    Create lens data from manual specifications (when Zemax file not available).

    This allows manually entering lens parameters from datasheets.

    Args:
        model: Lens model name
        manufacturer: Manufacturer name
        focal_length_mm: Focal length in mm
        f_number: F-number (f-stop)
        working_distance_mm: Working distance in mm
        field_of_view_deg: Full field of view in degrees
        magnification: Optical magnification
        is_telecentric: Whether lens is telecentric
        distortion_k1/k2/k3: Radial distortion coefficients
        distortion_p1/p2: Tangential distortion coefficients
        mtf_at_50lpmm: MTF contrast at 50 lp/mm
        mtf_at_100lpmm: MTF contrast at 100 lp/mm

    Returns:
        ZemaxLensData object with specified parameters
    """
    lens_data = ZemaxLensData()

    # Metadata
    lens_data.metadata["model"] = model
    lens_data.metadata["manufacturer"] = manufacturer
    lens_data.metadata["notes"] = "Created from manual specifications"

    # Optical
    lens_data.optical["focal_length_mm"] = focal_length_mm
    lens_data.optical["effective_focal_length_mm"] = focal_length_mm
    lens_data.optical["f_number"] = f_number
    lens_data.optical["working_distance_mm"] = working_distance_mm
    lens_data.optical["field_of_view_deg"] = field_of_view_deg
    lens_data.optical["half_field_angle_deg"] = field_of_view_deg / 2
    lens_data.optical["magnification"] = magnification
    lens_data.optical["is_telecentric"] = is_telecentric

    if f_number > 0:
        lens_data.optical["numerical_aperture"] = 1.0 / (2.0 * f_number)

    # Distortion
    lens_data.distortion["k1"] = distortion_k1
    lens_data.distortion["k2"] = distortion_k2
    lens_data.distortion["k3"] = distortion_k3
    lens_data.distortion["p1"] = distortion_p1
    lens_data.distortion["p2"] = distortion_p2

    # MTF
    lens_data.mtf["mtf_at_50lpmm"] = mtf_at_50lpmm
    lens_data.mtf["mtf_at_100lpmm"] = mtf_at_100lpmm
    lens_data.mtf["f_stop"] = f_number

    # Set common spatial frequencies if MTF values provided
    if mtf_at_50lpmm > 0 or mtf_at_100lpmm > 0:
        lens_data.mtf["spatial_frequencies"] = [10, 20, 30, 40, 50, 75, 100]
        # Interpolate other values (simple linear approximation)
        lens_data.mtf["contrast_sagittal"] = [
            1.0,
            max(0, 1.0 - 0.02 * 10),
            max(0, 1.0 - 0.02 * 20),
            max(0, 1.0 - 0.02 * 30),
            mtf_at_50lpmm if mtf_at_50lpmm > 0 else 0.7,
            (mtf_at_50lpmm + mtf_at_100lpmm) / 2 if mtf_at_50lpmm > 0 else 0.5,
            mtf_at_100lpmm if mtf_at_100lpmm > 0 else 0.4
        ]
        lens_data.mtf["contrast_tangential"] = lens_data.mtf["contrast_sagittal"].copy()

    return lens_data


# Example usage and testing
if __name__ == "__main__":
    # Test with manual specs
    lens = create_lens_data_from_specs(
        model="TechSpec #67-857",
        manufacturer="Edmund Optics",
        focal_length_mm=35.0,
        f_number=2.8,
        working_distance_mm=100.0,
        field_of_view_deg=45.0,
        is_telecentric=True,
        mtf_at_50lpmm=0.75,
        mtf_at_100lpmm=0.48
    )

    print("Lens Data (JSON):")
    print(lens.to_json())

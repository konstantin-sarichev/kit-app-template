# Zemax Lens Integration for Omniverse

## Executive Summary

This document outlines research findings and implementation strategy for integrating Zemax lens files (`.ZMX` and `.ZAR` formats) into NVIDIA Omniverse to create a preloaded lens library that can be applied to cameras as custom profiles.

**Goal:** Preload Zemax files for all lenses, creating a library of lens profiles that can be selected and applied directly to Omniverse cameras via custom attributes.

**Simplified Approach:** Lens parameters are applied directly to Omniverse cameras as custom profiles. 3D CAD models are omitted to simplify implementation.

---

## 1. Zemax File Formats

### 1.1 File Types

- **`.ZMX`** - Native Zemax OpticStudio lens design file (text-based, human-readable)
- **`.ZAR`** - Zemax Archive file (compressed archive containing `.ZMX` files and associated data)

### 1.2 Zemax File Contents

Zemax files contain comprehensive optical design data:

**Optical Parameters:**
- Focal length (mm)
- Effective focal length (EFL)
- Back focal length (BFL)
- Working distance (WD)
- Field of view (FOV)
- F-number (f/#)
- Numerical aperture (NA)
- Magnification
- Telecentricity parameters
- Entrance/exit pupil positions and sizes

**Distortion Data:**
- Radial distortion coefficients (k1, k2, k3)
- Tangential distortion coefficients (p1, p2)
- Distortion model type

**MTF (Modulation Transfer Function):**
- Spatial frequency response (typically 0-200 lp/mm)
- Contrast vs. frequency curves (0.0-1.0 modulation)
- Sagittal and tangential MTF curves (separate for radial/tangential directions)
- Field position variation (center, edge, corner positions)
- Wavelength-dependent MTF (if polychromatic analysis available)
- F-stop dependent MTF (diffraction-limited performance varies with aperture)

---

## 2. Python Libraries for Zemax File Parsing

### 2.1 zmxtools

**Purpose:** Extract and read Zemax Archive (`.ZAR`) files

**Installation:**
```bash
pip install zmxtools
```

**Usage:**
```python
from zmxtools import zar

# Extract contents of a ZAR file
zar.extract('path_to_your_lens.zar')

# Read the contents of the ZAR file
lens_data = zar.read('path_to_your_lens.zar')
```

**Documentation:** https://zmxtools.readthedocs.io/

**Limitations:** Primarily for `.ZAR` archives, may require additional parsing for `.ZMX` files

---

### 2.2 ZOSPy

**Purpose:** Pythonic interface to Zemax OpticStudio API (requires Zemax OpticStudio installed)

**Installation:**
```bash
pip install zospy
```

**Usage:**
```python
import zospy as zp

# Connect to Zemax OpticStudio
zos = zp.ZOS()
oss = zos.connect()

# Load a lens file
oss.load_file('path_to_your_file.zmx')

# Access lens parameters
system_data = oss.SystemData
lens_data = oss.LDE  # Lens Data Editor

# Extract focal length
focal_length = system_data.FocalLength

# Extract distortion coefficients
# (varies by Zemax version and API)
```

**Documentation:** https://github.com/MREYE-LUMC/ZOSPy

**Advantages:**
- Full access to Zemax OpticStudio API
- Can export lens data programmatically
- Can calculate MTF, distortion, and other optical metrics

**Limitations:**
- Requires Zemax OpticStudio license and installation
- COM-based API (Windows) or .NET API (cross-platform)

---

### 2.3 Manual ZMX Parsing

**ZMX File Structure:**
ZMX files are text-based with specific sections:
- `VERS` - Version information
- `MODE` - System mode (sequential/non-sequential)
- `SURF` - Surface definitions
- `GLAS` - Glass catalog references
- `APER` - Aperture definitions
- `WAVE` - Wavelength definitions
- `FIEL` - Field definitions
- `CONF` - Configuration data

**Example ZMX Surface Entry:**
```
SURF    1
TYPE    STANDARD
CURV    0.0
DISZ    0.0
GLAS    N-BK7
DIAM    25.4
```

**Parsing Strategy:**
- Use Python's `re` module for pattern matching
- Parse section headers and data blocks
- Extract optical parameters from system data section
- Build lens parameter dictionary

---

## 3. Omniverse Camera and Lens Integration

### 3.1 Omniverse Camera Schema

Omniverse uses USD (Universal Scene Description) for camera definitions:

**Standard Camera Attributes:**
```python
from pxr import UsdGeom

camera = UsdGeom.Camera(camera_prim)

# Focal length (mm)
camera.GetFocalLengthAttr().Set(35.0)

# Horizontal aperture (mm)
camera.GetHorizontalApertureAttr().Set(20.955)

# Vertical aperture (mm)
camera.GetVerticalApertureAttr().Set(15.955)

# F-stop
camera.GetFStopAttr().Set(2.8)

# Focus distance (mm)
camera.GetFocusDistanceAttr().Set(1000.0)
```

---

### 3.2 Omniverse Lens Distortion API

Omniverse supports lens distortion models via specialized schemas:

**OpenCV Pinhole Model:**
```python
from pxr import Usd, UsdGeom

stage = Usd.Stage.Open('path_to_stage.usd')
camera_prim = stage.GetPrimAtPath('/World/Camera')

# Apply OpenCV pinhole lens distortion schema
camera_prim.ApplyAPI('OmniLensDistortionOpenCvPinholeAPI')

# Set distortion parameters
camera_prim.GetAttribute('lensDistortion:k1').Set(0.1)  # Radial k1
camera_prim.GetAttribute('lensDistortion:k2').Set(0.01)  # Radial k2
camera_prim.GetAttribute('lensDistortion:k3').Set(0.001) # Radial k3
camera_prim.GetAttribute('lensDistortion:p1').Set(0.001) # Tangential p1
camera_prim.GetAttribute('lensDistortion:p2').Set(0.001) # Tangential p2
```

**Fisheye Model:**
```python
camera_prim.ApplyAPI('OmniLensDistortionFisheyeAPI')
# Similar parameter setting for fisheye distortion
```

**Documentation:** https://docs.omniverse.nvidia.com/materials-and-rendering/latest/cameras.html

---

### 3.3 Vision DT Lens Attributes (Proposed)

Based on the existing Vision DT architecture, lens parameters should be stored as custom attributes:

```python
# Lens profile selection
visiondt:lens:libraryId              # Lens library ID (e.g., "lens_001")
visiondt:lens:profileName           # Human-readable profile name

# Lens optical parameters
visiondt:lens:focalLengthMm         # Focal length (mm)
visiondt:lens:workingDistanceMm     # Working distance (mm)
visiondt:lens:fNumber               # F-number
visiondt:lens:effectiveFocalLength  # EFL (mm)
visiondt:lens:backFocalLength       # BFL (mm)
visiondt:lens:fieldOfViewDeg        # FOV (degrees)
visiondt:lens:numericalAperture     # NA
visiondt:lens:magnification         # Magnification
visiondt:lens:isTelecentric         # Bool

# Distortion coefficients
visiondt:lens:k1, k2, k3            # Radial distortion
visiondt:lens:p1, p2                # Tangential distortion
visiondt:lens:distortionModel       # "brown-conrady" or "fisheye"

# MTF data (stored as JSON or separate file reference)
visiondt:lens:mtfDataPath           # Path to MTF CSV/JSON file
visiondt:lens:mtfSpatialFreq        # Spatial frequencies array (lp/mm)
visiondt:lens:mtfContrastSagittal   # Sagittal MTF contrast values (0.0-1.0)
visiondt:lens:mtfContrastTangential # Tangential MTF contrast values (0.0-1.0)
visiondt:lens:mtfFieldPosition     # Field position (0.0=center, 1.0=edge)
visiondt:lens:mtfWavelength        # Wavelength for MTF measurement (nm)
visiondt:lens:mtfFStop              # F-stop at which MTF was measured
visiondt:lens:mtfAt50lpmm           # Quick reference: MTF at 50 lp/mm (sagittal)
visiondt:lens:mtfAt100lpmm          # Quick reference: MTF at 100 lp/mm (sagittal)

# Lens metadata
visiondt:lens:model                 # Lens model name
visiondt:lens:manufacturer          # Manufacturer
visiondt:lens:serialNumber          # Serial number
visiondt:lens:zemaxFilePath         # Source Zemax file path
```

---

## 4. Implementation Strategy

### 4.1 Phase 1: Zemax File Parser

**Goal:** Create Python module to parse Zemax files and extract optical parameters

**Components:**
1. **Zemax Parser Module** (`bootstrap/utils/zemax_parser.py`)
   - Parse `.ZMX` files (text-based parsing)
   - Extract `.ZAR` archives using `zmxtools`
   - Extract optical parameters (focal length, FOV, distortion, etc.)
   - Return structured dictionary of lens parameters

2. **Lens Data Structure:**
   ```python
   {
       "metadata": {
           "model": "Lens Model Name",
           "manufacturer": "Manufacturer",
           "zemax_file": "path/to/file.zmx",
           "version": "1.0"
       },
       "optical": {
           "focal_length_mm": 35.0,
           "working_distance_mm": 100.0,
           "f_number": 2.8,
           "field_of_view_deg": 45.0,
           "magnification": 0.25,
           "is_telecentric": True
       },
       "distortion": {
           "model": "brown-conrady",
           "k1": 0.1,
           "k2": 0.01,
           "k3": 0.001,
           "p1": 0.001,
           "p2": 0.001
       },
       "mtf": {
           "spatial_frequencies": [10, 20, 30, 40, 50, 100],  # lp/mm
           "contrast_sagittal": [0.95, 0.90, 0.85, 0.80, 0.75, 0.50],  # Sagittal MTF
           "contrast_tangential": [0.95, 0.90, 0.85, 0.80, 0.75, 0.50],  # Tangential MTF
           "field_positions": [0.0, 0.5, 1.0],  # Normalized field (0=center, 1=edge)
           "wavelength_nm": 550.0,  # Wavelength for MTF measurement
           "f_stop": 2.8,  # F-stop at which MTF was measured
           "field_dependent": True,  # True if MTF varies with field position
           "mtf_at_50lpmm": 0.75,  # Quick reference value
           "mtf_at_100lpmm": 0.50  # Quick reference value
       }
   }
   ```

---

### 4.2 Phase 2: Lens Library System

**Goal:** Create a library structure for storing and managing lens definitions

**Directory Structure:**
```
assets/
├── Lenses/
│   ├── Library/
│   │   ├── lens_library.json          # Master index of all lenses
│   │   ├── Manufacturer1/
│   │   │   ├── Model1/
│   │   │   │   ├── lens_data.json    # Parsed Zemax parameters
│   │   │   │   └── source.zmx        # Original Zemax file (optional)
│   │   │   └── Model2/
│   │   └── Manufacturer2/
│   └── Presets/
│       ├── telecentric_lenses.json
│       └── standard_lenses.json
```

**Lens Library Index (`lens_library.json`):**
```json
{
    "lenses": [
        {
            "id": "lens_001",
            "manufacturer": "Edmund Optics",
            "model": "TechSpec #67-857",
            "type": "telecentric",
            "focal_length_mm": 35.0,
            "working_distance_mm": 100.0,
            "data_path": "Library/EdmundOptics/TechSpec_67-857/lens_data.json",
            "zemax_path": "Library/EdmundOptics/TechSpec_67-857/source.zmx"
        }
    ]
}
```

---

### 4.3 Phase 3: Lens Profile Application to Cameras

**Goal:** Create capability to apply lens parameters from library to Omniverse cameras as custom profiles

**Components:**

1. **Lens Library Manager** (`bootstrap/utils/lens_library.py`)
   - Load lens library index
   - Search/filter lenses by parameters
   - Load lens data from JSON files
   - Return lens parameter dictionaries

2. **Lens Application Capability** (`bootstrap/capabilities/25_apply_lens_profile.py`)
   - Priority: 25 (runs after camera configuration, before transforms)
   - Finds cameras with `visiondt:lens:libraryId` attribute
   - Loads lens data from library
   - Applies optical parameters directly to Omniverse camera
   - Applies distortion model via Omniverse API
   - Sets Vision DT custom attributes for reference
   - **No CAD geometry** - parameters only

3. **Lens Profile Selection** (Future - custom extension)
   - Dropdown/selector for lens library
   - Preview lens parameters
   - Apply to selected camera via `visiondt:lens:libraryId` attribute

---

## 5. Implementation Code Examples

### 5.1 Zemax Parser (Simplified)

```python
# bootstrap/utils/zemax_parser.py

import re
from pathlib import Path
from typing import Dict, Optional

def parse_zmx_file(zmx_path: str) -> Dict:
    """
    Parse a Zemax .ZMX file and extract optical parameters.

    Args:
        zmx_path: Path to .ZMX file

    Returns:
        Dictionary containing lens parameters
    """
    with open(zmx_path, 'r') as f:
        content = f.read()

    lens_data = {
        "metadata": {},
        "optical": {},
        "distortion": {},
        "mtf": {}
    }

    # Extract version
    vers_match = re.search(r'VERS\s+(\S+)', content)
    if vers_match:
        lens_data["metadata"]["version"] = vers_match.group(1)

    # Extract focal length (from system data)
    focal_match = re.search(r'EFL\s+([\d.]+)', content)
    if focal_match:
        lens_data["optical"]["focal_length_mm"] = float(focal_match.group(1))

    # Extract F-number
    fnum_match = re.search(r'FNUM\s+([\d.]+)', content)
    if fnum_match:
        lens_data["optical"]["f_number"] = float(fnum_match.group(1))

    # Extract distortion coefficients (if available)
    # Note: Distortion format varies by Zemax version
    # This is a simplified example

    return lens_data
```

---

### 5.2 Lens Library Manager

```python
# bootstrap/utils/lens_library.py

import json
from pathlib import Path
from typing import List, Dict, Optional

class LensLibrary:
    def __init__(self, library_path: str):
        self.library_path = Path(library_path)
        self.index_path = self.library_path / "lens_library.json"
        self._index = None

    def load_index(self) -> Dict:
        """Load the lens library index."""
        if self._index is None:
            if self.index_path.exists():
                with open(self.index_path, 'r') as f:
                    self._index = json.load(f)
            else:
                self._index = {"lenses": []}
        return self._index

    def find_lens(self, lens_id: str) -> Optional[Dict]:
        """Find a lens by ID."""
        index = self.load_index()
        for lens in index["lenses"]:
            if lens["id"] == lens_id:
                return self.load_lens_data(lens["data_path"])
        return None

    def load_lens_data(self, data_path: str) -> Dict:
        """Load lens data from JSON file."""
        full_path = self.library_path / data_path
        with open(full_path, 'r') as f:
            return json.load(f)

    def search_lenses(self, **filters) -> List[Dict]:
        """Search lenses by parameters."""
        index = self.load_index()
        results = []
        for lens in index["lenses"]:
            match = True
            for key, value in filters.items():
                if lens.get(key) != value:
                    match = False
                    break
            if match:
                results.append(lens)
        return results
```

---

### 5.3 Lens Profile Application Capability

```python
# bootstrap/capabilities/25_apply_lens_profile.py

"""
Capability: Apply Lens Profile from Library

This capability applies lens parameters from the lens library to cameras
that have a visiondt:lens:libraryId attribute set. Lens parameters are
applied directly to Omniverse camera prims as custom profiles.
"""

from pxr import Usd, UsdGeom, Sdf
import sys
from pathlib import Path

# Add bootstrap utils to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import get_current_stage, find_prims_by_type
from utils.lens_library import LensLibrary

CAPABILITY_NAME = "Apply Lens Profile from Library"
CAPABILITY_DESCRIPTION = "Applies lens parameters from library to cameras as custom profiles"

def run():
    """Apply lens parameters to cameras."""
    stage = get_current_stage()
    if not stage:
        return

    # Initialize lens library
    library_path = "assets/Lenses/Library"
    lens_lib = LensLibrary(library_path)

    # Find all cameras
    cameras = find_prims_by_type(stage, "Camera")

    for camera_prim in cameras:
        # Check if camera has lens library ID
        lens_id_attr = camera_prim.GetAttribute("visiondt:lens:libraryId")
        if not lens_id_attr or not lens_id_attr.Get():
            continue

        lens_id = lens_id_attr.Get()
        lens_data = lens_lib.find_lens(lens_id)

        if not lens_data:
            continue

        # Apply optical parameters directly to camera
        apply_lens_profile_to_camera(camera_prim, lens_data)

def apply_lens_profile_to_camera(camera_prim: Usd.Prim, lens_data: Dict):
    """Apply lens parameters to a camera prim."""
    camera = UsdGeom.Camera(camera_prim)

    # Set focal length
    if "focal_length_mm" in lens_data.get("optical", {}):
        camera.GetFocalLengthAttr().Set(lens_data["optical"]["focal_length_mm"])

    # Set F-stop
    if "f_number" in lens_data.get("optical", {}):
        camera.GetFStopAttr().Set(lens_data["optical"]["f_number"])

    # Set focus distance (working distance)
    if "working_distance_mm" in lens_data.get("optical", {}):
        camera.GetFocusDistanceAttr().Set(lens_data["optical"]["working_distance_mm"])

    # Apply distortion
    if "distortion" in lens_data:
        apply_distortion(camera_prim, lens_data["distortion"])

    # Set Vision DT attributes for reference
    set_visiondt_lens_attributes(camera_prim, lens_data)

def apply_distortion(camera_prim: Usd.Prim, distortion_data: Dict):
    """Apply lens distortion model to camera."""
    model = distortion_data.get("model", "brown-conrady")

    if model == "brown-conrady":
        camera_prim.ApplyAPI("OmniLensDistortionOpenCvPinholeAPI")
        camera_prim.GetAttribute("lensDistortion:k1").Set(distortion_data.get("k1", 0.0))
        camera_prim.GetAttribute("lensDistortion:k2").Set(distortion_data.get("k2", 0.0))
        camera_prim.GetAttribute("lensDistortion:k3").Set(distortion_data.get("k3", 0.0))
        camera_prim.GetAttribute("lensDistortion:p1").Set(distortion_data.get("p1", 0.0))
        camera_prim.GetAttribute("lensDistortion:p2").Set(distortion_data.get("p2", 0.0))
    elif model == "fisheye":
        camera_prim.ApplyAPI("OmniLensDistortionFisheyeAPI")
        # Set fisheye parameters as needed

def set_visiondt_lens_attributes(camera_prim: Usd.Prim, lens_data: Dict):
    """Set Vision DT custom attributes for lens reference."""
    from utils.helpers import create_custom_attribute

    # Lens metadata
    if "model" in lens_data.get("metadata", {}):
        create_custom_attribute(
            camera_prim,
            "visiondt:lens:model",
            Sdf.ValueTypeNames.String,
            lens_data["metadata"]["model"]
        )

    if "manufacturer" in lens_data.get("metadata", {}):
        create_custom_attribute(
            camera_prim,
            "visiondt:lens:manufacturer",
            Sdf.ValueTypeNames.String,
            lens_data["metadata"]["manufacturer"]
        )

    # Optical parameters (for reference)
    optical = lens_data.get("optical", {})
    for key, value in optical.items():
        attr_name = f"visiondt:lens:{key}"
        if isinstance(value, float):
            create_custom_attribute(
                camera_prim,
                attr_name,
                Sdf.ValueTypeNames.Float,
                value
            )
        elif isinstance(value, bool):
            create_custom_attribute(
                camera_prim,
                attr_name,
                Sdf.ValueTypeNames.Bool,
                value
            )
```

---

## 6. Workflow for Adding New Lenses

### 6.1 Step-by-Step Process

1. **Parse Zemax File:**
   ```python
   from bootstrap.utils.zemax_parser import parse_zmx_file

   lens_data = parse_zmx_file("path/to/lens.zmx")
   ```

2. **Create Lens Data JSON:**
   ```python
   import json

   with open("lens_data.json", 'w') as f:
       json.dump(lens_data, f, indent=2)
   ```

3. **Add to Library Index:**
   ```python
   from bootstrap.utils.lens_library import LensLibrary

   lib = LensLibrary("assets/Lenses/Library")
   lib.add_lens({
       "id": "lens_001",
       "manufacturer": "Manufacturer",
       "model": "Model",
       "data_path": "Manufacturer/Model/lens_data.json",
       "zemax_path": "Manufacturer/Model/source.zmx"
   })
   ```

4. **Apply to Camera:**
   ```python
   camera_prim.GetAttribute("visiondt:lens:libraryId").Set("lens_001")
   # Bootstrap will automatically apply on next stage open
   ```

---

## 7. Recommended Python Packages

### Required:
- `zmxtools` - For extracting `.ZAR` archives
- `zospy` - For Zemax OpticStudio API access (if Zemax is installed)

### Optional:
- `numpy` - For numerical calculations (MTF, distortion)
- `scipy` - For interpolation and curve fitting
- `pandas` - For CSV/Excel data handling

---

## 8. Next Steps

1. **Create Zemax Parser Module**
   - Implement `.ZMX` file parsing
   - Test with sample Zemax files
   - Extract key optical parameters

2. **Set Up Lens Library Structure**
   - Create directory structure
   - Create lens library index JSON
   - Add sample lens data

3. **Implement Lens Application Capability**
   - Create `25_apply_lens_profile.py`
   - Test with sample lens data
   - Verify Omniverse camera parameters update correctly

4. **Test with Real Zemax Files**
   - Obtain sample Zemax lens files
   - Parse and extract parameters
   - Verify accuracy against Zemax OpticStudio

---

## 9. References

- **zmxtools Documentation:** https://zmxtools.readthedocs.io/
- **ZOSPy GitHub:** https://github.com/MREYE-LUMC/ZOSPy
- **Omniverse Camera Documentation:** https://docs.omniverse.nvidia.com/materials-and-rendering/latest/cameras.html
- **USD Python API:** https://openusd.org/release/api/index.html

---

## 10. MTF Parameter Details

### 10.1 MTF Parameters Handled by Implementation

The implementation will handle the following MTF parameters extracted from Zemax files:

**Core MTF Data:**
- **Spatial Frequencies** (lp/mm): Array of frequencies at which MTF is measured
  - Typical range: 0-200 lp/mm for machine vision lenses
  - Common frequencies: 10, 20, 30, 40, 50, 100 lp/mm
  - Stored as: `visiondt:lens:mtfSpatialFreq` (FloatArray)

- **Sagittal MTF** (0.0-1.0): Contrast transfer in radial direction
  - Measured perpendicular to the radial line from center
  - Stored as: `visiondt:lens:mtfContrastSagittal` (FloatArray)
  - One value per spatial frequency

- **Tangential MTF** (0.0-1.0): Contrast transfer in tangential direction
  - Measured along the radial line from center
  - Stored as: `visiondt:lens:mtfContrastTangential` (FloatArray)
  - One value per spatial frequency

**Field Position Variation:**
- **Field Position** (0.0-1.0): Normalized field position
  - 0.0 = center of field
  - 0.5 = mid-field
  - 1.0 = edge of field
  - Stored as: `visiondt:lens:mtfFieldPosition` (FloatArray)
  - Allows field-dependent MTF curves

**Measurement Conditions:**
- **Wavelength** (nm): Wavelength at which MTF was measured
  - Typically 550nm (green) for polychromatic systems
  - Stored as: `visiondt:lens:mtfWavelength` (Float)

- **F-Stop**: Aperture setting at which MTF was measured
  - MTF varies with f-stop (diffraction-limited performance)
  - Stored as: `visiondt:lens:mtfFStop` (Float)

**Quick Reference Values:**
- **MTF at 50 lp/mm**: Common specification point
  - Stored as: `visiondt:lens:mtfAt50lpmm` (Float)
  - Used for quick lens comparison

- **MTF at 100 lp/mm**: High-frequency performance indicator
  - Stored as: `visiondt:lens:mtfAt100lpmm` (Float)
  - Indicates fine detail resolution capability

**Data Storage:**
- **MTF Data Path**: Reference to external CSV/JSON file
  - Stored as: `visiondt:lens:mtfDataPath` (Asset)
  - Allows large MTF datasets without bloating USD files
  - Format: CSV with columns: frequency, sagittal, tangential, field_position

### 10.2 MTF Data Structure Example

```json
{
    "mtf": {
        "spatial_frequencies": [0, 10, 20, 30, 40, 50, 75, 100, 150, 200],
        "field_positions": [0.0, 0.5, 1.0],
        "wavelength_nm": 550.0,
        "f_stop": 2.8,
        "field_dependent": true,
        "data": {
            "0.0": {  // Center field
                "sagittal": [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.65, 0.50, 0.30, 0.15],
                "tangential": [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.65, 0.50, 0.30, 0.15]
            },
            "0.5": {  // Mid-field
                "sagittal": [0.98, 0.92, 0.87, 0.82, 0.77, 0.72, 0.60, 0.45, 0.25, 0.12],
                "tangential": [0.97, 0.91, 0.86, 0.81, 0.76, 0.71, 0.58, 0.43, 0.23, 0.10]
            },
            "1.0": {  // Edge field
                "sagittal": [0.95, 0.88, 0.82, 0.76, 0.70, 0.65, 0.52, 0.38, 0.20, 0.08],
                "tangential": [0.90, 0.82, 0.75, 0.68, 0.60, 0.55, 0.42, 0.28, 0.12, 0.05]
            }
        },
        "mtf_at_50lpmm": 0.75,  // Center field sagittal
        "mtf_at_100lpmm": 0.50  // Center field sagittal
    }
}
```

### 10.3 MTF Application in Omniverse

**Current Implementation Plan:**
- Store MTF data as custom attributes on camera prim
- Reference external CSV/JSON files for detailed MTF curves
- Quick reference values (MTF@50, MTF@100) stored directly as attributes

**Future Implementation (Post-Processing):**
- Apply MTF as post-process blur kernel
- Frequency-dependent blur based on MTF curves
- Field-dependent blur (center vs. edge sharpness)
- Integration with Omniverse's depth-of-field system

---

## 11. Implementation Tiers and Industrial Vision Requirements

### 11.1 Why MTF is Critical for Industrial Vision

Industrial machine vision systems rely on **edge detection** for:
- Dimensional measurement (edge-to-edge distances)
- Defect detection (scratches, chips, cracks)
- Part presence/absence verification
- Barcode/QR code reading
- OCR (character recognition)
- Alignment and positioning

**Without MTF modeling, synthetic images will have perfect edges while real camera images have MTF rolloff. This causes:**
- Edge detection algorithms calibrated on synthetic data to fail on real images
- Measurement accuracy simulations to be optimistically wrong
- Training data that doesn't match real camera output

**Post-process MTF is valid for industrial vision because:**
- Primary camera view is what matters (parts are directly imaged)
- Controlled lighting minimizes specular reflections
- Fixed working distance (MTF characterized at inspection distance)
- Telecentric lenses eliminate perspective distortion

### 11.2 Implementation Tiers

All lens optical parameters come from **Zemax file import**. The tiers describe how parameters are applied in Omniverse.

#### Tier 1: Native Integration (Render-Time)

Parameters applied directly to Omniverse camera at render time via USD APIs.

| Feature | Source (Zemax) | Omniverse API | Status |
|---------|---------------|---------------|--------|
| Focal Length | EFL from system data | `camera.GetFocalLengthAttr()` | 🟢 Active |
| F-Stop | FNUM from system data | `camera.GetFStopAttr()` | 🟢 Active |
| Working Distance | Object distance | `camera.GetFocusDistanceAttr()` | 🟢 Active |
| Aperture Size | Image height/width | `camera.GetHorizontalApertureAttr()` | 🟢 Active |
| Brown-Conrady Distortion | Distortion analysis | `OmniLensDistortionOpenCvPinholeAPI` | 🟢 Active |
| Fisheye Distortion | Distortion analysis | `OmniLensDistortionFisheyeAPI` | 🟢 Active |
| Telecentric Projection | Telecentricity flag | `camera.GetProjectionAttr("orthographic")` | 🟡 Needs Testing |

#### Tier 2: Post-Process (Active — Critical for Industrial Vision)

Parameters applied after rendering via image processing. **Essential for accurate edge simulation.**

| Feature | Source (Zemax) | Implementation | Priority |
|---------|---------------|----------------|----------|
| **MTF Blur Kernel** | MTF analysis data | Post-process convolution | 🔴 Critical |
| **Field-Dependent MTF** | MTF vs field position | Per-pixel blur kernel | 🔴 Critical |
| **Sagittal/Tangential MTF** | Directional MTF curves | Asymmetric PSF kernel | 🔴 Critical |
| PSF Convolution | Huygens PSF export | Direct PSF application | 🟡 High |
| Higher-Order Distortion | Extended distortion | Polynomial remapping | 🟡 High |
| Chromatic Aberration | Lateral/longitudinal CA | RGB channel shift | 🟡 Medium |

#### Tier 3: Reference Data (Stored for Documentation)

Data stored as USD attributes but not actively rendered. Available for export and documentation.

| Data | Source (Zemax) | Attribute | Purpose |
|------|---------------|-----------|---------|
| Wavelength-Dependent MTF | Polychromatic MTF | `visiondt:lens:mtfWavelength` | Reference |
| Full MTF Curves | MTF analysis | `visiondt:lens:mtfDataPath` | CSV/JSON export |
| Lens Metadata | File header | `visiondt:lens:model`, `manufacturer` | Traceability |
| Original Zemax Path | File system | `visiondt:lens:zemaxFilePath` | Source reference |

#### Tier 4: Platform Limitations (Not Implementable)

Features that cannot be implemented due to Omniverse architecture constraints.

| Feature | Limitation | Workaround |
|---------|-----------|------------|
| Spectral Rendering | RGB-only rendering (no wavelength rays) | Store SPD, convert to RGB |
| Ray-Based Chromatic Aberration | No lens element ray tracing | Post-process RGB shift |
| MTF on Reflections | Post-process doesn't affect secondary rays | Accept as limitation |
| True Wavelength-Dependent PSF | RGB color space only | Use averaged PSF |

### 11.3 Camera UI Integration — Lens Profile Selector

Lens profiles from Zemax files should be accessible when editing cameras in Omniverse.

**User Workflow:**

```
1. Select Camera in Omniverse
2. In Property Panel → "Vision DT Lens" section:
   ├── Lens Profile: [Dropdown: Select from Library]
   │   ├── Edmund Optics TechSpec #67-857 (Telecentric, 0.5×)
   │   ├── Navitar 1-60135 (Standard, 35mm)
   │   ├── Schneider Xenoplan 1.4/23 (Industrial, 23mm)
   │   └── [+ Import New Zemax Profile...]
   │
   ├── Quick Info (read-only):
   │   ├── Focal Length: 35.0 mm
   │   ├── Working Distance: 150.0 mm
   │   ├── F-Number: 2.8
   │   ├── MTF @ 50 lp/mm: 0.75
   │   └── Telecentric: Yes/No
   │
   └── Advanced (expandable):
       ├── Override F-Stop: [slider]
       ├── MTF Blur: [enabled/disabled]
       └── View Full Profile... [opens detail panel]
```

**Adding New Zemax Profiles:**

```
[+ Import New Zemax Profile...]
   │
   ├── Select Zemax File: [file picker for .zmx/.zar]
   ├── Lens Name: [auto-filled from file]
   ├── Manufacturer: [auto-filled or manual]
   │
   └── [Import] → Parses Zemax file
                 → Extracts all parameters
                 → Adds to lens library
                 → Available in dropdown
```

**Vision DT Attributes on Camera:**

```python
# Profile selection (user sets this)
visiondt:lens:libraryId          # e.g., "edmund_techspec_67857"

# Auto-populated from Zemax on profile selection
visiondt:lens:profileName        # "TechSpec #67-857"
visiondt:lens:manufacturer       # "Edmund Optics"
visiondt:lens:focalLengthMm      # 50.0
visiondt:lens:workingDistanceMm  # 150.0
visiondt:lens:fNumber            # 2.8
visiondt:lens:isTelecentric      # true
visiondt:lens:mtfAt50lpmm        # 0.75
visiondt:lens:mtfAt100lpmm       # 0.48
visiondt:lens:zemaxFilePath      # "Library/EdmundOptics/67-857/source.zmx"
visiondt:lens:mtfDataPath        # "Library/EdmundOptics/67-857/mtf_data.json"

# Post-process control
visiondt:lens:mtfBlurEnabled     # true (default for industrial vision)
visiondt:lens:distortionEnabled  # true
```

---

## 12. Advanced Features for Near-Zemax Performance

To achieve near-Zemax performance in Omniverse Vision DT, the pipeline must implement the following advanced features beyond basic lens parameter application.

**All data for these features comes from Zemax file import.**

### 12.1 Post-Processing MTF-Based Blur Kernel

**Purpose:** Apply field-dependent blur to final rendered images based on MTF curves.

**Implementation Requirements:**
- Extract MTF curves from lens data (sagittal/tangential, field-dependent)
- Convert MTF to spatial frequency response
- Generate blur kernel from MTF data
- Apply field-dependent blur (center vs. edge sharpness variation)
- Post-process rendered images with frequency-dependent blur

**Technical Approach:**
```python
# Pseudo-code for MTF-based blur kernel
def generate_mtf_blur_kernel(mtf_data, field_position, spatial_freq):
    """
    Generate blur kernel from MTF data.

    Args:
        mtf_data: MTF curve data (sagittal/tangential)
        field_position: Normalized field position (0.0-1.0)
        spatial_freq: Target spatial frequency (lp/mm)

    Returns:
        Blur kernel (2D array) for convolution
    """
    # Interpolate MTF at field position
    mtf_value = interpolate_mtf(mtf_data, field_position, spatial_freq)

    # Convert MTF to point spread function (PSF)
    psf = mtf_to_psf(mtf_value, spatial_freq)

    # Generate blur kernel from PSF
    blur_kernel = psf_to_kernel(psf)

    return blur_kernel

def apply_field_dependent_blur(image, lens_data, camera_params):
    """
    Apply field-dependent blur to rendered image.
    """
    height, width = image.shape[:2]
    blurred_image = np.zeros_like(image)

    for y in range(height):
        for x in range(width):
            # Calculate field position for this pixel
            field_pos = calculate_field_position(x, y, width, height)

            # Get MTF-based blur kernel for this field position
            kernel = generate_mtf_blur_kernel(
                lens_data["mtf"],
                field_pos,
                spatial_freq=50.0  # 50 lp/mm reference
            )

            # Apply blur to pixel region
            blurred_image[y, x] = convolve_pixel(image, x, y, kernel)

    return blurred_image
```

**Vision DT Attributes:**
- `visiondt:lens:mtfBlurEnabled` (Bool) - Enable MTF-based blur
- `visiondt:lens:mtfBlurKernelSize` (Int) - Blur kernel size in pixels
- `visiondt:lens:mtfBlurReferenceFreq` (Float) - Reference spatial frequency (lp/mm)

**Integration Points:**
- Post-process render output before saving
- Apply per-pixel based on field position
- Support both sagittal and tangential MTF curves

---

### 12.2 Chromatic Aberration Shader

**Purpose:** Add lateral and longitudinal chromatic aberration (CA) shift by wavelength.

**Implementation Requirements:**
- Extract chromatic aberration data from Zemax (lateral CA, longitudinal CA)
- Wavelength-dependent shift calculations
- RGB channel separation and shift
- Apply CA as post-process shader or material effect

**Technical Approach:**
```python
def apply_chromatic_aberration(image, lens_data, camera_params):
    """
    Apply chromatic aberration to image.

    Lateral CA: Wavelength-dependent shift in image plane
    Longitudinal CA: Wavelength-dependent focus shift
    """
    # Extract CA coefficients from lens data
    lateral_ca_r = lens_data["chromatic"]["lateral_ca_red"]  # pixels
    lateral_ca_b = lens_data["chromatic"]["lateral_ca_blue"]  # pixels
    longitudinal_ca = lens_data["chromatic"]["longitudinal_ca"]  # mm

    # Separate RGB channels
    r_channel = image[:, :, 0]
    g_channel = image[:, :, 1]  # Reference (green, typically 550nm)
    b_channel = image[:, :, 2]

    # Apply lateral CA (shift red and blue channels)
    r_shifted = shift_channel(r_channel, lateral_ca_r)
    b_shifted = shift_channel(b_channel, lateral_ca_b)

    # Apply longitudinal CA (blur based on focus shift)
    if longitudinal_ca != 0:
        r_blurred = apply_defocus_blur(r_shifted, longitudinal_ca, "red")
        b_blurred = apply_defocus_blur(b_shifted, longitudinal_ca, "blue")
    else:
        r_blurred = r_shifted
        b_blurred = b_shifted

    # Recombine channels
    ca_image = np.stack([r_blurred, g_channel, b_blurred], axis=2)

    return ca_image
```

**Vision DT Attributes:**
- `visiondt:lens:chromaticAberrationEnabled` (Bool) - Enable CA
- `visiondt:lens:lateralCaRed` (Float) - Lateral CA for red channel (pixels)
- `visiondt:lens:lateralCaBlue` (Float) - Lateral CA for blue channel (pixels)
- `visiondt:lens:longitudinalCa` (Float) - Longitudinal CA (mm focus shift)
- `visiondt:lens:caWavelengths` (FloatArray) - Wavelengths for CA measurement (nm)

**Zemax Data Extraction:**
- Lateral CA: Field-dependent wavelength shift
- Longitudinal CA: Wavelength-dependent focus position
- Typically measured at multiple field positions

---

### 12.3 Telecentric Projection Mode

**Purpose:** Override pinhole projection matrix to simulate parallel rays (telecentric lenses).

**Implementation Requirements:**
- Detect telecentric lens flag (`visiondt:lens:isTelecentric`)
- Override Omniverse camera projection matrix
- Implement orthographic or modified perspective projection
- Maintain proper scaling and field of view

**Technical Approach:**
```python
def apply_telecentric_projection(camera_prim, lens_data):
    """
    Apply telecentric projection to camera.

    Telecentric lenses have parallel chief rays, eliminating
    perspective distortion. This requires custom projection matrix.
    """
    if not lens_data["optical"].get("is_telecentric", False):
        return  # Use standard pinhole projection

    # Get telecentric parameters
    magnification = lens_data["optical"]["magnification"]
    fov_width = lens_data["optical"]["fov_width_mm"]
    fov_height = lens_data["optical"]["fov_height_mm"]

    # Calculate orthographic projection parameters
    # In telecentric: object size = image size / magnification
    ortho_width = fov_width / magnification
    ortho_height = fov_height / magnification

    # Override camera projection
    # Note: This may require custom Omniverse extension or shader
    camera = UsdGeom.Camera(camera_prim)

    # Set projection type to orthographic
    camera.GetProjectionAttr().Set("orthographic")

    # Set orthographic width/height
    camera.GetHorizontalApertureAttr().Set(ortho_width)
    camera.GetVerticalApertureAttr().Set(ortho_height)

    # Alternative: Custom projection matrix via shader
    # Implement parallel ray projection in vertex/fragment shader
```

**Vision DT Attributes:**
- `visiondt:lens:isTelecentric` (Bool) - Telecentric lens flag
- `visiondt:lens:telecentricType` (String) - "object-space", "image-space", or "double"
- `visiondt:lens:telecentricMagnification` (Float) - Magnification factor

**Projection Matrix Override:**
- Standard pinhole: `P = K [R|t]` (perspective)
- Telecentric: `P = K_ortho [R|t]` (orthographic or modified)
- Custom shader implementation may be required

---

### 12.4 PSF Convolution Engine

**Purpose:** Import Zemax Point Spread Function (PSF) data and convolve with rendered images for realistic blur and edge rolloff.

**Implementation Requirements:**
- Import PSF data from Zemax (2D or 3D PSF arrays)
- Support field-dependent PSF (center vs. edge)
- Support wavelength-dependent PSF (for chromatic effects)
- Efficient convolution engine for real-time or post-process

**Technical Approach:**
```python
def load_zemax_psf(psf_file_path):
    """
    Load PSF data from Zemax export.

    Zemax can export PSF as:
    - 2D image (PSF at specific field/wavelength)
    - 3D array (field position × wavelength × PSF data)
    - Text file with PSF coefficients
    """
    # Load PSF data (format depends on Zemax export)
    if psf_file_path.endswith('.png') or psf_file_path.endswith('.tif'):
        psf = cv2.imread(psf_file_path, cv2.IMREAD_GRAYSCALE)
    elif psf_file_path.endswith('.npy'):
        psf = np.load(psf_file_path)
    elif psf_file_path.endswith('.txt'):
        psf = load_psf_text(psf_file_path)

    # Normalize PSF
    psf = psf / np.sum(psf)

    return psf

def apply_psf_convolution(image, lens_data, field_position, wavelength_nm):
    """
    Apply PSF convolution to image.

    PSF provides most accurate blur simulation, including:
    - Diffraction effects
    - Aberrations
    - Edge rolloff
    - Field-dependent blur variation
    """
    # Get PSF for this field position and wavelength
    psf = get_psf_for_conditions(
        lens_data["psf"],
        field_position,
        wavelength_nm
    )

    # Convolve image with PSF
    # Apply per-channel if wavelength-dependent
    if len(psf.shape) == 3:  # Wavelength-dependent PSF
        convolved = np.zeros_like(image)
        for channel_idx, channel in enumerate(image.shape[2]):
            convolved[:, :, channel_idx] = cv2.filter2D(
                image[:, :, channel_idx],
                -1,
                psf[:, :, channel_idx]
            )
    else:  # Single PSF for all channels
        convolved = cv2.filter2D(image, -1, psf)

    return convolved
```

**Vision DT Attributes:**
- `visiondt:lens:psfDataPath` (Asset) - Path to PSF data file
- `visiondt:lens:psfEnabled` (Bool) - Enable PSF convolution
- `visiondt:lens:psfFieldDependent` (Bool) - PSF varies with field position
- `visiondt:lens:psfWavelengthDependent` (Bool) - PSF varies with wavelength
- `visiondt:lens:psfSize` (Int2) - PSF kernel size (width, height)

**PSF Data Formats:**
- 2D image files (PNG, TIFF) - Single PSF
- NumPy arrays (.npy) - Multi-dimensional PSF data
- Text files - PSF coefficients or tabular data
- Zemax export formats - Direct import from OpticStudio

**Performance Considerations:**
- PSF convolution is computationally expensive
- Consider GPU acceleration (CUDA, OpenCL)
- Pre-compute PSF kernels for common field positions
- Use separable PSF kernels when possible

---

### 12.5 Distortion Model Extension

**Purpose:** Support arbitrary polynomial distortion models instead of limiting to OpenCV's 5-coefficient Brown-Conrady model.

**Implementation Requirements:**
- Support higher-order polynomial distortion (6th, 8th order)
- Support custom distortion models (Fisheye, Equidistant, etc.)
- Implement distortion correction/application in post-process
- Handle distortion at render time or post-process

**Technical Approach:**
```python
def apply_polynomial_distortion(image, lens_data, direction="forward"):
    """
    Apply arbitrary polynomial distortion.

    Supports:
    - Brown-Conrady (k1, k2, k3, p1, p2) - OpenCV standard
    - Higher-order radial (k4, k5, k6, ...)
    - Custom polynomial models
    """
    distortion = lens_data["distortion"]
    model = distortion.get("model", "brown-conrady")

    if model == "brown-conrady":
        # Standard OpenCV model (5 coefficients)
        k1, k2, k3 = distortion["k1"], distortion["k2"], distortion["k3"]
        p1, p2 = distortion["p1"], distortion["p2"]

        # Apply via OpenCV
        camera_matrix = get_camera_matrix(image.shape)
        dist_coeffs = np.array([k1, k2, p1, p2, k3])

        if direction == "forward":
            distorted = cv2.undistort(image, camera_matrix, dist_coeffs)
        else:
            distorted = cv2.distort(image, camera_matrix, dist_coeffs)

    elif model == "polynomial":
        # Higher-order polynomial (6th, 8th order)
        coeffs = distortion["coefficients"]  # [k1, k2, k3, k4, k5, ...]
        order = len(coeffs)

        # Apply custom polynomial distortion
        distorted = apply_polynomial_distortion_custom(
            image,
            coeffs,
            order,
            direction
        )

    elif model == "fisheye":
        # Fisheye distortion model
        k1, k2, k3, k4 = distortion["k1"], distortion["k2"], distortion["k3"], distortion["k4"]

        distorted = cv2.fisheye.undistortImage(
            image,
            camera_matrix,
            np.array([k1, k2, k3, k4])
        )

    return distorted

def apply_polynomial_distortion_custom(image, coeffs, order, direction):
    """
    Apply custom polynomial distortion model.

    Radial distortion: r' = r * (1 + k1*r² + k2*r⁴ + k3*r⁶ + ...)
    """
    height, width = image.shape[:2]
    center_x, center_y = width / 2, height / 2

    # Create coordinate grids
    y, x = np.ogrid[:height, :width]
    x_norm = (x - center_x) / (width / 2)
    y_norm = (y - center_y) / (height / 2)

    # Calculate radial distance
    r_sq = x_norm**2 + y_norm**2
    r = np.sqrt(r_sq)

    # Calculate distortion factor
    distortion_factor = 1.0
    for i, k in enumerate(coeffs):
        power = 2 * (i + 1)  # r², r⁴, r⁶, ...
        distortion_factor += k * (r ** power)

    # Apply distortion
    if direction == "forward":
        x_distorted = x_norm * distortion_factor
        y_distorted = y_norm * distortion_factor
    else:  # reverse
        x_distorted = x_norm / distortion_factor
        y_distorted = y_norm / distortion_factor

    # Remap image
    map_x = (x_distorted * (width / 2) + center_x).astype(np.float32)
    map_y = (y_distorted * (height / 2) + center_y).astype(np.float32)

    distorted = cv2.remap(image, map_x, map_y, cv2.INTER_LINEAR)

    return distorted
```

**Vision DT Attributes:**
- `visiondt:lens:distortionModel` (String) - Model type: "brown-conrady", "polynomial", "fisheye", "custom"
- `visiondt:lens:distortionOrder` (Int) - Polynomial order (2, 4, 6, 8, ...)
- `visiondt:lens:distortionCoefficients` (FloatArray) - All distortion coefficients
- `visiondt:lens:distortionCenterX` (Float) - Distortion center X (pixels, optional)
- `visiondt:lens:distortionCenterY` (Float) - Distortion center Y (pixels, optional)

**Supported Models:**
- **Brown-Conrady**: Standard OpenCV model (k1, k2, k3, p1, p2)
- **Polynomial**: Higher-order radial (k1-k8 or more)
- **Fisheye**: Fisheye projection model (k1-k4)
- **Equidistant**: Equidistant fisheye
- **Stereographic**: Stereographic fisheye
- **Custom**: User-defined polynomial coefficients

**Zemax Distortion Models:**
- Zemax uses F-Tan(θ) distortion model
- May require conversion to polynomial form
- Field-dependent distortion supported

---

### 12.6 Implementation Priority and Dependencies

**Recommended Implementation Order:**

1. **Phase 1: Foundation** (Zemax Parser + Lens Library)
   - Zemax file parser module
   - Lens library JSON structure
   - Camera attribute application
   - Focal length, FOV, basic distortion

2. **Phase 2: MTF System** (Critical for Industrial Vision)
   - MTF data extraction from Zemax
   - Post-process MTF blur kernel
   - Field-dependent blur (center vs edge)
   - **Priority:** 🔴 Critical — Required for edge-based inspection

3. **Phase 3: Distortion Extension** (12.5)
   - Higher-order polynomial distortion
   - Multiple distortion models
   - **Dependency:** Zemax distortion analysis data

4. **Phase 4: Telecentric Projection** (12.3)
   - Override projection matrix
   - **Dependency:** Zemax telecentricity parameters

5. **Phase 5: Chromatic Aberration** (12.2)
   - Lateral and longitudinal CA from Zemax
   - **Dependency:** Zemax CA analysis data

6. **Phase 6: PSF Convolution** (12.4)
   - Direct Zemax PSF import
   - GPU-accelerated convolution
   - **Dependency:** Zemax Huygens PSF export

**Performance Considerations:**
- Post-process features (MTF blur, CA, PSF) can be GPU-accelerated
- Telecentric projection requires render-time modification
- Distortion can be applied at render time or post-process
- Consider caching computed kernels/PSFs for performance

---

## 13. Platform Limitations and Constraints

### 13.1 Omniverse Rendering Architecture

| Constraint | Impact | Mitigation |
|------------|--------|------------|
| **RGB-only rendering** | No spectral ray tracing | Store SPD data, convert to RGB |
| **No lens element simulation** | CA happens in post, not at ray level | Accept as approximation |
| **Post-process is 2D only** | Doesn't affect reflections/refractions | Valid for industrial vision (primary view) |
| **iray deprecated (Oct 2025)** | Some advanced features unavailable | Use RTX Path Tracing |

### 13.2 What Works Well for Industrial Vision

Post-process MTF/distortion IS valid for industrial vision because:

1. **Primary camera view is everything** — Parts are directly imaged, not through mirrors
2. **Controlled lighting** — Diffuse lighting minimizes specular reflections
3. **Matte surfaces** — Industrial parts often have non-reflective coatings
4. **Fixed working distance** — MTF characterized at inspection distance
5. **Telecentric lenses** — No perspective distortion, consistent magnification

### 13.3 What Does NOT Work

Post-process effects will NOT correctly simulate:
- MTF on reflective surfaces (mirrors, polished metal)
- Chromatic aberration in refracted light (through glass)
- Field-dependent effects on secondary rays
- Spectral/wavelength-accurate rendering

**For these use cases, external spectral renderers (Mitsuba 3, PBRT) would be required.**

---

## 14. Open Questions

1. **Zemax File Access:**
   - Do you have Zemax OpticStudio installed for ZOSPy API access?
   - Or do you only have `.ZMX`/`.ZAR` files to parse?

2. **Lens Library Scope:**
   - How many lenses are in the library?
   - What manufacturers/models are included?

3. **MTF Data Availability:**
   - Is MTF data available in Zemax files?
   - Are sagittal/tangential curves both available?
   - Is field-dependent MTF data available?

4. **Distortion Models:**
   - Which distortion model does Zemax use?
   - How to convert to OpenCV Brown-Conrady model?

---

## 15. Document History

| Date | Change | Author |
|------|--------|--------|
| 2025-12-08 | Initial research document | Vision DT Project |
| 2025-12-08 | Added MTF parameters specification | Vision DT Project |
| 2025-12-08 | Added advanced features for near-Zemax performance | Vision DT Project |
| 2025-12-09 | Added implementation tiers, industrial vision requirements, camera UI integration, platform limitations | Vision DT Project |

---

*All lens optical data flows from Zemax file import → Lens Library → Camera Attributes → Render/Post-Process*

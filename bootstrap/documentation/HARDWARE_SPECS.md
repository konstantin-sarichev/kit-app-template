# Vision DT Hardware Specifications

## Overview

This document defines the hardware parameters required for accurate digital twin simulation of optical inspection systems. All specifications should be derived from manufacturer datasheets.

---

## Camera Specifications

| Parameter | Description | Why It's Needed | Priority |
|-----------|-------------|-----------------|----------|
| **Sensor model** | Manufacturer and model (e.g., Sony IMX) | Sets baseline for noise, dynamic range, spectral response | Critical |
| **Sensor format** | Size classification (1", 1/1.8", 2/3") | Determines optical magnification and FOV | Critical |
| **Active area** | Physical light-sensitive region (mm) | Computes real-world scaling between pixels and geometry | Critical |
| **Resolution** | Total pixels (width × height) | Affects sampling density and feature detectability | Critical |
| **Pixel pitch** | Distance between pixels (µm) | Links optical blur and sampling; models diffraction and MTF | Critical |
| **Bit depth** | Bits per pixel (8-bit, 12-bit, 16-bit) | Controls quantization precision and gray-level accuracy | Critical |
| **Read noise** | Variation during readout (e⁻ rms) | Sets noise floor for low-light and short exposures | Critical |
| **Shutter type** | Rolling or global exposure | Determines motion distortion in simulation | Critical |
| **Exposure/Strobe timing** | Accuracy and jitter of exposure start | Critical for synchronization with lighting/motion | Critical |
| **Intrinsic parameters** | Camera matrix (focal length, principal point, skew) | Core of geometric projection and ray tracing | Critical |
| **Distortion coefficients** | Radial and tangential distortion | Essential for realism and measurement accuracy | Critical |
| **MTF** | Modulation Transfer Function | Defines sharpness and blur for realistic rendering | Critical |

---

## Lens Specifications

| Parameter | Description | Why It's Needed | Priority |
|-----------|-------------|-----------------|----------|
| **Focal length** | Distance from principal plane to image plane (mm) | Defines projection geometry and scaling | Critical |
| **Working distance (WD)** | Object distance at focus | Determines magnification, DOF, and scene placement | Critical |
| **Telecentricity** | Parallel chief rays (object/image-space telecentric) | Eliminates perspective distortion for measurement | Critical |
| **F-number (f/#)** | Focal length to aperture ratio | Determines exposure, diffraction blur, and DOF | Critical |
| **MTF** | Contrast transfer vs spatial frequency | Sets perceived sharpness and AI dataset quality | Critical |

---

## Light Specifications

### Geometry & Layout

| Parameter | Description |
|-----------|-------------|
| Emitter type/shape | Rect, disk, line, ring |
| Emitter size | Physical width/height (should exceed FOV) |
| Emitter pose | Position and orientation relative to optical axis |
| Working plane distance | Distance from emitter to object plane |
| Baffles/hoods | Stray-light control presence |

### Angular / Beam Properties

| Parameter | Description |
|-----------|-------------|
| Collimation / NA | Divergence half-angle or numerical aperture |
| Angular intensity distribution | Lambertian vs. collimated vs. IES profile |
| Shadow casting | On/off depending on geometry |
| Polar pattern uniformity | Center-to-edge variation at object plane |

### Spectral Properties

| Parameter | Description |
|-----------|-------------|
| Spectrum | White (broad) or narrowband (365/385/405/450/520/625 nm) |
| Bandwidth / FWHM | Spectral width (e.g., 20 nm for LEDs) |
| CCT (if white) | Correlated color temperature |
| Custom SPD | Load from CSV for accurate spectral simulation |

### Spatial Uniformity

| Parameter | Description |
|-----------|-------------|
| Uniformity profile | Custom uniformity map if available |

---

## Vision DT Attributes (Reference)

### Camera Attributes (`visiondt:camera:`)
- `magnification` (Float) — Optical magnification
- `workingDistance` (Float, mm) — Working distance
- `fovWidth` (Float, mm) — Field of view width
- `fovHeight` (Float, mm) — Field of view height
- `isTelecentric` (Bool) — Telecentric flag

### Light Attributes (`visiondt:` and `visiondt:led:`)

See `LIGHTING_AND_OPTICS.md` for complete attribute reference.

---

## Data Sources

- Manufacturer datasheets
- Optical design software exports (Zemax, Code V)
- Measured calibration data
- IES photometric files

---

*Document Version: 1.0*
*Last Updated: December 2025*



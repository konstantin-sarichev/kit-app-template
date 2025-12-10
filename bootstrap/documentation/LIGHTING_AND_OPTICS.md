# Vision DT Lighting and Optics System

## Overview

The Vision Digital Twin lighting system provides **physically accurate** light simulation based on real LED and lamp specifications. Unlike Omniverse's default RGB/Kelvin controls, Vision DT uses:

- **Spectral Power Distribution (SPD)** for color accuracy
- **Photometric values (mcd, mlm)** for brightness accuracy
- **Real-time synchronization** for interactive parameter adjustment

This enables accurate simulation of machine vision lighting scenarios where spectral characteristics and precise brightness control are critical.

---

## Architecture

### Module Structure

```
bootstrap/
├── capabilities/
│   ├── 40_add_custom_attributes.py    # Basic visiondt: temperature attrs
│   ├── 45_configure_advanced_lighting.py  # Multi-spectrum Kelvin
│   └── 46_configure_led_profile.py    # LED SPD + luminosity attrs
├── utils/
│   ├── lighting.py          # Kelvin-to-RGB conversion
│   ├── spectral.py          # SPD processing, CIE color matching
│   ├── luminous.py          # Photometric conversions (mcd→nits)
│   ├── light_watcher.py     # Auto-add attrs to new lights
│   ├── color_sync.py        # Real-time Kelvin sync
│   └── led_color_sync.py    # Real-time SPD + luminosity sync
└── lighting-profiles/
    └── spd/                 # SPD CSV library
        ├── D65_daylight_6500K.csv
        ├── white_LED_cool_5000K.csv
        ├── white_LED_warm_3000K.csv
        ├── flat_equal_energy_white.csv
        └── incandescent_2700K.csv
```

### Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BOOTSTRAP (on stage open)                    │
├─────────────────────────────────────────────────────────────────────┤
│  1. Capabilities run in order (40→45→46)                            │
│  2. Add visiondt: attributes to existing lights                     │
│  3. Start watchers for real-time sync                               │
└─────────────────────────────────────────────────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         ▼                          ▼                          ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  LightWatcher   │      │   ColorSync     │      │  LEDColorSync   │
│                 │      │                 │      │                 │
│ • Detects new   │      │ • Watches temp  │      │ • Watches SPD   │
│   light prims   │      │   attributes    │      │   attributes    │
│ • Adds all      │      │ • Kelvin → RGB  │      │ • SPD → RGB     │
│   visiondt:     │      │ • Overrides OV  │      │ • mcd → nits    │
│   attributes    │      │   color temp    │      │ • Overrides OV  │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

## 1. SPD (Spectral Power Distribution) System

### Purpose

Convert real spectral data to accurate RGB color using CIE 1931 color matching functions. This provides more accurate color representation than simplified RGB or Kelvin values.

### SPD Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| `gaussian` | Peak wavelength + FWHM bandwidth | Quick LED simulation |
| `csv` | Load from CSV file | Real datasheet curves |
| `manual` | Direct wavelength/intensity arrays | Custom profiles |

### Attributes

#### Vision DT LED - Spectral Group

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `visiondt:led:enabled` | Bool | False | Enable LED color mode |
| `visiondt:led:spdMode` | String | "gaussian" | Mode selection |
| `visiondt:led:peakWavelength` | Float | 0.0 | Peak λ (nm) for Gaussian |
| `visiondt:led:dominantWavelength` | Float | 0.0 | Dominant λ (nm) |
| `visiondt:led:spectralBandwidth` | Float | 30.0 | FWHM (nm) for Gaussian |
| `visiondt:led:whiteMix` | Float | 0.0 | Blend with white (0-1) |

#### Vision DT LED - SPD Data Group

| Attribute | Type | Description |
|-----------|------|-------------|
| `visiondt:led:spdCsvPath` | Asset | Path to CSV file |
| `visiondt:led:spdWavelengths` | FloatArray | Wavelength data (nm) |
| `visiondt:led:spdIntensities` | FloatArray | Intensity data (0-1) |
| `visiondt:led:spdDataJson` | String | JSON import/export |
| `visiondt:led:spdInfo` | String | Read-only info summary |

### Color Calculation Pipeline

```
SPD Data (λ, I)
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  CIE 1931 Color Matching Integration                        │
│                                                             │
│  X = ∫ SPD(λ) × x̄(λ) dλ                                    │
│  Y = ∫ SPD(λ) × ȳ(λ) dλ                                    │
│  Z = ∫ SPD(λ) × z̄(λ) dλ                                    │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  XYZ to Linear sRGB                                         │
│                                                             │
│  [R]   [ 3.2406 -1.5372 -0.4986] [X]                       │
│  [G] = [-0.9689  1.8758  0.0415] [Y]                       │
│  [B]   [ 0.0557 -0.2040  1.0570] [Z]                       │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  White Mix Blending                                         │
│                                                             │
│  result = white × whiteMix + spectral × (1 - whiteMix)     │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
inputs:color (Omniverse light attribute)
```

### CSV File Format

Standard two-column format:

```csv
wavelength_nm,relative_power
380,0.01
400,0.05
450,0.85
500,0.62
530,1.00
600,0.45
700,0.10
```

- Supports comma, tab, or semicolon delimiters
- Header row optional (auto-detected)
- Intensities auto-normalized to 0-1 range
- Wavelength range: typically 380-780nm

### SPD Library

Pre-built profiles in `_build/bootstrap/lighting-profiles/spd/`:

| File | Color Temp | Description |
|------|------------|-------------|
| `D65_daylight_6500K.csv` | 6500K | CIE standard daylight |
| `white_LED_cool_5000K.csv` | 5000K | Phosphor white LED (cool) |
| `white_LED_warm_3000K.csv` | 3000K | Phosphor white LED (warm) |
| `flat_equal_energy_white.csv` | ~5500K | Equal power reference |
| `incandescent_2700K.csv` | 2700K | Black-body radiator |

### Usage Example

```python
# In Omniverse Script Editor
import omni.usd
from pxr import Sdf

stage = omni.usd.get_context().get_stage()
light = stage.GetPrimAtPath("/World/SphereLight")

# Enable CSV mode
light.GetAttribute("visiondt:led:spdMode").Set("csv")
light.GetAttribute("visiondt:led:spdCsvPath").Set(
    Sdf.AssetPath("G:/Vision_Example_1/kit-app-template/_build/bootstrap/lighting-profiles/spd/D65_daylight_6500K.csv")
)
light.GetAttribute("visiondt:led:enabled").Set(True)

# Optional: blend towards white
light.GetAttribute("visiondt:led:whiteMix").Set(0.3)
```

---

## 2. Luminosity System

### Purpose

Convert real LED datasheet brightness specifications (millicandelas, millilumens) to Omniverse light intensity values. This enables accurate brightness matching between simulation and physical hardware.

### Photometric Concepts

| Term | Symbol | Unit | Description |
|------|--------|------|-------------|
| Luminous Intensity | Iv | mcd (millicandela) | Light per solid angle |
| Luminous Flux | Φv | mlm (millilumen) | Total light output |
| Luminance | Lv | nit (cd/m²) | Light per area per angle |

### Attributes

#### Vision DT LED - Brightness Group

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `visiondt:led:useLuminousIntensity` | Bool | False | Enable datasheet brightness |
| `visiondt:led:luminousIntensity` | Float | 0.0 | Intensity in mcd |
| `visiondt:led:luminousFlux` | Float | 0.0 | Flux in mlm |
| `visiondt:led:emitterWidthMm` | Float | 0.5 | LED die width (mm) |
| `visiondt:led:emitterHeightMm` | Float | 0.3 | LED die height (mm) |
| `visiondt:led:currentRatio` | Float | 1.0 | Dimming factor (0-1) |

#### Vision DT LED - Computed Group (Read-Only)

| Attribute | Type | Description |
|-----------|------|-------------|
| `visiondt:led:computedNits` | Float | Calculated luminance |
| `visiondt:led:computedIntensity` | Float | Omniverse intensity |
| `visiondt:led:computedExposure` | Float | Omniverse exposure |
| `visiondt:led:computedColor` | Color3f | Calculated RGB |

### Conversion Pipeline

```
Datasheet Values
      │
      ├── mcd (luminous intensity)
      │   └── nits = mcd / (area_mm² × 1e-6)
      │
      └── mlm (luminous flux)
          └── nits = mlm / (π × area_mm² × 1e-6 × beam_factor)
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│  Nits to Omniverse Mapping                                  │
│                                                             │
│  Omniverse: effective_luminance = intensity × 2^exposure   │
│                                                             │
│  intensity = clamp(nits, 0.01, 100)                        │
│  exposure = log2(nits / intensity)                         │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
inputs:intensity + inputs:exposure (Omniverse)
```

### Example: OSRAM LT QH9G

From datasheet:
- Luminous intensity: 90 mcd (Q2 brightness group)
- Emitter size: 0.5 × 0.3 mm

Calculation:
```
area = 0.5 × 0.3 = 0.15 mm²
nits = 90 / (0.15 × 1e-6) = 600,000 cd/m²

intensity = 100 (clamped)
exposure = log2(600000 / 100) = 12.5
```

### Usage Example

```python
light = stage.GetPrimAtPath("/World/SphereLight")

# Enable luminosity mode
light.GetAttribute("visiondt:led:useLuminousIntensity").Set(True)
light.GetAttribute("visiondt:led:luminousIntensity").Set(90.0)  # mcd
light.GetAttribute("visiondt:led:emitterWidthMm").Set(0.5)
light.GetAttribute("visiondt:led:emitterHeightMm").Set(0.3)

# Check computed values
print(light.GetAttribute("visiondt:led:computedNits").Get())
print(light.GetAttribute("visiondt:led:computedIntensity").Get())
print(light.GetAttribute("visiondt:led:computedExposure").Get())
```

---

## 3. Multi-Spectrum Kelvin System

### Purpose

Provides per-channel color temperature control for advanced color mixing, while maintaining compatibility with traditional Kelvin-based workflows.

### Color Temperature Reference

| Temperature | Color Description | Use Case |
|-------------|-------------------|----------|
| **1800K** | Candlelight | Warm ambient |
| **2700K** | Incandescent bulb | Warm white, indoor |
| **3000K** | Warm white LED | Studio, indoor |
| **4000K** | Cool white | Office, neutral |
| **5000K** | Daylight | Balanced white |
| **5500K** | Noon daylight | Photography standard |
| **6500K** | **Default** - Daylight | True neutral white |
| **7500K** | Overcast sky | Cool white |
| **9000K** | Blue sky | Very cool |
| **10000K+** | Clear blue sky | Ultra cool/blue |

### Vision System Typical Ranges

| Application | Temperature Range | Notes |
|-------------|-------------------|-------|
| Machine Vision | 5500K - 6500K | Neutral white for accuracy |
| Red Inspection | 2000K - 3000K | Warm red emphasis |
| Green Inspection | 5000K - 6000K | Neutral to slightly cool |
| Blue/UV | 7500K - 10000K+ | Cool to very cool |
| Multi-spectral | Variable per channel | Independent control |

### Attributes (Vision DT Group)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `visiondt:overallTemperature` | Float | 6500.0 | Overall Kelvin temperature |
| `visiondt:redTemperature` | Float | 6500.0 | Red channel Kelvin |
| `visiondt:greenTemperature` | Float | 6500.0 | Green channel Kelvin |
| `visiondt:blueTemperature` | Float | 6500.0 | Blue channel Kelvin |
| `visiondt:iesProfile` | Asset | "" | IES profile path |

### Algorithm

```
For each channel (R, G, B):
  1. Convert channel Kelvin to RGB using Tanner Helland algorithm
  2. Extract the relevant channel value

Final color:
  R = kelvin_to_rgb(redTemp).r × kelvin_to_rgb(overallTemp).r
  G = kelvin_to_rgb(greenTemp).g × kelvin_to_rgb(overallTemp).g
  B = kelvin_to_rgb(blueTemp).b × kelvin_to_rgb(overallTemp).b
```

### Usage Scenarios

**Neutral Daylight (6500K):**
```
Overall: 6500K, Red: 6500K, Green: 6500K, Blue: 6500K
→ True neutral white, standard daylight
```

**Warm Indoor Lighting (3000K):**
```
Overall: 3000K, Red: 3000K, Green: 3000K, Blue: 3000K
→ Warm white LED, indoor feel
```

**Red-Emphasized Inspection:**
```
Overall: 6500K, Red: 3000K, Green: 6500K, Blue: 8000K
→ Red channel emphasized, high contrast for red defects
```

**Green Machine Vision:**
```
Overall: 5500K, Red: 7000K, Green: 5000K, Blue: 7000K
→ Green-dominant for high-contrast imaging
```

**Blue/UV Simulation:**
```
Overall: 8000K, Red: 10000K, Green: 9000K, Blue: 6000K
→ Cool blue-shifted light, UV-like appearance
```

---

## 4. Real-Time Synchronization

### Watchers

Three watcher modules monitor for attribute changes and automatically update light properties:

| Watcher | Triggers On | Updates |
|---------|-------------|---------|
| `LightWatcher` | New light creation | Adds all visiondt: attributes |
| `ColorSync` | visiondt:*Temperature | inputs:color |
| `LEDColorSync` | visiondt:led:* | inputs:color, inputs:intensity, inputs:exposure |

### Trigger Attributes

#### Color Triggers (LEDColorSync)
- `visiondt:led:enabled`
- `visiondt:led:spdMode`
- `visiondt:led:peakWavelength`
- `visiondt:led:dominantWavelength`
- `visiondt:led:spectralBandwidth`
- `visiondt:led:spdWavelengths`
- `visiondt:led:spdIntensities`
- `visiondt:led:spdCsvPath`
- `visiondt:led:whiteMix`

#### Luminosity Triggers (LEDColorSync)
- `visiondt:led:useLuminousIntensity`
- `visiondt:led:luminousIntensity`
- `visiondt:led:luminousFlux`
- `visiondt:led:emitterWidthMm`
- `visiondt:led:emitterHeightMm`
- `visiondt:led:viewingAngleH`
- `visiondt:led:viewingAngleV`
- `visiondt:led:currentRatio`

### Override Behavior

Vision DT settings **always override** Omniverse defaults when enabled:

1. `inputs:enableColorTemperature` is set to `False`
2. `inputs:color` is set from Vision DT calculation
3. `inputs:intensity` and `inputs:exposure` are set from Vision DT (if luminosity enabled)

---

## 5. Supported Light Types

All Vision DT lighting features work with:

- `DomeLight`
- `RectLight`
- `DiskLight`
- `SphereLight`
- `DistantLight`
- `CylinderLight`

---

## 6. Best Practices

### For Machine Vision Simulation

1. **Use SPD mode** for color-critical applications
2. **Use datasheet mcd values** for brightness accuracy
3. **Set emitter dimensions** from LED package datasheet
4. **Store SPD files** in `assets/SPD/` or `lighting-profiles/spd/`

### For General Lighting

1. **Use Kelvin temperatures** for quick setup
2. **Use whiteMix** to soften saturated LED colors
3. **Use preset SPD files** for realistic white sources

### File Organization

```
project/
├── assets/
│   └── SPD/
│       ├── custom_led_spectrum.csv
│       └── measured_lamp.csv
└── _build/bootstrap/lighting-profiles/spd/
    └── (standard library files)
```

---

## 7. Troubleshooting

### SPD CSV Not Loading

- **Use absolute paths** (not relative)
- Check file exists at specified location
- Verify CSV format (wavelength_nm, relative_power columns)

### Luminosity Not Working

- Enable `visiondt:led:useLuminousIntensity`
- Set non-zero `luminousIntensity` (mcd) value
- Set realistic emitter dimensions (not 0)

### Color Too Saturated

- Increase `whiteMix` (0.5-0.8 for realistic white LEDs)
- Check SPD data represents intended light source

### Changes Not Taking Effect

- Verify editing `_build/bootstrap/` files (not `bootstrap/`)
- Restart Omniverse after code changes
- Check console for `[Vision DT]` error messages

---

## 8. References

- CIE 1931 Color Space: https://en.wikipedia.org/wiki/CIE_1931_color_space
- Kelvin to RGB: Tanner Helland algorithm
- Photometry: https://en.wikipedia.org/wiki/Photometry_(optics)
- USD Light Schema: https://openusd.org/docs/api/class_usd_lux_light_a_p_i.html

# Vision DT Bootstrap System

## Overview

The Bootstrap System automatically configures Omniverse stages for the Vision Digital Twin environment. When a stage opens, it ensures proper units, optical parameters, lighting attributes, and validation are applied consistently.

---

## How It Works

### Automatic Execution

```
Application Start
      ↓
Extension Loads (my_company.my_usd_composer_setup_extension)
      ↓
Subscribe to Stage Open Events
      ↓
User Opens/Creates Stage
      ↓
Wait 5 frames (stage stability)
      ↓
Run all capabilities in numeric order
      ↓
Display status message
```

### No User Action Required

- Bootstrap runs automatically on every stage open
- Configures all lights, cameras, and stage properties
- Reports status in the Omniverse console

---

## Capabilities

Capabilities are modular scripts in `bootstrap/capabilities/` that run in numeric order:

| Priority | Capability | Purpose |
|----------|------------|---------|
| 00 | `set_units_mm.py` | Set stage units to millimeters (metersPerUnit=0.001) |
| 40 | `add_custom_attributes.py` | Add Vision DT temperature attributes to lights |
| 45 | `configure_advanced_lighting.py` | Multi-spectrum Kelvin color calculation |
| 46 | `configure_led_profile.py` | LED SPD and luminosity attributes |

### Capability Interface

Each capability module must have:

```python
CAPABILITY_NAME = "Display Name"
CAPABILITY_DESCRIPTION = "What it does"

def run(stage=None) -> tuple:
    """Returns (success: bool, message: str)"""
    return True, "Success message"
```

---

## Adding New Capabilities

1. Create file: `_build/bootstrap/capabilities/NN_my_capability.py`
2. Use numeric prefix (NN) to control execution order
3. Define required `CAPABILITY_NAME`, `CAPABILITY_DESCRIPTION`, and `run()` function
4. Restart Omniverse to test

### Template

```python
"""
Capability: My Feature

Description of what this capability does.
Priority: NN (runs after XX, before YY)
"""

import logging
import carb
from pxr import Usd, Sdf

CAPABILITY_NAME = "My Feature"
CAPABILITY_DESCRIPTION = "Description of what this does"

logger = logging.getLogger("vision_dt.capability.my_feature")

def _log_info(msg):
    logger.info(msg)
    carb.log_info(f"[Vision DT] {msg}")

def run(stage=None) -> tuple:
    try:
        if stage is None:
            import omni.usd
            stage = omni.usd.get_context().get_stage()

        if not stage:
            return True, "No stage (skipped)"

        # Your implementation here

        return True, "Success message"
    except Exception as e:
        _log_info(f"Error: {e}")
        return False, str(e)
```

---

## Real-Time Watchers

After capabilities run, watchers monitor for changes:

| Watcher | Monitors | Updates |
|---------|----------|---------|
| `LightWatcher` | New light creation | Adds Vision DT attributes to new lights |
| `ColorSync` | `visiondt:*Temperature` changes | Updates `inputs:color` |
| `LEDColorSync` | `visiondt:led:*` changes | Updates color from SPD, intensity from mcd |

This enables real-time parameter adjustment without restarting.

---

## Directory Structure

```
bootstrap/
├── loader.py              # Core orchestration
├── __init__.py            # Package init
├── capabilities/          # Capability modules
│   ├── 00_set_units_mm.py
│   ├── 40_add_custom_attributes.py
│   ├── 45_configure_advanced_lighting.py
│   └── 46_configure_led_profile.py
├── utils/                 # Shared utilities
│   ├── helpers.py         # Stage/prim helpers
│   ├── lighting.py        # Kelvin-to-RGB
│   ├── spectral.py        # SPD processing
│   ├── luminous.py        # Photometric conversions
│   ├── light_watcher.py   # Auto-add attrs to new lights
│   ├── color_sync.py      # Real-time Kelvin sync
│   └── led_color_sync.py  # Real-time SPD+luminosity sync
├── lighting-profiles/     # SPD data library
│   └── spd/               # CSV spectral files
└── documentation/         # Architecture docs
```

---

## Console Messages

### Successful Bootstrap

```
[vision_dt.bootstrap] Vision DT Bootstrap system initialized
[vision_dt.bootstrap] Found 4 capability modules
[vision_dt.bootstrap] Loading capability: 00_set_units_mm
[vision_dt.bootstrap] ✓ 00_set_units_mm: Set to 0.001 meters per unit
...
[vision_dt.bootstrap] BOOTSTRAP INITIALIZATION COMPLETE
[vision_dt.bootstrap] Total: 4, Successful: 4, Failed: 0
```

### Watcher Status

```
[Vision DT LightWatcher] ★ Active - monitoring for new lights
[Vision DT ColorSync] ★ Active - monitoring temperature changes
[Vision DT LEDSync] ★ Active - monitoring LED attribute changes
```

---

## Troubleshooting

### Bootstrap Not Running

**Symptoms**: No console messages on stage open

**Check**:
1. Console visible? (Window > Console)
2. Extension loaded? (Window > Extensions, search "USD Composer Setup")
3. Bootstrap directory exists at correct path?

**Solution**: Restart Omniverse, check for import errors in console

### Attributes Not Appearing on Lights

**Symptoms**: Light missing Vision DT attributes

**Cause**: Light created AFTER bootstrap ran

**Solution**:
- Close and reopen stage (triggers bootstrap)
- Or use LightWatcher (adds attributes automatically to new lights)

### Code Changes Not Taking Effect

**Symptoms**: Edited capability but behavior unchanged

**Cause**: Omniverse loads from `_build/bootstrap/`, not `bootstrap/`

**Solution**:
1. Edit files in `_build/bootstrap/` directly, OR
2. Copy updated files: `Copy-Item bootstrap/* _build/bootstrap/ -Recurse`
3. Restart Omniverse

### Math Domain Errors

**Symptoms**: `ValueError: math domain error` in console

**Cause**: Invalid input to `math.log()` (zero or negative value)

**Solution**: Ensure Kelvin values are positive (>0), use input validation

---

## Build Directory Policy

> **IMPORTANT**: Omniverse loads from `_build/bootstrap/`, NOT `bootstrap/`

| Action | Target |
|--------|--------|
| Edit capabilities | `_build/bootstrap/capabilities/` |
| Edit utilities | `_build/bootstrap/utils/` |
| Edit loader | `_build/bootstrap/loader.py` |

After editing in `_build/`, optionally sync back to `bootstrap/` for version control.

---

## Performance

| Stage Type | Bootstrap Time |
|------------|----------------|
| Empty stage | ~50-100ms |
| Stage with lights | ~100-200ms |
| Complex stage | ~200-500ms |

Bootstrap runs asynchronously and does not block the UI.

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| `LIGHTING_AND_OPTICS.md` | SPD, luminosity, multi-spectrum Kelvin systems |
| `HARDWARE_SPECS.md` | Camera, lens, and light specifications |
| `logs/changes.log` | Incremental change history |

---

*Document Version: 1.0*
*Last Updated: December 2025*



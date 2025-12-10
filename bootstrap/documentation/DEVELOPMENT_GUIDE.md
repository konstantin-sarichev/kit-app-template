# Vision DT Development Guide

## Overview

This guide documents proven patterns and common pitfalls for developing features in the Vision DT Omniverse environment. It is based on lessons learned during the implementation of the lighting and bootstrap systems.

---

## Common Pitfalls & Solutions

### PITFALL 1: Custom Attributes Not Visible in Omniverse UI

**Wrong:**
```python
attr = prim.CreateAttribute("inputs:visiondt:myAttr", Sdf.ValueTypeNames.Float, custom=False)
attr.SetDisplayName("My Attribute")  # This method doesn't exist!
```

**Correct:**
```python
attr = prim.CreateAttribute("visiondt:myAttr", Sdf.ValueTypeNames.Float, custom=True)
attr.SetCustomDataByKey("displayName", "My Attribute")
attr.SetCustomDataByKey("displayGroup", "Vision DT")
```

**Key Rules:**
- Use `custom=True` for custom attributes (not `custom=False`)
- Do NOT use `inputs:` prefix (reserved for shader inputs)
- Use `SetCustomDataByKey()` NOT `SetDisplayName()` or `SetMetadata("customData", ...)`
- Custom attributes appear in "Raw USD Properties" section

---

### PITFALL 2: Code Changes Not Taking Effect

**Problem:** Edited `bootstrap/capabilities/my_feature.py` but changes don't appear

**Solution:** Omniverse loads from `_build/`, not source:

```powershell
# Copy single file:
Copy-Item "bootstrap/capabilities/my_feature.py" "_build/bootstrap/capabilities/" -Force

# Copy all capabilities:
Copy-Item "bootstrap/capabilities/*.py" "_build/bootstrap/capabilities/" -Force

# Copy all utils:
Copy-Item "bootstrap/utils/*.py" "_build/bootstrap/utils/" -Force
```

**Always remember:** After editing source files, copy to `_build/` before testing!

---

### PITFALL 3: Module Import Errors

**Problem:** `No module named loader` or similar import errors

**Solution:** Use robust path discovery:

```python
import sys
from pathlib import Path

# Add bootstrap to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

# Now imports work
from utils.helpers import get_current_stage
```

---

### PITFALL 4: Math Domain Errors

**Problem:** `ValueError: math domain error` when using `math.log()`

**Solution:** Always validate numeric inputs:

```python
def safe_calculation(value, default=6500.0):
    # Handle None, zero, or negative values
    if value is None or value <= 0:
        value = default
    # Clamp to valid range
    value = max(1000.0, min(value, 40000.0))
    return value
```

---

### PITFALL 5: Changes Don't Update in Real-Time

**Problem:** Bootstrap runs once, attribute changes afterward have no effect

**Solution:** Use USD Notice system for real-time updates:

```python
from pxr import Tf, Usd

class AttributeWatcher:
    def start(self, stage):
        self._listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged,
            self._on_objects_changed,
            stage
        )

    def _on_objects_changed(self, notice, stage):
        for path in notice.GetChangedInfoOnlyPaths():
            # Handle attribute changes
            pass
        for path in notice.GetResyncedPaths():
            # Handle new/deleted prims
            pass
```

---

### PITFALL 6: Omniverse Overrides Custom Settings

**Problem:** Built-in Omniverse features override your custom values

**Solution:** Explicitly disable conflicting features:

```python
# Example: Disable Omniverse color temperature to use custom color
ct_attr = prim.GetAttribute("inputs:enableColorTemperature")
if ct_attr and ct_attr.IsValid():
    ct_attr.Set(False)  # Force disable
```

---

### PITFALL 7: Logs Not Appearing in Omniverse Console

**Problem:** Python `logging` module output not visible in Omniverse

**Solution:** Use BOTH Python logging AND carb logging:

```python
import logging
import carb

logger = logging.getLogger("vision_dt.my_feature")

def _log_info(message):
    logger.info(message)
    carb.log_info(f"[Vision DT] {message}")

def _log_error(message):
    logger.error(message)
    carb.log_error(f"[Vision DT] {message}")
```

---

## Feature Development Workflow

```
1. PLAN
   ├─ Define feature purpose and scope
   ├─ Identify affected prims/attributes
   ├─ Check for conflicts with existing features
   └─ Determine if real-time updates needed

2. CREATE
   ├─ Create file in _build/bootstrap/capabilities/ or utils/
   ├─ Add CAPABILITY_NAME and CAPABILITY_DESCRIPTION
   ├─ Use custom=True for custom attributes
   ├─ Use SetCustomDataByKey() for display metadata
   └─ Add dual logging (logging + carb)

3. TEST
   ├─ Restart Omniverse
   ├─ Check console for errors
   └─ Verify attributes in Raw USD Properties

4. ADD WATCHERS (if real-time updates needed)
   ├─ Create watcher class using Tf.Notice.Register
   ├─ Handle ObjectsChanged for attribute changes
   ├─ Handle ResyncedPaths for new prims
   └─ Start watcher from loader.py after bootstrap

5. HANDLE CONFLICTS
   ├─ Identify Omniverse features that may override
   ├─ Explicitly disable conflicting features
   └─ Log when overrides are applied

6. DOCUMENT
   ├─ Update logs/changes.log
   └─ Update relevant architecture doc if significant change
```

---

## Capability Module Template

```python
"""
Capability: [Feature Name]

[Description of what this capability does]

Priority: NN (runs after XX, before YY)
"""

import logging
import carb
from pxr import Usd, Sdf
import sys
from pathlib import Path

# Add bootstrap to path
bootstrap_dir = Path(__file__).parent.parent
if str(bootstrap_dir) not in sys.path:
    sys.path.insert(0, str(bootstrap_dir))

from utils.helpers import get_current_stage, find_prims_by_type

# Required capability attributes
CAPABILITY_NAME = "Feature Name"
CAPABILITY_DESCRIPTION = "Description of what this does"

logger = logging.getLogger("vision_dt.capability.feature_name")

def _log_info(msg):
    logger.info(msg)
    carb.log_info(f"[Vision DT {CAPABILITY_NAME}] {msg}")

def configure_prim(prim: Usd.Prim) -> bool:
    """Configure a single prim with custom attributes."""
    try:
        # Create custom attribute (use custom=True!)
        if not prim.HasAttribute("visiondt:myAttribute"):
            attr = prim.CreateAttribute(
                "visiondt:myAttribute",
                Sdf.ValueTypeNames.Float,
                custom=True  # IMPORTANT: Must be True
            )
            if attr:
                attr.Set(1.0)  # Default value
                attr.SetCustomDataByKey("displayName", "My Attribute")
                attr.SetCustomDataByKey("displayGroup", "Vision DT")

        _log_info(f"Configured {prim.GetPath()}")
        return True

    except Exception as e:
        _log_info(f"Error configuring {prim.GetPath()}: {e}")
        return False

def run(stage: Usd.Stage = None) -> tuple:
    """
    Main entry point - called by bootstrap loader.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        if stage is None:
            stage = get_current_stage()

        if not stage:
            return True, "No stage (skipped)"

        # Find prims to configure
        prims = find_prims_by_type(stage, "YourPrimType")

        if not prims:
            return True, "No prims found (skipped)"

        count = 0
        for prim in prims:
            if configure_prim(prim):
                count += 1

        msg = f"Configured {count} prim(s)"
        _log_info(msg)
        return True, msg

    except Exception as e:
        _log_info(f"Error: {e}")
        return False, str(e)
```

---

## Quick Reference: USD Attribute Types

```python
from pxr import Sdf

# Common attribute types
Sdf.ValueTypeNames.Float      # Single float
Sdf.ValueTypeNames.Double     # Double precision
Sdf.ValueTypeNames.Int        # Integer
Sdf.ValueTypeNames.Bool       # Boolean
Sdf.ValueTypeNames.String     # String
Sdf.ValueTypeNames.Asset      # File path/asset reference
Sdf.ValueTypeNames.Float3     # 3D vector (x, y, z)
Sdf.ValueTypeNames.Color3f    # RGB color
Sdf.ValueTypeNames.Matrix4d   # 4x4 transform matrix
Sdf.ValueTypeNames.FloatArray # Array of floats
```

---

## Quick Reference: Finding Prims

```python
# Find by type
for prim in stage.Traverse():
    if prim.GetTypeName() == "SphereLight":
        # Process light
        pass

# Find by pattern
for prim in stage.Traverse():
    if "Camera" in prim.GetName():
        # Process camera
        pass

# Common light types
LIGHT_TYPES = ["DomeLight", "RectLight", "DiskLight",
               "SphereLight", "DistantLight", "CylinderLight"]

# Common prim types
# Camera, Mesh, Xform, Scope, Material, Shader
```

---

## Quick Reference: Reading/Writing Attributes

```python
# Read attribute
attr = prim.GetAttribute("visiondt:temperature")
value = attr.Get() if attr else None

# Write attribute
if attr and attr.IsValid():
    attr.Set(6500.0)

# Create attribute if missing
if not prim.HasAttribute("visiondt:temperature"):
    attr = prim.CreateAttribute(
        "visiondt:temperature",
        Sdf.ValueTypeNames.Float,
        custom=True
    )
    attr.Set(6500.0)
```

---

*Document Version: 1.0*
*Last Updated: December 2025*



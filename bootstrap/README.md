# Vision Digital Twin Bootstrap System

## Overview

The Bootstrap System is a modular initialization framework for the Industrial Dynamics Vision Digital Twin environment. It automatically discovers and executes capability modules when an Omniverse stage is opened, ensuring consistent configuration, proper units, and physical accuracy across all projects.

## Architecture

### Components

1. **Loader (`loader.py`)**: Core orchestration system that discovers, loads, and executes capabilities
2. **Capabilities (`capabilities/`)**: Individual modules that perform specific initialization tasks
3. **Utilities (`utils/`)**: Shared helper functions for stage manipulation and metadata management

### Execution Flow

```
Stage Opens
    ↓
Bootstrap Loader Activates
    ↓
Discover Capability Modules (sorted by filename)
    ↓
Load Each Module
    ↓
Execute module.run()
    ↓
Report Status (Success/Failure)
```

## Capabilities

Capabilities are executed in numeric order based on their filename prefix:

### 00_set_units_mm.py
- **Priority**: 00 (first)
- **Purpose**: Set stage units to millimeters (metersPerUnit = 0.001)
- **Actions**:
  - Configures stage metersPerUnit metadata
  - Sets up axis to Z
  - Ensures consistent measurement system

### 10_enable_extensions.py
- **Priority**: 10
- **Purpose**: Enable required Omniverse Kit extensions
- **Actions**:
  - Checks for required extensions
  - Enables missing extensions
  - Reports availability status

### 20_configure_telecentric_cameras.py
- **Priority**: 20
- **Purpose**: Configure telecentric camera optical parameters
- **Actions**:
  - Finds all Camera prims
  - Adds custom attributes: magnification, working distance, FOV dimensions
  - Sets telecentric flag
  - Adds Vision DT metadata

### 30_normalize_transforms.py
- **Priority**: 30
- **Purpose**: Normalize all prim transforms
- **Actions**:
  - Removes non-uniform scaling
  - Ensures identity scale (1,1,1)
  - Adds standard xform ops (Translate, Rotate, Scale)
  - Maintains physical accuracy

### 40_add_custom_attributes.py
- **Priority**: 40
- **Purpose**: Add Vision DT custom attributes
- **Actions**:
  - Adds brightness controls to lights
  - Adds power rating metadata
  - Adds working distance attributes
  - Sets stage-level Vision DT metadata

### 50_check_asset_consistency.py
- **Priority**: 50 (last)
- **Purpose**: Validate asset naming and structure
- **Actions**:
  - Checks naming conventions
  - Validates metadata presence
  - Reports consistency issues
  - Provides warnings for non-compliant assets

## Creating New Capabilities

To create a new capability:

1. Create a Python file in `bootstrap/capabilities/` with a numeric prefix (e.g., `60_my_capability.py`)
2. Define required module attributes:
   ```python
   CAPABILITY_NAME = "My Capability Name"
   CAPABILITY_DESCRIPTION = "What this capability does"
   ```
3. Implement the `run()` function:
   ```python
   def run(stage: Usd.Stage = None) -> tuple:
       """
       Execute the capability.
       
       Returns:
           Tuple of (success: bool, message: str)
       """
       # Your implementation here
       return True, "Success message"
   ```
4. Use utility functions from `utils.helpers` for common operations
5. Log actions using the logging module

### Example Capability

```python
"""
Capability: Example Custom Setup

This capability demonstrates how to create a new bootstrap capability.
Priority: 60 (runs after consistency checks)
"""

import logging
from pxr import Usd

CAPABILITY_NAME = "Example Custom Setup"
CAPABILITY_DESCRIPTION = "Demonstrates custom capability creation"

logger = logging.getLogger("vision_dt.capability.example")

def run(stage: Usd.Stage = None) -> tuple:
    try:
        # Get stage if not provided
        if stage is None:
            import omni.usd
            context = omni.usd.get_context()
            stage = context.get_stage() if context else None
        
        if stage is None:
            return True, "No stage available (skipped)"
        
        # Your capability logic here
        logger.info("Running example capability")
        
        return True, "Example capability completed"
        
    except Exception as e:
        logger.error(f"Exception in example capability: {e}")
        return False, f"Exception: {str(e)}"
```

## Utility Functions

The `utils.helpers` module provides common functions:

### Stage Operations
- `get_current_stage()`: Get the active USD stage
- `set_stage_metadata(stage, key, value)`: Set stage-level metadata
- `get_stage_metadata(stage, key, default)`: Get stage-level metadata

### Prim Operations
- `find_prims_by_type(stage, prim_type)`: Find prims by type name
- `find_prims_by_pattern(stage, name_pattern)`: Find prims by name pattern
- `normalize_prim_transform(prim)`: Remove non-identity scale
- `ensure_xform_ops(prim, op_order)`: Add standard transform ops

### Attribute Management
- `has_custom_attribute(prim, attr_name)`: Check for attribute existence
- `create_custom_attribute(prim, attr_name, attr_type, default_value)`: Create custom attribute
- `get_prim_metadata(prim, key, default)`: Get prim metadata
- `set_prim_metadata(prim, key, value)`: Set prim metadata

### Logging
- `log_capability_action(capability_name, action, details)`: Log capability actions

## Integration

The bootstrap system is integrated with the `my_company.my_usd_composer_setup_extension` extension:

1. Bootstrap loader is initialized on extension startup
2. Stage event subscription monitors for stage open events
3. When a stage opens, all capabilities run asynchronously
4. Status messages are logged and displayed to the user

## Configuration

No configuration files are needed. The system automatically:
- Discovers capability modules by scanning the `capabilities/` directory
- Executes modules in filename order
- Reports success/failure status for each capability

## Debugging

To debug capabilities:

1. Check the Omniverse console for detailed logs
2. Look for messages from `vision_dt.bootstrap` logger
3. Each capability logs its actions with its own logger (e.g., `vision_dt.capability.set_units_mm`)
4. Failed capabilities report specific error messages

## Best Practices

1. **Keep capabilities focused**: Each capability should do one thing well
2. **Use appropriate prefixes**: Number your capabilities to control execution order
3. **Handle missing stages gracefully**: Check if stage is available before operating
4. **Log actions**: Use logging to document what the capability is doing
5. **Return meaningful messages**: Provide clear success/failure messages
6. **Use utility functions**: Leverage `utils.helpers` for common operations
7. **Test thoroughly**: Ensure capabilities work with empty stages and complex scenes

## Physical Accuracy Requirements

All capabilities must maintain the Vision Digital Twin's core principles:

1. **Millimeter Units**: All measurements in mm (metersPerUnit = 0.001)
2. **No Scaling**: Geometry at 1:1 real-world scale
3. **Metadata Traceability**: Add `vision_dt:` prefixed metadata for tracking
4. **Consistent Transforms**: Standard TRS (Translate, Rotate, Scale) order
5. **Real-World Parameters**: Optical and lighting values match hardware specs

## Troubleshooting

### Capability Not Running
- Check filename has numeric prefix and `.py` extension
- Ensure file is in `bootstrap/capabilities/` directory
- Verify module has required `CAPABILITY_NAME`, `CAPABILITY_DESCRIPTION`, and `run()` function

### Import Errors
- Check that `bootstrap/` directory is added to Python path
- Verify all required Omniverse modules are available
- Use try/except for optional imports

### Stage Not Available
- Some capabilities may run before stage is fully loaded
- Return success with "skipped" message if stage is None
- Stage will be available after first async delay

## Version History

- **1.0.0** (2025-11-12): Initial implementation with 6 core capabilities

## Support

For issues or questions about the bootstrap system:
1. Check the `logs/changes.log` for implementation history
2. Review capability source code for detailed behavior
3. Consult `systemprompt.md` for project requirements





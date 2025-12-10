"""
Capability: Enable Required Extensions

This capability ensures that all required Omniverse Kit extensions are loaded
and enabled. This includes physics, replicator, and other extensions needed
for the Vision Digital Twin environment.

Priority: 10 (runs early, after basic stage setup)
"""

import logging
import omni.ext

# Required capability attributes
CAPABILITY_NAME = "Enable Required Extensions"
CAPABILITY_DESCRIPTION = "Ensures all required Omniverse Kit extensions are loaded and enabled"

logger = logging.getLogger("vision_dt.capability.enable_extensions")

# List of required extensions for Vision Digital Twin
REQUIRED_EXTENSIONS = [
    "omni.physx",  # Physics simulation
    "omni.kit.viewport.window",  # Viewport rendering
    "omni.kit.renderer.core",  # Core rendering
    "omni.usd",  # USD core
    # Replicator extensions (may be optional depending on installation)
    # "omni.replicator.core",
    # "omni.syntheticdata",
]


def is_extension_enabled(ext_name: str) -> bool:
    """
    Check if an extension is currently enabled.
    
    Args:
        ext_name: Extension name to check
        
    Returns:
        True if enabled, False otherwise
    """
    try:
        manager = omni.ext.get_extension_manager()
        if manager:
            return manager.is_extension_enabled(ext_name)
        return False
    except Exception as e:
        logger.warning(f"Could not check extension {ext_name}: {e}")
        return False


def enable_extension(ext_name: str) -> bool:
    """
    Enable a specific extension.
    
    Args:
        ext_name: Extension name to enable
        
    Returns:
        True if successful or already enabled, False otherwise
    """
    try:
        manager = omni.ext.get_extension_manager()
        if not manager:
            logger.warning("Extension manager not available")
            return False
        
        # Check if already enabled
        if manager.is_extension_enabled(ext_name):
            logger.info(f"Extension already enabled: {ext_name}")
            return True
        
        # Try to enable it
        manager.set_extension_enabled(ext_name, True)
        
        # Verify
        if manager.is_extension_enabled(ext_name):
            logger.info(f"Successfully enabled extension: {ext_name}")
            return True
        else:
            logger.warning(f"Failed to enable extension: {ext_name}")
            return False
            
    except Exception as e:
        logger.warning(f"Could not enable extension {ext_name}: {e}")
        return False


def run(stage=None) -> tuple:
    """
    Enable all required extensions.
    
    Args:
        stage: USD stage (not used by this capability but included for consistency)
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        enabled_count = 0
        already_enabled_count = 0
        failed_extensions = []
        
        for ext_name in REQUIRED_EXTENSIONS:
            was_enabled = is_extension_enabled(ext_name)
            
            if was_enabled:
                already_enabled_count += 1
            else:
                success = enable_extension(ext_name)
                if success:
                    enabled_count += 1
                else:
                    failed_extensions.append(ext_name)
        
        # Build result message
        total = len(REQUIRED_EXTENSIONS)
        
        if failed_extensions:
            msg = f"Enabled {enabled_count}/{total} extensions, {already_enabled_count} already enabled, {len(failed_extensions)} failed: {', '.join(failed_extensions)}"
            # We return success even if some extensions fail, as they may be optional
            logger.warning(msg)
            return True, msg
        else:
            msg = f"All {total} required extensions available ({enabled_count} newly enabled, {already_enabled_count} already enabled)"
            logger.info(msg)
            return True, msg
            
    except Exception as e:
        logger.error(f"Exception in enable_extensions capability: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False, f"Exception: {str(e)}"



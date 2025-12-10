"""
Enhanced Prim Watcher for Bootstrap

This optional enhancement adds real-time prim creation watching to automatically
apply bootstrap capabilities to newly created prims (like lights) without needing
to close and reopen the stage.

To integrate this into your extension:
1. Copy the PrimCreationWatcher class
2. Add it to your extension's on_startup()
3. Initialize it after bootstrap initialization
4. Clean up in on_shutdown()
"""

import asyncio
import logging
from typing import List, Set
from pathlib import Path
import carb
import omni.usd
import omni.kit.app
from pxr import Usd, Tf


class PrimCreationWatcher:
    """
    Watches for prim creation events and automatically applies bootstrap
    capabilities to newly created lights.
    """
    
    def __init__(self, bootstrap_loader):
        """
        Initialize the prim creation watcher.
        
        Args:
            bootstrap_loader: BootstrapLoader instance to use for configuration
        """
        self._bootstrap_loader = bootstrap_loader
        self._stage_listener = None
        self._known_light_paths: Set[str] = set()
        self._processing = False
        
        # Light types we want to watch for
        self._watched_light_types = [
            "DomeLight", "RectLight", "DiskLight", 
            "SphereLight", "DistantLight", "CylinderLight"
        ]
        
        logging.info("PrimCreationWatcher initialized")
        
        # Subscribe to stage events
        self._initialize_watcher()
    
    def _initialize_watcher(self):
        """Set up USD stage listener for prim changes."""
        try:
            # Subscribe to stage events to set up listeners when stage changes
            usd_context = omni.usd.get_context()
            if usd_context:
                events = usd_context.get_stage_event_stream()
                self._stage_event_subscription = events.create_subscription_to_pop(
                    self._on_stage_event,
                    name="Prim Creation Watcher"
                )
                
                # If there's already a stage, set up listener now
                stage = usd_context.get_stage()
                if stage:
                    self._setup_stage_listener(stage)
                    
        except Exception as e:
            logging.error(f"Failed to initialize prim watcher: {e}")
    
    def _on_stage_event(self, event):
        """Handle stage events to update listener."""
        try:
            event_type = event.type
            
            if event_type == int(omni.usd.StageEventType.OPENED):
                # New stage opened, set up listener
                usd_context = omni.usd.get_context()
                stage = usd_context.get_stage() if usd_context else None
                if stage:
                    self._setup_stage_listener(stage)
                    # Index existing lights
                    self._index_existing_lights(stage)
                    
            elif event_type == int(omni.usd.StageEventType.CLOSED):
                # Stage closed, clean up
                self._cleanup_stage_listener()
                self._known_light_paths.clear()
                
        except Exception as e:
            logging.error(f"Error in stage event handler: {e}")
    
    def _setup_stage_listener(self, stage: Usd.Stage):
        """Set up USD notice listener for the stage."""
        try:
            if self._stage_listener:
                self._cleanup_stage_listener()
            
            # Create listener for stage changes
            self._stage_listener = Tf.Notice.Register(
                Usd.Notice.ObjectsChanged,
                self._on_objects_changed,
                stage
            )
            
            logging.info("Stage listener set up for prim creation watching")
            
        except Exception as e:
            logging.error(f"Failed to set up stage listener: {e}")
    
    def _cleanup_stage_listener(self):
        """Remove the stage listener."""
        if self._stage_listener:
            self._stage_listener.Revoke()
            self._stage_listener = None
    
    def _index_existing_lights(self, stage: Usd.Stage):
        """Build index of existing lights in the stage."""
        self._known_light_paths.clear()
        
        for prim in stage.Traverse():
            if prim.GetTypeName() in self._watched_light_types:
                self._known_light_paths.add(str(prim.GetPath()))
        
        logging.info(f"Indexed {len(self._known_light_paths)} existing lights")
    
    def _on_objects_changed(self, notice, stage):
        """Handle USD objects changed notification."""
        if self._processing:
            return  # Avoid recursion
            
        try:
            # Check for new prims
            new_lights = []
            
            for path in notice.GetResyncedPaths():
                prim = stage.GetPrimAtPath(path)
                if prim and prim.IsValid():
                    prim_type = prim.GetTypeName()
                    prim_path = str(prim.GetPath())
                    
                    # Check if it's a light we haven't seen before
                    if (prim_type in self._watched_light_types and 
                        prim_path not in self._known_light_paths):
                        new_lights.append(prim)
                        self._known_light_paths.add(prim_path)
            
            # If we found new lights, configure them
            if new_lights:
                logging.info(f"Detected {len(new_lights)} new light(s), applying bootstrap...")
                asyncio.ensure_future(self._configure_new_lights(new_lights))
                
        except Exception as e:
            logging.error(f"Error handling objects changed: {e}")
    
    async def _configure_new_lights(self, lights: List[Usd.Prim]):
        """Apply bootstrap capabilities to newly created lights."""
        self._processing = True
        
        try:
            # Wait a frame to let the prim fully initialize
            await omni.kit.app.get_app().next_update_async()
            
            # Import the capability module to configure lights
            import sys
            bootstrap_path = Path(self._bootstrap_loader.capabilities_dir).parent
            if str(bootstrap_path) not in sys.path:
                sys.path.insert(0, str(bootstrap_path))
            
            # Find and load the multi-spectrum capability
            capabilities_dir = Path(self._bootstrap_loader.capabilities_dir)
            capability_file = capabilities_dir / "40_add_custom_attributes.py"
            
            if capability_file.exists():
                # Import the module
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    "multispectrum_capability", 
                    capability_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Configure each light
                for light in lights:
                    try:
                        success = module.configure_light_prim(light)
                        if success:
                            carb.log_info(f"✓ Auto-configured light: {light.GetPath()}")
                        else:
                            carb.log_warn(f"⚠ Failed to configure light: {light.GetPath()}")
                    except Exception as e:
                        logging.error(f"Error configuring light {light.GetPath()}: {e}")
                
                carb.log_info(f"Vision DT: Auto-configured {len(lights)} new light(s)")
            else:
                logging.warning("Multi-spectrum capability not found")
                
        except Exception as e:
            logging.error(f"Error in auto-configuration: {e}")
            import traceback
            logging.error(traceback.format_exc())
        finally:
            self._processing = False
    
    def shutdown(self):
        """Clean up the watcher."""
        self._cleanup_stage_listener()
        if hasattr(self, '_stage_event_subscription') and self._stage_event_subscription:
            self._stage_event_subscription.unsubscribe()
            self._stage_event_subscription = None
        self._known_light_paths.clear()
        logging.info("PrimCreationWatcher shut down")


# ============================================================================
# Integration Instructions
# ============================================================================

"""
To integrate this into your extension.py:

1. Import at the top of the file:
    from pathlib import Path
    # ... after bootstrap import ...
    try:
        from enhanced_prim_watcher import PrimCreationWatcher
        PRIM_WATCHER_AVAILABLE = True
    except ImportError:
        PRIM_WATCHER_AVAILABLE = False

2. Add instance variable in __init__ or on_startup:
    self._prim_watcher = None

3. Initialize after bootstrap in on_startup (after line 209):
    # Initialize Vision DT Bootstrap System
    if BOOTSTRAP_AVAILABLE:
        self._initialize_bootstrap()
        
        # NEW: Initialize prim creation watcher
        if PRIM_WATCHER_AVAILABLE and self._bootstrap_loader:
            self._prim_watcher = PrimCreationWatcher(self._bootstrap_loader)
            logging.info("Prim creation watcher enabled - lights will be auto-configured")

4. Clean up in on_shutdown (around line 550):
    # Clean up bootstrap subscriptions
    if self._stage_event_subscription:
        self._stage_event_subscription.unsubscribe()
        self._stage_event_subscription = None
    
    # NEW: Clean up prim watcher
    if self._prim_watcher:
        self._prim_watcher.shutdown()
        self._prim_watcher = None
    
    self._bootstrap_loader = None
"""


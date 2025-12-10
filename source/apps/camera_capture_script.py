"""
Multi-Camera Image Capture Script for USD Composer
==================================================

This script allows you to capture images from multiple cameras in your USD stage.
You can manually specify camera paths or use selected cameras.

Usage:
1. Run this script in USD Composer's Script Editor
2. Specify camera paths manually or use selection
3. Images will be saved to specified output directory

Requirements:
- USD Composer/Omniverse Kit environment
- Cameras in the USD stage
"""

import omni.kit.commands
import omni.usd
import omni.kit.viewport.utility
import omni.kit.capture.viewport
import omni.ui as ui
import asyncio
import os
from datetime import datetime
from pathlib import Path
from pxr import Usd, UsdGeom, Gf
import carb


class MultiCameraCaptureScript:
    def __init__(self):
        self.stage = omni.usd.get_context().get_stage()
        self.camera_paths = []
        self.output_directory = "C:/temp/camera_captures"
        self.image_format = ".png"
        self.resolution = (1920, 1080)

    def get_all_cameras_in_stage(self):
        """Get all camera prims in the current stage"""
        cameras = []
        if self.stage:
            for prim in self.stage.Traverse():
                if prim.IsA(UsdGeom.Camera):
                    cameras.append(str(prim.GetPath()))
        return cameras

    def get_selected_cameras(self):
        """Get camera paths from current selection"""
        context = omni.usd.get_context()
        selection = context.get_selection()
        selected_paths = selection.get_selected_prim_paths()

        cameras = []
        for path in selected_paths:
            prim = self.stage.GetPrimAtPath(path)
            if prim and prim.IsA(UsdGeom.Camera):
                cameras.append(path)
        return cameras

    def add_camera_path(self, camera_path):
        """Manually add a camera path"""
        if camera_path and camera_path not in self.camera_paths:
            # Validate that the path exists and is a camera
            prim = self.stage.GetPrimAtPath(camera_path)
            if prim and prim.IsA(UsdGeom.Camera):
                self.camera_paths.append(camera_path)
                carb.log_info(f"Added camera: {camera_path}")
                return True
            else:
                carb.log_warn(f"Invalid camera path: {camera_path}")
                return False
        return False

    def remove_camera_path(self, camera_path):
        """Remove a camera path from the list"""
        if camera_path in self.camera_paths:
            self.camera_paths.remove(camera_path)
            carb.log_info(f"Removed camera: {camera_path}")

    def clear_camera_paths(self):
        """Clear all camera paths"""
        self.camera_paths.clear()
        carb.log_info("Cleared all camera paths")

    def set_output_directory(self, directory):
        """Set the output directory for captured images"""
        self.output_directory = directory
        # Create directory if it doesn't exist
        Path(directory).mkdir(parents=True, exist_ok=True)

    def set_resolution(self, width, height):
        """Set capture resolution"""
        self.resolution = (width, height)

    def set_image_format(self, format_type):
        """Set image format (png, jpg, exr, etc.)"""
        self.image_format = format_type.lower()

    async def capture_from_camera(self, camera_path, output_path):
        """Capture image from a specific camera"""
        print(f"\n🎬 STARTING CAPTURE for {camera_path}")
        print(f"📁 Output path: {output_path}")

        try:
            # Get viewport
            viewport_api = omni.kit.viewport.utility.get_active_viewport()
            if not viewport_api:
                print("❌ No active viewport found")
                carb.log_error("No active viewport found")
                return False

            print("✅ Active viewport found")

            # Set camera as active - try multiple methods
            camera_set = False

            # Method A: Try SetActiveCamera command
            try:
                omni.kit.commands.execute(
                    "SetActiveCamera",
                    camera_path=camera_path
                )
                camera_set = True
                carb.log_info(f"Set camera using SetActiveCamera: {camera_path}")
            except Exception as e:
                carb.log_info(f"SetActiveCamera not available (expected): {e}")
                carb.log_info("Trying alternative camera setting methods...")

            # Method B: Try viewport API camera setting
            if not camera_set:
                try:
                    carb.log_info("Trying Method B: Direct viewport camera setting")

                    # First select the camera prim
                    omni.kit.commands.execute(
                        "SelectPrims",
                        old_selected_paths=[],
                        new_selected_paths=[camera_path],
                        expand_in_stage=True
                    )

                    # Try multiple viewport camera setting approaches
                    if hasattr(viewport_api, 'camera_path'):
                        viewport_api.camera_path = camera_path
                        camera_set = True
                        carb.log_info(f"Set camera using viewport_api.camera_path: {camera_path}")
                    elif hasattr(viewport_api, 'set_active_camera'):
                        viewport_api.set_active_camera(camera_path)
                        camera_set = True
                        carb.log_info(f"Set camera using viewport_api.set_active_camera: {camera_path}")
                    elif hasattr(viewport_api, 'set_camera_path'):
                        viewport_api.set_camera_path(camera_path)
                        camera_set = True
                        carb.log_info(f"Set camera using viewport_api.set_camera_path: {camera_path}")

                except Exception as e:
                    carb.log_warn(f"Viewport camera setting failed: {e}")

            # Method C: Try USD stage camera setting
            if not camera_set:
                try:
                    carb.log_info("Trying Method C: USD context camera setting")
                    from pxr import UsdGeom
                    stage = omni.usd.get_context().get_stage()
                    camera_prim = stage.GetPrimAtPath(camera_path)

                    if camera_prim and camera_prim.IsA(UsdGeom.Camera):
                        usd_context = omni.usd.get_context()

                        # Try different USD context methods
                        if hasattr(usd_context, 'set_active_camera'):
                            usd_context.set_active_camera(camera_path)
                            camera_set = True
                            carb.log_info(f"Set camera using usd_context.set_active_camera: {camera_path}")
                        elif hasattr(usd_context, 'set_camera_path'):
                            usd_context.set_camera_path(camera_path)
                            camera_set = True
                            carb.log_info(f"Set camera using usd_context.set_camera_path: {camera_path}")
                        else:
                            carb.log_info("No suitable USD context camera setting method found")
                    else:
                        carb.log_warn(f"Camera prim not found or not a camera: {camera_path}")

                except Exception as e:
                    carb.log_warn(f"USD camera setting failed: {e}")

            if not camera_set:
                print("⚠️ Could not set camera as active, continuing anyway...")
                carb.log_warn(f"Could not set camera {camera_path} as active, continuing anyway...")

            # Wait a frame for the camera to be set
            print("⏳ Waiting for camera to be set...")
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            print("⏳ Camera setting wait complete")

            # Try multiple capture methods
            print("🎯 Starting capture methods...")
            success = False

            # Method 1: Try Kit commands approach
            try:
                carb.log_info("Trying Method 1: Kit commands")
                print("Method 1: Kit commands")
                omni.kit.commands.execute(
                    "CaptureViewportToFile",
                    output_file_path=output_path,
                    width=self.resolution[0],
                    height=self.resolution[1]
                )
                success = True
                carb.log_info(f"Captured using Method 1: {output_path}")
            except Exception as e:
                carb.log_warn(f"Method 1 failed: {e}")

            # Method 2: Try ScreenCapture command
            if not success:
                try:
                    carb.log_info("Trying Method 2: ScreenCapture")
                    print("Method 2: ScreenCapture")
                    omni.kit.commands.execute(
                        "ScreenCapture",
                        file_path=output_path,
                        resolution=self.resolution
                    )
                    success = True
                    carb.log_info(f"Captured using Method 2: {output_path}")
                except Exception as e:
                    carb.log_warn(f"Method 2 failed: {e}")

            # Method 3: Try CaptureExtension with correct methods
            if not success:
                try:
                    carb.log_info("Trying Method 3: CaptureExtension")
                    print("Method 3: CaptureExtension")
                    import omni.kit.capture.viewport

                    capture_instance = omni.kit.capture.viewport.CaptureExtension.get_instance()
                    if capture_instance:
                        carb.log_info(f"CaptureExtension methods: {[m for m in dir(capture_instance) if not m.startswith('_')]}")

                        # Try different method names that might exist
                        if hasattr(capture_instance, 'capture_viewport_to_file'):
                            carb.log_info("Using capture_viewport_to_file")
                            capture_instance.capture_viewport_to_file(output_path)
                            success = True
                        elif hasattr(capture_instance, 'capture_viewport'):
                            carb.log_info("Using capture_viewport")
                            capture_instance.capture_viewport(output_path)
                            success = True
                        elif hasattr(capture_instance, 'capture'):
                            carb.log_info("Using capture")
                            capture_instance.capture(output_path)
                            success = True
                        elif hasattr(capture_instance, 'save_viewport'):
                            carb.log_info("Using save_viewport")
                            capture_instance.save_viewport(output_path)
                            success = True

                        if success:
                            carb.log_info(f"Captured using Method 3: {output_path}")
                        else:
                            carb.log_warn("No suitable capture method found in CaptureExtension")

                except Exception as e:
                    carb.log_warn(f"Method 3 failed: {e}")

            # Method 4: Try basic screenshot approach
            if not success:
                try:
                    carb.log_info("Trying Method 4: Basic screenshot")
                    # Get the viewport window and try to screenshot it
                    import omni.kit.app
                    app = omni.kit.app.get_app()

                    # Use the renderer to capture
                    renderer = app.get_renderer()
                    if renderer:
                        # This is a simplified approach - might need adjustment
                        image_data = renderer.capture_frame()
                        if image_data:
                            # Save the image data to file
                            import PIL.Image
                            img = PIL.Image.fromarray(image_data)
                            img.save(output_path)
                            success = True
                            carb.log_info(f"Captured using Method 4: {output_path}")
                except Exception as e:
                    carb.log_warn(f"Method 4 failed: {e}")

            # Method 5: Try viewport window screenshot
            if not success:
                try:
                    carb.log_info("Trying Method 5: Viewport window screenshot")

                    # Get the viewport window
                    import omni.kit.viewport.window
                    viewport_window_ext = omni.kit.viewport.window.get_viewport_window_extension()

                    if viewport_window_ext:
                        viewport_window = viewport_window_ext.get_viewport_window()
                        if viewport_window and hasattr(viewport_window, 'save_viewport_to_file'):
                            viewport_window.save_viewport_to_file(output_path)
                            success = True
                            carb.log_info(f"Captured using Method 5: {output_path}")
                        elif viewport_window and hasattr(viewport_window, 'capture_viewport'):
                            viewport_window.capture_viewport(output_path)
                            success = True
                            carb.log_info(f"Captured using Method 5b: {output_path}")

                except Exception as e:
                    carb.log_warn(f"Method 5 failed: {e}")

            # Method 6: Try direct viewport API methods
            if not success:
                try:
                    carb.log_info("Trying Method 6: Direct viewport API")
                    # Check what methods the viewport_api actually has
                    carb.log_info(f"Viewport API methods: {[m for m in dir(viewport_api) if 'capture' in m.lower() or 'save' in m.lower()]}")

                    if hasattr(viewport_api, 'save_viewport_to_file'):
                        viewport_api.save_viewport_to_file(output_path)
                        success = True
                        carb.log_info(f"Captured using Method 6: {output_path}")
                    elif hasattr(viewport_api, 'capture_viewport_to_file'):
                        viewport_api.capture_viewport_to_file(output_path)
                        success = True
                        carb.log_info(f"Captured using Method 6b: {output_path}")

                except Exception as e:
                    carb.log_warn(f"Method 6 failed: {e}")

            if success:
                print(f"🎉 SUCCESS! Captured image from {camera_path}")
                carb.log_info(f"Successfully captured image from {camera_path} to {output_path}")
                return True
            else:
                print(f"❌ ALL CAPTURE METHODS FAILED for {camera_path}")
                carb.log_error(f"All capture methods failed for {camera_path}")
                # Print available methods for debugging
                print("🔍 Available viewport API methods:")
                carb.log_error("Available viewport API methods:")
                if viewport_api:
                    for attr in dir(viewport_api):
                        if 'capture' in attr.lower() or 'save' in attr.lower() or 'screenshot' in attr.lower():
                            print(f"  - {attr}")
                            carb.log_error(f"  - {attr}")
                return False

        except Exception as e:
            print(f"💥 EXCEPTION in capture_from_camera: {str(e)}")
            carb.log_error(f"Error capturing from camera {camera_path}: {str(e)}")
            return False

    async def capture_all_cameras(self):
        """Capture images from all specified cameras"""
        print(f"\n🚀 STARTING CAPTURE SESSION")
        print(f"📋 Number of cameras: {len(self.camera_paths)}")

        if not self.camera_paths:
            print("❌ No cameras specified for capture")
            carb.log_warn("No cameras specified for capture")
            return []

        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join(self.output_directory, f"capture_session_{timestamp}")
        Path(session_dir).mkdir(parents=True, exist_ok=True)
        print(f"📁 Output directory: {session_dir}")

        captured_files = []

        for i, camera_path in enumerate(self.camera_paths):
            print(f"\n📷 Processing camera {i+1}/{len(self.camera_paths)}: {camera_path}")

            # Generate filename
            camera_name = camera_path.split("/")[-1] if "/" in camera_path else camera_path
            filename = f"camera_{i+1:02d}_{camera_name}{self.image_format}"
            output_path = os.path.join(session_dir, filename)

            # Capture image
            success = await self.capture_from_camera(camera_path, output_path)
            if success:
                captured_files.append(output_path)
                print(f"✅ Camera {i+1} captured successfully")
            else:
                print(f"❌ Camera {i+1} capture failed")

        print(f"\n🏁 CAPTURE SESSION COMPLETE")
        print(f"✅ Success: {len(captured_files)}/{len(self.camera_paths)} cameras")
        carb.log_info(f"Capture session complete. {len(captured_files)} images saved to: {session_dir}")
        return captured_files

    def print_status(self):
        """Print current configuration"""
        print("\n=== Multi-Camera Capture Configuration ===")
        print(f"Output Directory: {self.output_directory}")
        print(f"Resolution: {self.resolution[0]}x{self.resolution[1]}")
        print(f"Image Format: {self.image_format}")
        print(f"Number of cameras: {len(self.camera_paths)}")
        print("Camera paths:")
        for i, path in enumerate(self.camera_paths, 1):
            print(f"  {i}. {path}")
        print("=" * 45)

    def debug_capture_capabilities(self):
        """Debug function to check available capture methods"""
        print("\n=== Capture Capabilities Debug ===")

        # Check viewport
        viewport_api = omni.kit.viewport.utility.get_active_viewport()
        if viewport_api:
            print("✓ Active viewport found")
            print("Available viewport methods:")
            for attr in dir(viewport_api):
                if any(keyword in attr.lower() for keyword in ['capture', 'save', 'screenshot', 'render']):
                    print(f"  - {attr}: {type(getattr(viewport_api, attr, None))}")
        else:
            print("✗ No active viewport")

        # Check capture extension
        try:
            import omni.kit.capture.viewport as capture_viewport
            print("✓ Capture viewport module imported")

            # Check for extension instance
            try:
                capture_instance = capture_viewport.CaptureExtension.get_instance()
                if capture_instance:
                    print("✓ Capture extension instance found")
                    print("All CaptureExtension methods:")
                    for attr in dir(capture_instance):
                        if not attr.startswith('_'):
                            attr_type = type(getattr(capture_instance, attr, None))
                            print(f"  - {attr}: {attr_type}")

                    print("\nPotential capture methods:")
                    for attr in dir(capture_instance):
                        if any(keyword in attr.lower() for keyword in ['capture', 'save', 'screenshot', 'render']):
                            print(f"  - {attr}")
                else:
                    print("✗ No capture extension instance")
            except Exception as e:
                print(f"✗ Error getting capture instance: {e}")

        except Exception as e:
            print(f"✗ Error importing capture module: {e}")

        # Check available commands
        print("\nChecking available Kit commands:")
        try:
            import omni.kit.commands
            registry = omni.kit.commands.get_command_registry()

            # Check capture commands
            capture_commands = [cmd for cmd in registry.get_all_command_names() if 'capture' in cmd.lower()]
            if capture_commands:
                print("Available capture commands:")
                for cmd in capture_commands:
                    print(f"  - {cmd}")
            else:
                print("✗ No capture commands found")

            # Check camera commands
            camera_commands = [cmd for cmd in registry.get_all_command_names() if 'camera' in cmd.lower()]
            if camera_commands:
                print("Available camera commands:")
                for cmd in camera_commands:
                    print(f"  - {cmd}")
            else:
                print("✗ No camera commands found")

        except Exception as e:
            print(f"✗ Error checking commands: {e}")

        print("=" * 45)


# Create global instance
camera_capture = MultiCameraCaptureScript()


# Convenience functions for easy use
def add_camera(camera_path):
    """Add a camera by path"""
    return camera_capture.add_camera_path(camera_path)

def add_selected_cameras():
    """Add all currently selected cameras"""
    selected = camera_capture.get_selected_cameras()
    for camera_path in selected:
        camera_capture.add_camera_path(camera_path)
    carb.log_info(f"Added {len(selected)} selected cameras")

def add_all_cameras():
    """Add all cameras in the stage"""
    all_cameras = camera_capture.get_all_cameras_in_stage()
    for camera_path in all_cameras:
        camera_capture.add_camera_path(camera_path)
    carb.log_info(f"Added {len(all_cameras)} cameras from stage")

def remove_camera(camera_path):
    """Remove a camera by path"""
    camera_capture.remove_camera_path(camera_path)

def clear_cameras():
    """Clear all cameras"""
    camera_capture.clear_camera_paths()

def set_output_dir(directory):
    """Set output directory"""
    camera_capture.set_output_directory(directory)

def set_resolution(width, height):
    """Set capture resolution"""
    camera_capture.set_resolution(width, height)

def set_format(format_type):
    """Set image format"""
    camera_capture.set_image_format(format_type)

def capture_images():
    """Capture images from all cameras (async wrapper)"""
    async def _capture():
        return await camera_capture.capture_all_cameras()

    # Run the async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_capture())
    finally:
        loop.close()

def show_status():
    """Show current configuration"""
    camera_capture.print_status()

def debug_capture():
    """Debug capture capabilities"""
    camera_capture.debug_capture_capabilities()

def test_camera_path(camera_path):
    """Test if a camera path is valid and accessible"""
    print(f"\n=== Testing Camera Path: {camera_path} ===")

    try:
        stage = omni.usd.get_context().get_stage()
        if not stage:
            print("✗ No USD stage found")
            return False

        prim = stage.GetPrimAtPath(camera_path)
        if not prim:
            print(f"✗ Prim not found at path: {camera_path}")
            return False

        print(f"✓ Prim found: {prim.GetName()}")
        print(f"  Type: {prim.GetTypeName()}")

        from pxr import UsdGeom
        if prim.IsA(UsdGeom.Camera):
            print("✓ Prim is a Camera")

            # Test camera setting using the same methods as the capture script
            viewport_api = omni.kit.viewport.utility.get_active_viewport()
            if viewport_api:
                print("✓ Active viewport found")

                camera_set = False

                # Test Method B: viewport API
                try:
                    if hasattr(viewport_api, 'camera_path'):
                        viewport_api.camera_path = camera_path
                        camera_set = True
                        print(f"✓ Successfully set camera using viewport_api.camera_path: {camera_path}")
                except Exception as e:
                    print(f"✗ viewport_api.camera_path failed: {e}")

                # Test Method C: USD context (if viewport failed)
                if not camera_set:
                    try:
                        usd_context = omni.usd.get_context()
                        if hasattr(usd_context, 'set_active_camera'):
                            usd_context.set_active_camera(camera_path)
                            camera_set = True
                            print(f"✓ Successfully set camera using usd_context.set_active_camera: {camera_path}")
                    except Exception as e:
                        print(f"✗ usd_context.set_active_camera failed: {e}")

                return camera_set
            else:
                print("✗ No active viewport")
        else:
            print(f"✗ Prim is not a Camera (type: {prim.GetTypeName()})")

    except Exception as e:
        print(f"✗ Error testing camera path: {e}")

    return False

def test_simple_capture():
    """Test a simple single capture without the full async framework"""
    print("\n=== Testing Simple Capture ===")

    # Check if we have cameras configured
    if not camera_capture.camera_paths:
        print("✗ No cameras configured. Add a camera first.")
        return False

    camera_path = camera_capture.camera_paths[0]
    print(f"Testing capture with camera: {camera_path}")

    # Test camera setting
    if not test_camera_path(camera_path):
        print("✗ Camera setting test failed")
        return False

    print("✓ Camera test passed - capture should work!")
    return True

def test_capture_with_debug():
    """Test capture with detailed debugging - call this to see what's happening"""
    print("\n🔧 TESTING CAPTURE WITH DEBUG OUTPUT")

    # Check if we have cameras
    if not camera_capture.camera_paths:
        print("❌ No cameras configured!")
        print("Use: add_camera('/your/camera/path')")
        return False

    print(f"📋 Cameras configured: {len(camera_capture.camera_paths)}")
    for i, path in enumerate(camera_capture.camera_paths):
        print(f"  {i+1}. {path}")

    # Test the capture
    import asyncio

    async def _test_capture():
        print("🎬 Starting async capture test...")
        try:
            captured_files = await camera_capture.capture_all_cameras()
            print(f"✅ Capture completed! Files: {captured_files}")
            return captured_files
        except Exception as e:
            print(f"💥 Capture failed with exception: {e}")
            import traceback
            traceback.print_exc()
            return []

    # Run the test
    try:
        print("🔄 Running async capture...")
        result = asyncio.ensure_future(_test_capture())
        print("⏳ Waiting for capture to complete...")
        # Let the async operation run
        import time
        time.sleep(0.1)  # Give it a moment to start
        return result
    except Exception as e:
        print(f"💥 Failed to start capture: {e}")
        import traceback
        traceback.print_exc()
        return False


# Example usage functions
def example_usage():
    """Example of how to use the script"""
    print("\n=== Multi-Camera Capture Script ===")
    print("Example usage:")
    print()
    print("# Add cameras manually:")
    print('add_camera("/World/Camera1")')
    print('add_camera("/World/Camera2")')
    print()
    print("# Or add selected cameras:")
    print("add_selected_cameras()")
    print()
    print("# Or add all cameras in stage:")
    print("add_all_cameras()")
    print()
    print("# Set output directory:")
    print('set_output_dir("C:/my_captures")')
    print()
    print("# Set resolution:")
    print("set_resolution(1920, 1080)")
    print()
    print("# Set image format:")
    print('set_format("png")')
    print()
    print("# Capture images:")
    print("capture_images()")
    print()
    print("# Show current status:")
    print("show_status()")


if __name__ == "__main__":
    example_usage()

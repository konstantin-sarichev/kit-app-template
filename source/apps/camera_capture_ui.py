"""
Simple UI for Multi-Camera Capture Script
=========================================

This creates a simple UI window for the camera capture functionality.
"""

import omni.ui as ui
import omni.kit.window.file_importer
import asyncio
import carb
import os
import sys

# Set the script directory to the exact project location
def get_script_directory():
    """Get the directory containing this script - hardcoded to project location"""
    return r"G:\Vision_Example_1\kit-app-template\source\apps"

current_dir = get_script_directory()
print(f"DEBUG: Detected script directory: {current_dir}")

if current_dir:
    if current_dir not in sys.path:
        sys.path.append(current_dir)

    # Now import the camera capture functionality
    try:
        from camera_capture_script import camera_capture
        print("SUCCESS: Imported camera_capture from module")
    except ImportError as e:
        print(f"Import failed: {e}")
        # If import fails, try to exec the script file directly
        script_path = os.path.join(current_dir, 'camera_capture_script.py')
        print(f"DEBUG: Trying to exec script at: {script_path}")
        if os.path.exists(script_path):
            print("SUCCESS: Found script file, executing...")
            exec(open(script_path).read())
            # After exec, camera_capture should be available in globals
            if 'camera_capture' not in globals():
                raise ImportError("Failed to load camera_capture from script")
            print("SUCCESS: Loaded camera_capture via exec")
        else:
            raise ImportError(f"Cannot find camera_capture_script.py at {script_path}")
else:
    raise ImportError("Could not determine script directory. Please ensure you're running from the correct location.")


class CameraCaptureUI:
    def __init__(self):
        self.window = None
        self.camera_path_field = None
        self.output_dir_field = None
        self.width_field = None
        self.height_field = None
        self.format_combo = None
        self.camera_list = None

    def create_window(self):
        """Create the UI window"""
        if self.window:
            self.window.visible = True
            return

        self.window = ui.Window("Multi-Camera Capture", width=500, height=600)

        with self.window.frame:
            with ui.VStack(spacing=10):
                # Title
                ui.Label("Multi-Camera Image Capture",
                        style={"font_size": 18, "color": 0xFF00B976})

                ui.Separator()

                # Camera Management Section
                with ui.CollapsableFrame("Camera Management", collapsed=False):
                    with ui.VStack(spacing=5):
                        # Manual camera path input
                        with ui.HStack():
                            ui.Label("Camera Path:", width=100)
                            self.camera_path_field = ui.StringField()
                            ui.Button("Add", width=50, clicked_fn=self._add_camera_manual)

                        # Quick add buttons
                        with ui.HStack():
                            ui.Button("Add Selected", clicked_fn=self._add_selected_cameras)
                            ui.Button("Add All in Stage", clicked_fn=self._add_all_cameras)
                            ui.Button("Clear All", clicked_fn=self._clear_cameras)

                # Camera List
                with ui.CollapsableFrame("Camera List", collapsed=False):
                    with ui.ScrollingFrame(height=150):
                        self.camera_list = ui.VStack()

                # Settings Section
                with ui.CollapsableFrame("Capture Settings", collapsed=False):
                    with ui.VStack(spacing=5):
                        # Output directory
                        with ui.HStack():
                            ui.Label("Output Dir:", width=100)
                            self.output_dir_field = ui.StringField()
                            self.output_dir_field.model.set_value(camera_capture.output_directory)
                            ui.Button("Browse", width=60, clicked_fn=self._browse_output_dir)

                        # Resolution
                        with ui.HStack():
                            ui.Label("Resolution:", width=100)
                            self.width_field = ui.IntField(width=80)
                            self.width_field.model.set_value(camera_capture.resolution[0])
                            ui.Label("x", width=10)
                            self.height_field = ui.IntField(width=80)
                            self.height_field.model.set_value(camera_capture.resolution[1])

                        # Image format
                        with ui.HStack():
                            ui.Label("Format:", width=100)
                            self.format_combo = ui.ComboBox(0, ".png", ".jpg", ".exr", ".tiff")

                ui.Separator()

                # Action buttons
                with ui.HStack():
                    ui.Button("Capture Images", height=40, clicked_fn=self._capture_images)
                    ui.Button("Show Status", height=40, clicked_fn=self._show_status)

                # Status area
                with ui.CollapsableFrame("Status", collapsed=True):
                    self.status_label = ui.Label("Ready", word_wrap=True)

        self._update_camera_list()

    def _add_camera_manual(self):
        """Add camera manually from text field"""
        camera_path = self.camera_path_field.model.get_value_as_string()
        if camera_path:
            success = camera_capture.add_camera_path(camera_path)
            if success:
                self.camera_path_field.model.set_value("")
                self._update_camera_list()
                self._update_status(f"Added camera: {camera_path}")
            else:
                self._update_status(f"Failed to add camera: {camera_path}")

    def _add_selected_cameras(self):
        """Add currently selected cameras"""
        selected = camera_capture.get_selected_cameras()
        for camera_path in selected:
            camera_capture.add_camera_path(camera_path)
        self._update_camera_list()
        self._update_status(f"Added {len(selected)} selected cameras")

    def _add_all_cameras(self):
        """Add all cameras in stage"""
        all_cameras = camera_capture.get_all_cameras_in_stage()
        for camera_path in all_cameras:
            camera_capture.add_camera_path(camera_path)
        self._update_camera_list()
        self._update_status(f"Added {len(all_cameras)} cameras from stage")

    def _clear_cameras(self):
        """Clear all cameras"""
        camera_capture.clear_camera_paths()
        self._update_camera_list()
        self._update_status("Cleared all cameras")

    def _browse_output_dir(self):
        """Browse for output directory"""
        # This is a simplified version - in a real implementation you'd use file dialog
        current_dir = self.output_dir_field.model.get_value_as_string()
        self._update_status(f"Current output directory: {current_dir}")

    def _capture_images(self):
        """Capture images from all cameras"""
        # Update settings
        self._update_settings()

        # Run capture asynchronously
        async def _capture():
            try:
                self._update_status("Capturing images...")
                captured_files = await camera_capture.capture_all_cameras()
                self._update_status(f"Captured {len(captured_files)} images successfully!")
            except Exception as e:
                self._update_status(f"Error during capture: {str(e)}")

        asyncio.ensure_future(_capture())

    def _show_status(self):
        """Show current status"""
        camera_capture.print_status()
        self._update_status(f"Status: {len(camera_capture.camera_paths)} cameras configured")

    def _update_settings(self):
        """Update capture settings from UI"""
        # Output directory
        output_dir = self.output_dir_field.model.get_value_as_string()
        if output_dir:
            camera_capture.set_output_directory(output_dir)

        # Resolution
        width = self.width_field.model.get_value_as_int()
        height = self.height_field.model.get_value_as_int()
        camera_capture.set_resolution(width, height)

        # Format
        formats = [".png", ".jpg", ".exr", ".tiff"]
        format_index = self.format_combo.model.get_item_value_model().get_value_as_int()
        camera_capture.set_image_format(formats[format_index])

    def _update_camera_list(self):
        """Update the camera list display"""
        if not self.camera_list:
            return

        # Clear existing items
        self.camera_list.clear()

        # Add current cameras
        for i, camera_path in enumerate(camera_capture.camera_paths):
            with self.camera_list:
                with ui.HStack():
                    ui.Label(f"{i+1}. {camera_path}", width=0)
                    ui.Button("Remove", width=60,
                             clicked_fn=lambda cp=camera_path: self._remove_camera(cp))

    def _remove_camera(self, camera_path):
        """Remove a specific camera"""
        camera_capture.remove_camera_path(camera_path)
        self._update_camera_list()
        self._update_status(f"Removed camera: {camera_path}")

    def _update_status(self, message):
        """Update status message"""
        if hasattr(self, 'status_label'):
            self.status_label.text = message
        carb.log_info(f"Camera Capture UI: {message}")

    def show(self):
        """Show the window"""
        if not self.window:
            self.create_window()
        else:
            self.window.visible = True

    def hide(self):
        """Hide the window"""
        if self.window:
            self.window.visible = False


# Global UI instance
camera_ui = CameraCaptureUI()

# Convenience functions
def show_camera_capture_ui():
    """Show the camera capture UI"""
    camera_ui.show()

def hide_camera_capture_ui():
    """Hide the camera capture UI"""
    camera_ui.hide()


# Auto-show UI when script is run
if __name__ == "__main__":
    show_camera_capture_ui()

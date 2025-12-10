# Multi-Camera Image Capture Script

This script allows you to capture images from multiple cameras in your USD Composer application without requiring Isaac Sim or Replicator extensions.

## Files

- `camera_capture_script.py` - Main capture functionality
- `camera_capture_ui.py` - Simple UI interface
- `CAMERA_CAPTURE_README.md` - This documentation

## How to Use

### Method 1: Using the UI (Recommended)

1. **Open USD Composer**
2. **Open Script Editor** (Window → Script Editor)
3. **Run the UI script** (choose the method that works best):

   **Option A: Direct execution with full paths**
   ```python
   exec(open(r'G:\Vision_Example_1\kit-app-template\source\apps\camera_capture_ui.py').read())
   ```

   **Option B: Change directory first**
   ```python
   import os
   os.chdir(r'G:\Vision_Example_1\kit-app-template\source\apps')
   exec(open('camera_capture_ui.py').read())
   ```

   **Option C: If you get import errors, run both scripts**
   ```python
   exec(open(r'G:\Vision_Example_1\kit-app-template\source\apps\camera_capture_script.py').read())
   exec(open(r'G:\Vision_Example_1\kit-app-template\source\apps\camera_capture_ui.py').read())
   ```
4. **The UI window will appear** with the following sections:
   - **Camera Management**: Add cameras manually or from selection
   - **Camera List**: View and manage selected cameras
   - **Capture Settings**: Configure output directory, resolution, and format
   - **Action Buttons**: Capture images and show status

### Method 2: Using Script Commands

1. **Open Script Editor** in USD Composer
2. **Load the script** (use full path to avoid import issues):
   ```python
   exec(open(r'G:\Vision_Example_1\kit-app-template\source\apps\camera_capture_script.py').read())
   ```
3. **Use the convenience functions**:

#### Add Cameras
```python
# Add camera by path (enter the full USD path)
add_camera("/World/Camera")
add_camera("/World/CameraRig/Camera1")

# Add all selected cameras (select cameras in stage first)
add_selected_cameras()

# Add all cameras in the stage
add_all_cameras()
```

#### Configure Settings
```python
# Set output directory
set_output_dir("C:/my_captures")

# Set resolution (width, height)
set_resolution(1920, 1080)

# Set image format (png, jpg, exr, tiff)
set_format("png")
```

#### Capture Images
```python
# Capture images from all configured cameras
capture_images()

# Show current configuration
show_status()
```

## Features

### Camera Management
- **Manual Path Entry**: Enter camera paths directly (e.g., `/World/Camera1`)
- **Selection-Based**: Add currently selected cameras from the stage
- **Auto-Discovery**: Find and add all cameras in the stage
- **Path Validation**: Ensures specified paths are valid camera prims

### Capture Settings
- **Configurable Resolution**: Set custom width/height for captures
- **Multiple Formats**: Support for PNG, JPG, EXR, TIFF
- **Custom Output Directory**: Specify where images should be saved
- **Timestamped Sessions**: Each capture session gets a unique timestamp folder

### Output Organization
Images are saved in the following structure:
```
output_directory/
└── capture_session_YYYYMMDD_HHMMSS/
    ├── camera_01_Camera.png
    ├── camera_02_Camera1.png
    └── camera_03_CameraRig_Camera2.png
```

## Finding Camera Paths

### Method 1: Stage Window
1. Open the **Stage** window
2. Expand your scene hierarchy
3. Look for camera icons or prims of type "Camera"
4. Right-click → "Copy Prim Path"

### Method 2: Selection
1. Select cameras in the viewport or stage
2. Use `add_selected_cameras()` in the script

### Method 3: Auto-Discovery
1. Use `add_all_cameras()` to automatically find all cameras

## Example Complete Workflow

```python
# Load the script
exec(open('camera_capture_script.py').read())

# Configure settings
set_output_dir("C:/temp/my_camera_captures")
set_resolution(1920, 1080)
set_format("png")

# Add cameras (choose one method)
add_camera("/World/Camera")                    # Manual
add_selected_cameras()                         # From selection
add_all_cameras()                             # All in stage

# Check configuration
show_status()

# Capture images
captured_files = capture_images()
print(f"Captured {len(captured_files)} images")
```

## Troubleshooting

### Common Issues

1. **"Invalid camera path" or "SetActiveCamera command not registered"**
   - Ensure the path exists in your stage
   - Verify the prim is actually a Camera type
   - Check spelling and case sensitivity
   - Test your camera path: `test_camera_path("/your/camera/path")`
   - The script now tries multiple camera setting methods automatically

2. **"No active viewport found"**
   - Make sure you have a viewport window open
   - Try opening Window → Viewport if needed

3. **"Capture extension not available" or "no attribute capture_viewport_to_file_async"**
   - The script now tries multiple capture methods automatically
   - Check the console output to see which method worked
   - Ensure `omni.kit.capture.viewport` extension is loaded
   - This should be included in USD Composer by default

4. **Images not saving**
   - Check that the output directory is writable
   - Ensure sufficient disk space
   - Verify the directory path is valid

### Getting Camera Paths

If you're unsure about camera paths:

```python
# List all cameras in the stage
exec(open('camera_capture_script.py').read())
all_cameras = camera_capture.get_all_cameras_in_stage()
for i, camera_path in enumerate(all_cameras):
    print(f"{i+1}. {camera_path}")
```

### Debug Capture Issues

If you're having capture problems, use the debug function:

```python
# Load the script first
exec(open(r'G:\Vision_Example_1\kit-app-template\source\apps\camera_capture_script.py').read())

# Run debug to see what capture methods are available
debug_capture()
```

This will show you:
- Available viewport methods
- Capture extension status
- Available Kit commands
- Specific error messages

## Requirements

- USD Composer / Omniverse Kit environment
- Cameras in the USD stage
- Write permissions to output directory

## Limitations

- Requires active viewport for capture
- Sequential capture (not simultaneous)
- Limited to viewport-based rendering
- No advanced rendering features (compared to Replicator)

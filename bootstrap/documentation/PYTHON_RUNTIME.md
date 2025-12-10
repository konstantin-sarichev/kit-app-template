# Python Runtime Environment for Vision Digital Twin

## Overview

The Vision Digital Twin project uses NVIDIA Omniverse Kit, which includes its own embedded Python environment. Understanding the Python runtime structure is critical for installing dependencies and debugging import errors.

---

## Python Installations in the Project

There are **three** Python installations in the `_build/` directory. Only **one** is used at runtime by Omniverse Kit.

| Location | Purpose | Used at Runtime? |
|----------|---------|------------------|
| `_build/target-deps/python/` | Build-time Python for compilation tools | ❌ No |
| `_build/host-deps/python/` | Host tools and utilities | ❌ No |
| **`_build/windows-x86_64/release/kit/python/`** | **Omniverse Kit runtime Python** | ✅ **Yes** |

---

## Runtime Python Location

The Python environment used by Omniverse Kit at runtime is:

```
_build/windows-x86_64/release/kit/python/python.exe
```

**This is the ONLY Python that matters for runtime imports.**

When you see import errors in Omniverse (e.g., `ModuleNotFoundError`), packages must be installed in THIS Python environment.

---

## Installing Packages

### Standard Installation

To install a package for use in Omniverse:

```powershell
# From project root
_build\windows-x86_64\release\kit\python\python.exe -m pip install <package_name>
```

### Example: Installing zmxtools

```powershell
_build\windows-x86_64\release\kit\python\python.exe -m pip install zmxtools
```

### Verify Installation

```powershell
_build\windows-x86_64\release\kit\python\python.exe -m pip list
```

---

## Currently Installed Packages

As of 2025-12-10, the following packages are installed in the Kit Python:

| Package | Version | Purpose |
|---------|---------|---------|
| pip | 24.3.1 | Package installer |
| zmxtools | 0.1.5 | Zemax .ZAR archive extraction |

---

## Required Packages for Vision DT Features

### Zemax Lens Integration

| Package | Version | Installation Command |
|---------|---------|---------------------|
| zmxtools | 0.1.5+ | `pip install zmxtools` |

**Without zmxtools:** `.ZAR` archive support is disabled. Only `.ZMX` text files can be parsed.

### Future Requirements

The following packages may be needed for future features:

| Feature | Package | Purpose |
|---------|---------|---------|
| MTF Post-Processing | numpy, scipy | FFT-based blur kernels |
| PSF Convolution | opencv-python | Image convolution |
| Advanced Distortion | opencv-python | Lens distortion correction |

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'xyz'"

1. **Check which Python is running:**
   The error log shows the Python path. Ensure packages are installed in that Python.

2. **Install in the correct Python:**
   ```powershell
   _build\windows-x86_64\release\kit\python\python.exe -m pip install xyz
   ```

3. **Restart Omniverse:**
   After installing packages, restart Omniverse to reload the Python environment.

### Package Installed But Not Found

If you installed a package but it's still not found:

1. **Verify installation location:**
   ```powershell
   _build\windows-x86_64\release\kit\python\python.exe -m pip show <package>
   ```

   Check the `Location:` field matches the kit/python path.

2. **Check for multiple installations:**
   You may have installed in the wrong Python. Check all three:
   ```powershell
   _build\target-deps\python\python.exe -m pip list
   _build\host-deps\python\python.exe -m pip list
   _build\windows-x86_64\release\kit\python\python.exe -m pip list
   ```

---

## Site Packages Location

The site-packages directory for Kit Python is:

```
_build/windows-x86_64/release/kit/python/Lib/site-packages/
```

---

## Python Version

Omniverse Kit uses Python 3.12:

```
_build/windows-x86_64/release/kit/python/python312.dll
```

Ensure any packages you install are compatible with Python 3.12.

---

## Running Python Scripts

### From Command Line

```powershell
_build\windows-x86_64\release\kit\python\python.exe my_script.py
```

### From Omniverse Script Editor

Code in the Omniverse Script Editor runs in the Kit Python environment. You can test imports directly:

```python
# Test if zmxtools is available
try:
    from zmxtools import zar
    print("zmxtools is installed!")
except ImportError as e:
    print(f"zmxtools not found: {e}")
```

---

## Common Package Installation Issues

### 1. No output from pip install

Sometimes pip install shows no output. Verify with:
```powershell
_build\windows-x86_64\release\kit\python\python.exe -m pip list | Select-String "package_name"
```

### 2. Permission errors

Run PowerShell as Administrator if you get permission errors.

### 3. Network/proxy issues

If pip can't download packages:
```powershell
# Download wheel file manually
_build\windows-x86_64\release\kit\python\python.exe -m pip download <package> -d .\temp\

# Install from local file
_build\windows-x86_64\release\kit\python\python.exe -m pip install .\temp\<package>.whl
```

---

## References

- `BOOTSTRAP_SYSTEM.md` - Bootstrap architecture
- `ZEMAX_LENS_INTEGRATION.md` - Zemax integration (requires zmxtools)
- `logs/changes.log` - Installation history and fixes

---

*Document Version: 1.0*
*Last Updated: December 2025*
*Author: Vision DT Project*

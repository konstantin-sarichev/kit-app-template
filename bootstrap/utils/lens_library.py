"""
Lens Library Manager for Vision Digital Twin

Manages a library of lens profiles parsed from Zemax files or created manually.
Provides search, load, and save functionality for lens data.

The lens library is stored as JSON files in a structured directory:
    assets/Lenses/Library/
    ├── lens_library.json          # Master index of all lenses
    ├── Manufacturer1/
    │   ├── Model1/
    │   │   ├── lens_data.json    # Parsed Zemax parameters
    │   │   └── source.zmx        # Original Zemax file (optional)
    │   └── Model2/
    └── Manufacturer2/

Reference: bootstrap/documentation/ZEMAX_LENS_INTEGRATION.md
"""

import json
import logging
import re
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

# Setup logging
logger = logging.getLogger(__name__)

# Try to import Omniverse modules for carb logging
try:
    import carb
    OMNIVERSE_AVAILABLE = True
except ImportError:
    OMNIVERSE_AVAILABLE = False


def _log_info(message: str):
    """Log to both Python logger and Omniverse carb if available."""
    logger.info(message)
    if OMNIVERSE_AVAILABLE:
        carb.log_info(f"[Vision DT LensLibrary] {message}")


def _log_warn(message: str):
    """Log warning to both Python logger and Omniverse carb if available."""
    logger.warning(message)
    if OMNIVERSE_AVAILABLE:
        carb.log_warn(f"[Vision DT LensLibrary] {message}")


def _log_error(message: str):
    """Log error to both Python logger and Omniverse carb if available."""
    logger.error(message)
    if OMNIVERSE_AVAILABLE:
        carb.log_error(f"[Vision DT LensLibrary] {message}")


class LensLibraryError(Exception):
    """Exception raised for lens library errors."""
    pass


class LensLibrary:
    """
    Manager for the Vision DT lens library.

    Provides functionality to:
    - Load and save lens library index
    - Add new lenses from Zemax files or manual specs
    - Search and filter lenses by parameters
    - Load lens data for application to cameras
    """

    def __init__(self, library_path: str = None):
        """
        Initialize lens library manager.

        Args:
            library_path: Path to lens library directory.
                         If None, uses default: assets/Lenses/Library
        """
        bootstrap_dir = Path(__file__).parent.parent
        build_root = bootstrap_dir.parent

        # Resolve project root: if running from _build, go one level higher
        if build_root.name == "_build":
            project_root = build_root.parent
        else:
            project_root = build_root

        if library_path is None:
            library_path = project_root / "assets" / "Lenses" / "Library"

        self.library_path = Path(library_path)
        # Fallback (old behavior) when library was written inside _build
        self._fallback_library_path = build_root / "assets" / "Lenses" / "Library"
        if self._fallback_library_path == self.library_path:
            self._fallback_library_path = None

        self.index_path = self.library_path / "lens_library.json"
        self._index: Optional[Dict] = None
        self._cache: Dict[str, Dict] = {}  # Cache of loaded lens data

    def ensure_directory_structure(self) -> bool:
        """
        Create library directory structure if it doesn't exist.

        Returns:
            True if successful
        """
        try:
            # If an older library exists in _build/assets, migrate it once
            if (
                self._fallback_library_path
                and not self.library_path.exists()
                and self._fallback_library_path.exists()
            ):
                _log_warn(
                    "Detected existing lens library in _build/assets/Lenses/Library - migrating to assets/Lenses/Library"
                )
                shutil.copytree(
                    self._fallback_library_path,
                    self.library_path,
                    dirs_exist_ok=True,
                )

            # Create main library directory
            self.library_path.mkdir(parents=True, exist_ok=True)

            # Create presets directory
            presets_dir = self.library_path.parent / "Presets"
            presets_dir.mkdir(parents=True, exist_ok=True)

            # Create empty index if not exists
            if not self.index_path.exists():
                self._create_empty_index()

            _log_info(f"Lens library directory structure verified: {self.library_path}")
            return True

        except Exception as e:
            _log_error(f"Failed to create library directory structure: {e}")
            return False

    def _create_empty_index(self):
        """Create an empty lens library index file."""
        empty_index = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
            "lenses": []
        }

        with open(self.index_path, 'w') as f:
            json.dump(empty_index, f, indent=2)

        self._index = empty_index

    def load_index(self) -> Dict:
        """
        Load the lens library index.

        Returns:
            Dictionary containing lens library index
        """
        if self._index is not None:
            return self._index

        if not self.index_path.exists():
            _log_warn(f"Lens library index not found, creating: {self.index_path}")
            self.ensure_directory_structure()

        try:
            with open(self.index_path, 'r') as f:
                self._index = json.load(f)
            return self._index

        except Exception as e:
            _log_error(f"Failed to load lens library index: {e}")
            return {"version": "1.0", "lenses": []}

    def save_index(self) -> bool:
        """
        Save the lens library index.

        Returns:
            True if successful
        """
        if self._index is None:
            return False

        try:
            self._index["updated"] = datetime.now().isoformat()

            with open(self.index_path, 'w') as f:
                json.dump(self._index, f, indent=2)

            _log_info("Lens library index saved")
            return True

        except Exception as e:
            _log_error(f"Failed to save lens library index: {e}")
            return False

    def get_lens_count(self) -> int:
        """Get number of lenses in library."""
        index = self.load_index()
        return len(index.get("lenses", []))

    def list_lenses(self) -> List[Dict]:
        """
        Get list of all lenses in library (index entries only).

        Returns:
            List of lens index entries
        """
        index = self.load_index()
        return index.get("lenses", [])

    def find_lens_by_id(self, lens_id: str) -> Optional[Dict]:
        """
        Find a lens index entry by ID.

        Args:
            lens_id: Unique lens identifier

        Returns:
            Lens index entry or None if not found
        """
        index = self.load_index()
        for lens in index.get("lenses", []):
            if lens.get("id") == lens_id:
                return lens
        return None

    def load_lens_data(self, lens_id: str) -> Optional[Dict]:
        """
        Load full lens data from JSON file.

        Args:
            lens_id: Unique lens identifier

        Returns:
            Complete lens data dictionary or None if not found
        """
        # Check cache first
        if lens_id in self._cache:
            return self._cache[lens_id]

        # Find lens in index
        lens_entry = self.find_lens_by_id(lens_id)
        if not lens_entry:
            _log_warn(f"Lens not found in library: {lens_id}")
            return None

        # Load data file
        data_path = self.library_path / lens_entry.get("data_path", "")
        if not data_path.exists():
            _log_error(f"Lens data file not found: {data_path}")
            return None

        try:
            with open(data_path, 'r') as f:
                lens_data = json.load(f)

            # Cache the loaded data
            self._cache[lens_id] = lens_data

            return lens_data

        except Exception as e:
            _log_error(f"Failed to load lens data for {lens_id}: {e}")
            return None

    def search_lenses(
        self,
        manufacturer: str = None,
        lens_type: str = None,
        focal_length_min: float = None,
        focal_length_max: float = None,
        f_number_max: float = None,
        is_telecentric: bool = None,
        name_contains: str = None
    ) -> List[Dict]:
        """
        Search lenses by various parameters.

        Args:
            manufacturer: Filter by manufacturer name (case-insensitive)
            lens_type: Filter by type (e.g., "telecentric", "standard", "macro")
            focal_length_min: Minimum focal length (mm)
            focal_length_max: Maximum focal length (mm)
            f_number_max: Maximum F-number
            is_telecentric: Filter by telecentric flag
            name_contains: Filter by model name containing string

        Returns:
            List of matching lens index entries
        """
        results = []
        index = self.load_index()

        for lens in index.get("lenses", []):
            # Apply filters
            if manufacturer:
                if lens.get("manufacturer", "").lower() != manufacturer.lower():
                    continue

            if lens_type:
                if lens.get("type", "").lower() != lens_type.lower():
                    continue

            if focal_length_min is not None:
                if lens.get("focal_length_mm", 0) < focal_length_min:
                    continue

            if focal_length_max is not None:
                if lens.get("focal_length_mm", float('inf')) > focal_length_max:
                    continue

            if f_number_max is not None:
                if lens.get("f_number", float('inf')) > f_number_max:
                    continue

            if is_telecentric is not None:
                if lens.get("is_telecentric", False) != is_telecentric:
                    continue

            if name_contains:
                if name_contains.lower() not in lens.get("model", "").lower():
                    continue

            results.append(lens)

        return results

    def add_lens(
        self,
        lens_id: str,
        manufacturer: str,
        model: str,
        lens_data: Dict,
        lens_type: str = "standard",
        zemax_path: str = None,
        overwrite: bool = False
    ) -> bool:
        """
        Add a new lens to the library.

        Args:
            lens_id: Unique identifier for the lens
            manufacturer: Manufacturer name
            model: Model name/number
            lens_data: Complete lens data dictionary
            lens_type: Type category (e.g., "telecentric", "standard", "macro")
            zemax_path: Path to original Zemax file (optional)
            overwrite: Whether to overwrite if lens_id already exists

        Returns:
            True if successful
        """
        # Check if lens already exists
        existing = self.find_lens_by_id(lens_id)
        if existing and not overwrite:
            _log_warn(f"Lens {lens_id} already exists. Use overwrite=True to replace.")
            return False

        # Ensure directory structure
        self.ensure_directory_structure()

        # Flat structure: all lens JSON files directly in Library folder
        # File named by lens_id for easy lookup
        safe_lens_id = self._sanitize_name(lens_id)
        data_path = self.library_path / f"{safe_lens_id}.json"

        # Include manufacturer/model in the lens_data for reference
        lens_data_copy = dict(lens_data)
        if "metadata" not in lens_data_copy:
            lens_data_copy["metadata"] = {}
        lens_data_copy["metadata"]["manufacturer"] = manufacturer
        lens_data_copy["metadata"]["model"] = model

        try:
            with open(data_path, 'w') as f:
                json.dump(lens_data_copy, f, indent=2)
        except Exception as e:
            _log_error(f"Failed to save lens data: {e}")
            return False

        # Copy Zemax source file if provided (into Library folder with lens_id prefix)
        zemax_dest_path = ""
        if zemax_path and Path(zemax_path).exists():
            zemax_ext = Path(zemax_path).suffix
            dest_zemax = self.library_path / f"{safe_lens_id}_source{zemax_ext}"
            shutil.copy(zemax_path, dest_zemax)
            zemax_dest_path = str(dest_zemax)

        # Create index entry
        relative_data_path = data_path.name  # Just the filename since it's in Library/

        optical = lens_data.get("optical", {})
        index_entry = {
            "id": lens_id,
            "manufacturer": manufacturer,
            "model": model,
            "type": lens_type,
            "focal_length_mm": optical.get("focal_length_mm", 0),
            "working_distance_mm": optical.get("working_distance_mm", 0),
            "f_number": optical.get("f_number", 0),
            "is_telecentric": optical.get("is_telecentric", False),
            "data_path": relative_data_path,
            "zemax_path": Path(zemax_dest_path).name if zemax_dest_path else "",
            "added": datetime.now().isoformat()
        }

        # Update or add to index
        index = self.load_index()
        if existing:
            # Replace existing entry
            index["lenses"] = [l for l in index["lenses"] if l["id"] != lens_id]

        index["lenses"].append(index_entry)
        self._index = index

        # Save index
        if not self.save_index():
            return False

        # Clear cache for this lens
        if lens_id in self._cache:
            del self._cache[lens_id]

        _log_info(f"Added lens to library: {lens_id} ({manufacturer} {model})")
        return True

    def add_lens_from_zemax(
        self,
        zemax_path: str,
        lens_id: str = None,
        manufacturer: str = None,
        lens_type: str = "standard",
        overwrite: bool = False
    ) -> Tuple[bool, str]:
        """
        Add a lens by parsing a Zemax file.

        Args:
            zemax_path: Path to .ZMX or .ZAR file
            lens_id: Optional lens ID (auto-generated if not provided)
            manufacturer: Optional manufacturer (extracted from file if possible)
            lens_type: Type category
            overwrite: Whether to overwrite existing lens

        Returns:
            Tuple of (success, lens_id or error message)
        """
        _log_info("=" * 60)
        _log_info(f"Importing Zemax file: {zemax_path}")
        _log_info("=" * 60)

        # Check if file exists
        zemax_file = Path(zemax_path)
        if not zemax_file.exists():
            error_msg = f"Zemax file not found: {zemax_path}"
            _log_error(error_msg)
            return (False, error_msg)

        file_size = zemax_file.stat().st_size
        _log_info(f"File size: {file_size:,} bytes")
        _log_info(f"File extension: {zemax_file.suffix}")

        try:
            # Import parser
            _log_info("Loading zemax_parser module...")
            try:
                from . import zemax_parser
                _log_info("zemax_parser imported from relative path")
            except ImportError:
                try:
                    import zemax_parser
                    _log_info("zemax_parser imported from absolute path")
                except ImportError:
                    error_msg = "zemax_parser module not available"
                    _log_error(error_msg)
                    return (False, error_msg)

        except Exception as import_error:
            error_msg = f"Failed to import zemax_parser: {import_error}"
            _log_error(error_msg)
            return (False, error_msg)

        try:
            # Parse Zemax file
            _log_info("Creating ZemaxParser instance...")
            parser = zemax_parser.ZemaxParser()

            _log_info("Starting Zemax file parsing...")
            lens_data_obj = parser.parse_file(zemax_path)
            _log_info("Zemax file parsing completed")

            lens_data = lens_data_obj.to_dict()
            _log_info("Converted lens data to dictionary")

            # Extract metadata
            metadata = lens_data.get("metadata", {})
            model = metadata.get("model", Path(zemax_path).stem)
            _log_info(f"Extracted model name: {model}")

            if manufacturer is None:
                _log_info("Manufacturer not provided, attempting to guess from model/notes...")
                # Try to extract from model name or notes
                manufacturer = self._guess_manufacturer(model, metadata.get("notes", ""))
                if manufacturer:
                    _log_info(f"Guessed manufacturer: {manufacturer}")
                else:
                    _log_warn("Could not determine manufacturer from file")

            # If still unknown, pick a friendlier bucket; tag telecentric imports distinctly
            optical = lens_data.get("optical", {})
            if manufacturer is None:
                if optical.get("is_telecentric"):
                    manufacturer = "Telecentric"
                else:
                    manufacturer = "Imported"
                _log_warn(f"Using default manufacturer: {manufacturer}")

            # Ensure metadata carries the resolved identifiers and source path
            metadata["manufacturer"] = manufacturer
            metadata["model"] = model
            metadata["zemax_file"] = str(Path(zemax_path).resolve().as_posix())
            lens_data["metadata"] = metadata

            # Infer lens type from telecentric flag
            if optical.get("is_telecentric"):
                lens_type = "telecentric"

            # Generate lens ID if not provided
            if lens_id is None:
                _log_info("Generating lens ID from manufacturer and model...")
                lens_id = self._generate_lens_id(manufacturer, model)
                _log_info(f"Generated lens ID: {lens_id}")
            else:
                _log_info(f"Using provided lens ID: {lens_id}")

            # Check if lens already exists
            existing = self.find_lens_by_id(lens_id)
            if existing:
                if overwrite:
                    _log_warn(f"Lens {lens_id} already exists - overwriting (overwrite=True)")
                else:
                    error_msg = f"Lens {lens_id} already exists. Use overwrite=True to replace."
                    _log_error(error_msg)
                    return (False, error_msg)

            # Add to library
            _log_info("Adding lens to library...")
            _log_info(f"  Manufacturer: {manufacturer}")
            _log_info(f"  Model: {model}")
            _log_info(f"  Type: {lens_type}")
            _log_info(f"  Lens ID: {lens_id}")

            success = self.add_lens(
                lens_id=lens_id,
                manufacturer=manufacturer,
                model=model,
                lens_data=lens_data,
                lens_type=lens_type,
                zemax_path=zemax_path,
                overwrite=overwrite
            )

            if success:
                _log_info("=" * 60)
                _log_info(f"✓ Successfully imported lens: {lens_id}")
                _log_info(f"  Location: {self.library_path}")
                _log_info("=" * 60)
                return (True, lens_id)
            else:
                error_msg = f"Failed to add lens {lens_id} to library"
                _log_error(error_msg)
                return (False, error_msg)

        except zemax_parser.ZemaxParseError as parse_error:
            error_msg = f"Zemax parsing error: {parse_error}"
            _log_error(error_msg)
            import traceback
            _log_error(f"Parse error traceback:\n{traceback.format_exc()}")
            return (False, error_msg)
        except Exception as e:
            error_msg = f"Failed to import Zemax file: {e}"
            _log_error(error_msg)
            import traceback
            _log_error(f"Import error traceback:\n{traceback.format_exc()}")
            return (False, error_msg)

    def remove_lens(self, lens_id: str, delete_files: bool = False) -> bool:
        """
        Remove a lens from the library.

        Args:
            lens_id: Lens identifier to remove
            delete_files: Whether to also delete the lens data files

        Returns:
            True if successful
        """
        lens_entry = self.find_lens_by_id(lens_id)
        if not lens_entry:
            _log_warn(f"Lens not found: {lens_id}")
            return False

        # Delete files if requested (flat structure: individual files in Library/)
        if delete_files:
            # Delete lens data JSON
            data_path = self.library_path / lens_entry.get("data_path", "")
            if data_path.exists():
                try:
                    data_path.unlink()
                except Exception as e:
                    _log_warn(f"Failed to delete lens data file: {e}")

            # Delete Zemax source file if exists
            zemax_path = lens_entry.get("zemax_path", "")
            if zemax_path:
                zemax_file = self.library_path / zemax_path
                if zemax_file.exists():
                    try:
                        zemax_file.unlink()
                    except Exception as e:
                        _log_warn(f"Failed to delete Zemax source file: {e}")

        # Remove from index
        index = self.load_index()
        index["lenses"] = [l for l in index["lenses"] if l["id"] != lens_id]
        self._index = index
        self.save_index()

        # Clear cache
        if lens_id in self._cache:
            del self._cache[lens_id]

        _log_info(f"Removed lens from library: {lens_id}")
        return True

    def get_lens_for_camera(self, lens_id: str) -> Optional[Dict]:
        """
        Get lens parameters formatted for camera application.

        Args:
            lens_id: Lens identifier

        Returns:
            Dictionary with camera-ready parameters, or None if not found
        """
        lens_data = self.load_lens_data(lens_id)
        if not lens_data:
            return None

        optical = lens_data.get("optical", {})
        distortion = lens_data.get("distortion", {})
        mtf = lens_data.get("mtf", {})
        metadata = lens_data.get("metadata", {})

        # Format for camera application
        return {
            # Identification
            "lens_id": lens_id,
            "model": metadata.get("model", ""),
            "manufacturer": metadata.get("manufacturer", ""),

            # Core optical parameters (applied to Omniverse camera)
            "focal_length_mm": optical.get("focal_length_mm", 0),
            "f_number": optical.get("f_number", 0),
            "working_distance_mm": optical.get("working_distance_mm", 0),

            # Extended optical parameters (stored as attributes)
            "field_of_view_deg": optical.get("field_of_view_deg", 0),
            "magnification": optical.get("magnification", 0),
            "numerical_aperture": optical.get("numerical_aperture", 0),
            "is_telecentric": optical.get("is_telecentric", False),
            "telecentric_type": optical.get("telecentric_type", ""),

            # Distortion (for OmniLensDistortionAPI)
            "distortion_model": distortion.get("model", "brown-conrady"),
            "k1": distortion.get("k1", 0),
            "k2": distortion.get("k2", 0),
            "k3": distortion.get("k3", 0),
            "p1": distortion.get("p1", 0),
            "p2": distortion.get("p2", 0),

            # MTF reference values
            "mtf_at_50lpmm": mtf.get("mtf_at_50lpmm", 0),
            "mtf_at_100lpmm": mtf.get("mtf_at_100lpmm", 0),

            # Source
            "zemax_file": metadata.get("zemax_file", "")
        }

    def _sanitize_name(self, name: str) -> str:
        """Sanitize a name for use as directory/file name."""
        # Replace spaces and special characters
        safe = re.sub(r'[^\w\-_.]', '_', name)
        # Remove multiple underscores
        safe = re.sub(r'_+', '_', safe)
        # Remove leading/trailing underscores
        safe = safe.strip('_')
        return safe or "unknown"

    def _generate_lens_id(self, manufacturer: str, model: str) -> str:
        """Generate a unique lens ID from manufacturer and model."""
        base_id = f"{self._sanitize_name(manufacturer)}_{self._sanitize_name(model)}".lower()

        # Check for uniqueness
        if not self.find_lens_by_id(base_id):
            return base_id

        # Add numeric suffix if needed
        counter = 1
        while self.find_lens_by_id(f"{base_id}_{counter}"):
            counter += 1

        return f"{base_id}_{counter}"

    def _guess_manufacturer(self, model: str, notes: str) -> Optional[str]:
        """Try to guess manufacturer from model name or notes."""
        # Common manufacturer patterns
        manufacturers = {
            "edmund": "Edmund Optics",
            "techspec": "Edmund Optics",
            "navitar": "Navitar",
            "schneider": "Schneider",
            "zeiss": "Zeiss",
            "tamron": "Tamron",
            "computar": "Computar",
            "fujinon": "Fujinon",
            "kowa": "Kowa",
            "nikon": "Nikon",
            "canon": "Canon",
            "sony": "Sony",
            "sigma": "Sigma",
            "olympus": "Olympus",
            "leica": "Leica",
            "thorlabs": "Thorlabs",
            "newport": "Newport",
            "opto": "Opto Engineering"
        }

        combined = f"{model} {notes}".lower()

        for pattern, name in manufacturers.items():
            if pattern in combined:
                return name

        return None


# Convenience functions

def get_default_library() -> LensLibrary:
    """Get the default lens library instance."""
    return LensLibrary()


def list_available_lenses() -> List[Dict]:
    """List all available lenses in the default library."""
    return get_default_library().list_lenses()


def load_lens(lens_id: str) -> Optional[Dict]:
    """Load lens data from the default library."""
    return get_default_library().load_lens_data(lens_id)


def search_lenses(**kwargs) -> List[Dict]:
    """Search lenses in the default library."""
    return get_default_library().search_lenses(**kwargs)


def import_zemax_file(file_path: str, overwrite: bool = True) -> Tuple[bool, str]:
    """
    Manually import a Zemax file into the lens library.

    This can be called from the Script Editor or a menu to import a specific file.

    Args:
        file_path: Full path to the .ZMX or .ZAR file
        overwrite: Whether to overwrite if lens already exists

    Returns:
        Tuple of (success, lens_id or error message)

    Example usage in Script Editor:
        from utils.lens_library import import_zemax_file
        success, result = import_zemax_file(r"C:\\path\\to\\lens.ZAR")
        if success:
            print(f"Imported lens: {result}")
        else:
            print(f"Import failed: {result}")
    """
    try:
        import carb
        carb.log_warn(f"[Vision DT] Manual import requested: {file_path}")
    except:
        pass

    lib = get_default_library()
    return lib.add_lens_from_zemax(file_path, overwrite=overwrite)


# Example usage
if __name__ == "__main__":
    # Create library manager
    lib = LensLibrary()

    # Ensure directory structure exists
    lib.ensure_directory_structure()

    # Import zemax_parser for testing
    try:
        from . import zemax_parser
    except ImportError:
        import zemax_parser

    # Create sample lens from manual specs
    sample_lens = zemax_parser.create_lens_data_from_specs(
        model="TechSpec #67-857",
        manufacturer="Edmund Optics",
        focal_length_mm=50.0,
        f_number=2.8,
        working_distance_mm=150.0,
        field_of_view_deg=40.0,
        magnification=0.5,
        is_telecentric=True,
        mtf_at_50lpmm=0.75,
        mtf_at_100lpmm=0.48
    )

    # Add to library
    success = lib.add_lens(
        lens_id="edmund_techspec_67857",
        manufacturer="Edmund Optics",
        model="TechSpec #67-857",
        lens_data=sample_lens.to_dict(),
        lens_type="telecentric"
    )

    if success:
        print("Sample lens added to library")

        # List lenses
        print("\nLenses in library:")
        for lens in lib.list_lenses():
            print(f"  - {lens['id']}: {lens['manufacturer']} {lens['model']}")

        # Search telecentric lenses
        print("\nTelecentric lenses:")
        for lens in lib.search_lenses(is_telecentric=True):
            print(f"  - {lens['id']}: {lens['focal_length_mm']}mm f/{lens['f_number']}")

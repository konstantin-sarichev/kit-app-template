"""Configuration for Omniverse documentation sources."""

import os
from pathlib import Path
from typing import Dict, List

# Cache configuration
CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_HOURS = int(os.getenv("OMNIVERSE_DOCS_CACHE_HOURS", "24"))
DEBUG = os.getenv("OMNIVERSE_DOCS_DEBUG", "0") == "1"

# Documentation source URLs
DOC_SOURCES = {
    "kit": {
        "base_url": os.getenv(
            "OMNIVERSE_DOCS_KIT_URL",
            "https://docs.omniverse.nvidia.com/kit/docs/kit-sdk/latest/",
        ),
        "api_path": "source/extensions/",
        "guides_path": "guide/",
    },
    "usd": {
        "base_url": os.getenv("OMNIVERSE_DOCS_USD_URL", "https://openusd.org/"),
        "api_path": "release/api/",
        "guides_path": "docs/",
    },
    "extensions": {
        "base_url": "https://docs.omniverse.nvidia.com/extensions/latest/",
        "patterns_path": "ext_dev_patterns/",
    },
    "replicator": {
        "base_url": "https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator/",
        "api_path": "api/",
    },
}

# Common search patterns for documentation
SEARCH_PATTERNS = {
    "stage_events": [
        "omni.usd.StageEventType",
        "get_stage_event_stream",
        "stage open event",
        "stage close event",
    ],
    "extension_lifecycle": [
        "IExt",
        "on_startup",
        "on_shutdown",
        "extension lifecycle",
    ],
    "usd_prims": [
        "Usd.Stage",
        "Usd.Prim",
        "GetPrimAtPath",
        "DefinePrim",
    ],
    "transforms": [
        "UsdGeom.Xformable",
        "SetTranslate",
        "GetLocalTransformation",
    ],
    "metadata": [
        "SetCustomData",
        "GetCustomData",
        "SetMetadata",
        "prim metadata",
    ],
}

# API namespace patterns
KIT_API_PATTERNS = [
    "omni.kit.*",
    "omni.usd.*",
    "omni.ui.*",
    "omni.graph.*",
    "omni.timeline.*",
    "carb.*",
]

USD_API_PATTERNS = [
    "pxr.Usd.*",
    "pxr.UsdGeom.*",
    "pxr.Sdf.*",
    "pxr.Tf.*",
    "pxr.Gf.*",
]

# Extension development topics
EXTENSION_TOPICS = {
    "lifecycle": "Extension lifecycle and initialization",
    "ui": "UI development with omni.ui",
    "stage": "Stage manipulation and USD operations",
    "events": "Event system and subscriptions",
    "settings": "Settings and configuration",
    "tests": "Testing extensions",
}


def ensure_cache_dir() -> Path:
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


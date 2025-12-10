"""
Industrial Dynamics Vision Digital Twin Bootstrap System

This package contains the bootstrap loader and capability modules that initialize
the Vision Digital Twin environment when an Omniverse stage is opened.

All capabilities are executed automatically in numeric order to ensure deterministic
startup and consistent configuration across all projects.
"""

__version__ = "1.0.0"
__author__ = "Industrial Dynamics"

from .loader import BootstrapLoader

__all__ = ["BootstrapLoader"]





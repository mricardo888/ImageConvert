"""
ImageConvert - A Python library for converting between different image formats.

This module provides functionality to convert between various image formats while
preserving metadata like EXIF information and file timestamps.

AVIF support requires Pillow 9.3.0 or higher.
"""

from .imageconvert import ImageConvert

__version__ = "0.2.0"
__all__ = ["ImageConvert"]
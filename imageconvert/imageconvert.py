"""
ImageConvert - A Python library for converting between different image formats

Author: Ricardo (https://github.com/mricardo888)

Supported formats:
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- WebP (.webp)
- SVG (.svg)
- RAW (.raw)
- HEIF/HEIC (.heif, .heic)

Features:
- Preserves EXIF and other metadata during conversion
- Maintains file creation and modification timestamps
- Supports batch processing and directory recursion
"""

import io
import os
import time
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple

import piexif
import pillow_heif
import rawpy
from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

pillow_heif.register_heif_opener()  # Register the HEIF opener with Pillow
__all__ = ["ImageConvert"]

# Windows creation time support (no-op on other platforms)
try:
    from win32_setctime import setctime
except ImportError:
    # Define a dummy function for non-Windows platforms
    def setctime(path, time):
        pass


class ImageConvert:
    """
    A class to convert images between different formats.

    Supports conversion between: JPG, JPEG, PNG, BMP, TIFF, TIF, WebP, HEIF, HEIC, SVG, and RAW formats.
    Preserves metadata including EXIF data and file timestamps.
    """

    SUPPORTED_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
        ".webp", ".heif", ".heic", ".svg", ".raw"
    ]

    # Formats that support EXIF metadata
    EXIF_SUPPORTED_FORMATS = [
        ".jpg", ".jpeg", ".tiff", ".tif", ".webp"
    ]

    # Map PIL format names to extensions
    FORMAT_TO_EXT = {
        "JPEG": ".jpg",
        "PNG": ".png",
        "BMP": ".bmp",
        "TIFF": ".tiff",
        "WEBP": ".webp",
    }

    @staticmethod
    def get_extension(filename: str) -> str:
        """Get the lowercase extension from a filename."""
        return os.path.splitext(filename)[1].lower()

    @classmethod
    def is_supported_format(cls, filename: str) -> bool:
        """Check if the file format is supported by the converter."""
        ext = cls.get_extension(filename)
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def _load_image(cls, input_path: Union[str, Path]) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Load an image from the given path based on its format.
        Returns a tuple of (PIL Image object, metadata dictionary).
        """
        input_path = str(input_path)
        ext = cls.get_extension(input_path)
        metadata = {'file_timestamps': {
            'created': os.path.getctime(input_path),
            'modified': os.path.getmtime(input_path),
            'accessed': os.path.getatime(input_path)
        }}

        # Store file system timestamps

        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.heif', '.heic']:
            # Standard formats handled directly by PIL (including HEIF/HEIC via pillow_heif)
            image = Image.open(input_path)

            # Extract EXIF data if present
            if ext in cls.EXIF_SUPPORTED_FORMATS or ext in ['.heif', '.heic']:
                try:
                    exif_dict = piexif.load(image.info.get('exif', b''))
                    metadata['exif'] = exif_dict
                except Exception:
                    # File might not have EXIF data
                    pass

            # Extract other metadata from image.info
            for key, value in image.info.items():
                if key != 'exif':  # We already handled exif separately
                    metadata[key] = value

            return image, metadata

        elif ext == '.svg':
            # SVG format
            drawing = svg2rlg(input_path)
            image = Image.open(io.BytesIO(renderPM.drawToString(drawing, fmt='PNG')))

            # SVGs don't have EXIF, but we might extract XML metadata if needed
            # For now, just including file system metadata
            return image, metadata

        elif ext == '.raw':
            # RAW format
            with rawpy.imread(input_path) as raw:
                rgb = raw.postprocess()
                # Try to extract metadata from RAW
                try:
                    if hasattr(raw, 'metadata') and raw.metadata is not None:
                        metadata['raw_metadata'] = raw.metadata
                except Exception:
                    pass

            # Convert numpy array to PIL Image
            image = Image.fromarray(rgb)
            return image, metadata

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _apply_metadata(
            image: Image.Image,
            metadata: Dict[str, Any],
            output_ext: str
    ) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Apply metadata to an image object based on the output format.

        Args:
            image: PIL Image object
            metadata: Dictionary of metadata
            output_ext: Output file extension

        Returns:
            Tuple of (image, save_options)
        """
        save_options = {}

        # Handle EXIF data for supported formats
        if output_ext in ImageConvert.EXIF_SUPPORTED_FORMATS and 'exif' in metadata:
            try:
                exif_bytes = piexif.dump(metadata['exif'])
                save_options['exif'] = exif_bytes
            except Exception as e:
                print(f"Warning: Could not apply EXIF data: {e}")

        # Handle other metadata
        for key, value in metadata.items():
            if key not in ['exif', 'file_timestamps', 'raw_metadata']:
                # Skip certain metadata that needs special handling
                if isinstance(value, (str, int, float, bytes)):
                    # Only copy simple types directly to image.info
                    image.info[key] = value

        # Explicitly return both objects
        return image, save_options

    @staticmethod
    def _apply_file_timestamps(output_path: str, timestamps: Dict[str, float]) -> None:
        """
        Apply file system timestamps to the output file.

        Args:
            output_path: Path to the output file
            timestamps: Dictionary with 'created', 'modified', and 'accessed' timestamps
        """
        # Set modification and access times
        os.utime(output_path, (timestamps['accessed'], timestamps['modified']))

        # Set creation time on Windows (no-op on other platforms)
        if os.name == 'nt':
            setctime(output_path, timestamps['created'])

    @classmethod
    def convert(
            cls,
            input_path: Union[str, Path],
            output_path: Union[str, Path],
            quality: int = 95,
            dpi: Optional[tuple] = None,
            preserve_metadata: bool = True,
            preserve_timestamps: bool = True
    ) -> str:
        """
        Convert an image from one format to another.

        Args:
            input_path: Path to the input image file
            output_path: Path where the converted image will be saved
            quality: Quality for lossy formats (0-100)
            dpi: Optional DPI tuple (x_dpi, y_dpi) for the output image
            preserve_metadata: Whether to preserve image metadata (EXIF, etc.)
            preserve_timestamps: Whether to preserve file timestamps

        Returns:
            The path to the converted image

        Raises:
            ValueError: If the input or output format is not supported
            FileNotFoundError: If the input file doesn't exist
        """
        # Convert to string if Path objects
        input_path = str(input_path)
        output_path = str(output_path)

        # Check if input file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Check if input and output formats are supported
        if not cls.is_supported_format(input_path):
            raise ValueError(f"Unsupported input format: {cls.get_extension(input_path)}")

        if not cls.is_supported_format(output_path):
            raise ValueError(f"Unsupported output format: {cls.get_extension(output_path)}")

        # Get the output extension
        output_ext = cls.get_extension(output_path)

        # Load the image based on its format and get metadata
        image, metadata = cls._load_image(input_path)

        # Set DPI if provided or preserve from metadata
        if dpi:
            image.info['dpi'] = dpi

        # Prepare base save options based on output format
        save_options = {}

        if output_ext in ['.jpg', '.jpeg']:
            save_options['quality'] = quality
            save_options['optimize'] = True
            if image.mode != 'RGB':
                image = image.convert('RGB')

        elif output_ext == '.png':
            save_options['optimize'] = True

        elif output_ext in ['.tiff', '.tif']:
            save_options['compression'] = 'tiff_lzw'

        elif output_ext == '.webp':
            save_options['quality'] = quality
            save_options['method'] = 6  # Higher quality but slower

        elif output_ext == '.bmp':
            # BMP doesn't have specific options
            pass

        elif output_ext in ['.heif', '.heic']:
            # PIL doesn't natively support HEIF/HEIC saving
            raise NotImplementedError("Saving to HEIF/HEIC is not yet implemented")

        elif output_ext == '.svg':
            # PIL doesn't support saving to SVG
            raise NotImplementedError("Conversion to SVG is not supported")

        elif output_ext == '.raw':
            # Cannot save to RAW format
            raise NotImplementedError("Conversion to RAW is not supported")

        # Apply metadata if requested
        if preserve_metadata:
            image, metadata_options = cls._apply_metadata(image, metadata, output_ext)
            save_options.update(metadata_options)

        # Save the image
        image.save(output_path, **save_options)

        # Apply original timestamps if requested
        if preserve_timestamps and 'file_timestamps' in metadata:
            cls._apply_file_timestamps(output_path, metadata['file_timestamps'])

        return output_path

    @classmethod
    def batch_convert(
            cls,
            input_dir: Union[str, Path],
            output_dir: Union[str, Path],
            output_format: str,
            quality: int = 95,
            dpi: Optional[tuple] = None,
            recursive: bool = False,
            preserve_metadata: bool = True,
            preserve_timestamps: bool = True
    ) -> List[str]:
        """
        Convert all supported images in a directory to the specified format.

        Args:
            input_dir: Directory containing input images
            output_dir: Directory where converted images will be saved
            output_format: Target format (e.g., '.png', '.jpg')
            quality: Quality for lossy formats (0-100)
            dpi: Optional DPI tuple (x_dpi, y_dpi) for output images
            recursive: Whether to process subdirectories
            preserve_metadata: Whether to preserve image metadata (EXIF, etc.)
            preserve_timestamps: Whether to preserve file timestamps

        Returns:
            List of paths to the converted images

        Raises:
            ValueError: If the output format is not supported
            NotADirectoryError: If input_dir is not a directory
        """
        # Normalize paths
        input_dir = str(input_dir)
        output_dir = str(output_dir)

        # Check if output format starts with a dot
        if not output_format.startswith('.'):
            output_format = f".{output_format}"

        # Check if output format is supported
        if output_format not in cls.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported output format: {output_format}")

        # Check if input directory exists
        if not os.path.isdir(input_dir):
            raise NotADirectoryError(f"Input directory not found: {input_dir}")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        converted_files = []

        # Walk through the directory
        for root, dirs, files in os.walk(input_dir):
            # Skip if not recursive and not in the top directory
            if not recursive and root != input_dir:
                continue

            # Create corresponding output subdirectory if recursive
            if recursive and root != input_dir:
                rel_path = os.path.relpath(root, input_dir)
                sub_output_dir = os.path.join(output_dir, rel_path)
                os.makedirs(sub_output_dir, exist_ok=True)
            else:
                sub_output_dir = output_dir

            # Process each file
            for file in files:
                input_path = os.path.join(root, file)

                # Check if the file is a supported image
                if cls.is_supported_format(input_path):
                    # Get base filename without extension
                    base_name = os.path.splitext(file)[0]

                    # Create output path with new extension
                    output_path = os.path.join(sub_output_dir, f"{base_name}{output_format}")

                    try:
                        # Convert the image
                        converted_path = cls.convert(
                            input_path,
                            output_path,
                            quality=quality,
                            dpi=dpi,
                            preserve_metadata=preserve_metadata,
                            preserve_timestamps=preserve_timestamps
                        )
                        converted_files.append(converted_path)
                    except Exception as e:
                        print(f"Error converting {input_path}: {e}")

        return converted_files

    @classmethod
    def get_image_info(cls, input_path: Union[str, Path], include_exif: bool = True) -> dict:
        """
        Get information about an image file.

        Args:
            input_path: Path to the image file
            include_exif: Whether to include detailed EXIF data

        Returns:
            Dictionary containing image information

        Raises:
            ValueError: If the format is not supported
            FileNotFoundError: If the file doesn't exist
        """
        # Convert to string if Path object
        input_path = str(input_path)

        # Check if file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"File not found: {input_path}")

        # Check if format is supported
        if not cls.is_supported_format(input_path):
            raise ValueError(f"Unsupported format: {cls.get_extension(input_path)}")

        # Get file size
        file_size = os.path.getsize(input_path)

        # Get image extension
        ext = cls.get_extension(input_path)

        # Load image and metadata
        image, metadata = cls._load_image(input_path)

        # Get timestamps
        timestamps = metadata.get('file_timestamps', {})

        # Convert timestamps to readable format
        readable_timestamps = {}
        for key, value in timestamps.items():
            readable_timestamps[key] = time.ctime(value)

        # Get information
        info = {
            'path': input_path,
            'format': image.format,
            'extension': ext,
            'mode': image.mode,
            'size': image.size,
            'width': image.width,
            'height': image.height,
            'file_size': file_size,
            'file_size_mb': round(file_size / (1024 * 1024), 2),
            'creation_time': readable_timestamps.get('created'),
            'modification_time': readable_timestamps.get('modified'),
            'access_time': readable_timestamps.get('accessed'),
        }

        # Add DPI information if available
        if 'dpi' in image.info:
            info['dpi'] = image.info['dpi']

        # Add metadata
        if include_exif and 'exif' in metadata:
            exif_info = {}
            exif_dict = metadata['exif']

            # Process EXIF data
            for ifd in exif_dict:
                if ifd == 'thumbnail':
                    continue

                if isinstance(exif_dict[ifd], dict):
                    for tag, value in exif_dict[ifd].items():
                        # Try to map tag to readable name
                        tag_name = None
                        try:
                            if ifd == 0:  # Main image IFD
                                tag_name = piexif.TAGS['Image'][tag]['name']
                            elif ifd == 1:  # Exif IFD
                                tag_name = piexif.TAGS['Exif'][tag]['name']
                            elif ifd == 2:  # GPS IFD
                                tag_name = piexif.TAGS['GPS'][tag]['name']
                            elif ifd == 3:  # Interop IFD
                                tag_name = piexif.TAGS['Interop'][tag]['name']
                        except KeyError:
                            tag_name = f"Unknown ({tag})"

                        # Convert byte strings to regular strings when possible
                        if isinstance(value, bytes):
                            try:
                                value = value.decode('utf-8')
                            except UnicodeDecodeError:
                                value = f"Binary data ({len(value)} bytes)"

                        exif_info[tag_name] = value

            # Extract commonly accessed EXIF data
            if 'DateTimeOriginal' in exif_info:
                info['date_taken'] = exif_info['DateTimeOriginal']

            if 'Make' in exif_info and 'Model' in exif_info:
                info['camera'] = f"{exif_info['Make']} {exif_info['Model']}"

            # Location data if available
            gps_info = exif_dict.get(2, {})
            if gps_info:
                try:
                    latref = gps_info.get(1, b'N').decode('ascii')
                    lat = gps_info.get(2, ((0, 1), (0, 1), (0, 1)))
                    lonref = gps_info.get(3, b'E').decode('ascii')
                    lon = gps_info.get(4, ((0, 1), (0, 1), (0, 1)))

                    # Check if we have valid GPS coordinates before calculating
                    if all(isinstance(x, tuple) and len(x) == 2 for x in lat) and \
                            all(isinstance(x, tuple) and len(x) == 2 for x in lon):

                        # Check for division by zero
                        if all(x[1] != 0 for x in lat) and all(x[1] != 0 for x in lon):
                            latitude = lat[0][0] / lat[0][1] + lat[1][0] / (60 * lat[1][1]) + lat[2][0] / (
                                        3600 * lat[2][1])
                            if latref == 'S': latitude = -latitude

                            longitude = lon[0][0] / lon[0][1] + lon[1][0] / (60 * lon[1][1]) + lon[2][0] / (
                                        3600 * lon[2][1])
                            if lonref == 'W': longitude = -longitude

                            info['gps'] = {'latitude': latitude, 'longitude': longitude}
                except (ValueError, TypeError, KeyError, IndexError, ZeroDivisionError) as e:
                    # Handle specific exceptions instead of bare except
                    # GPS extraction can be complex, skip if there are issues
                    info['gps_error'] = str(e)

            # Add all EXIF data if requested
            if include_exif:
                info['exif_data'] = exif_info

        return info


# Example usage
if __name__ == "__main__":
    # Single file conversion with metadata preservation
    try:
        ImageConvert.convert(
            "input.jpg",
            "output.png",
            quality=90,
            preserve_metadata=True,
            preserve_timestamps=True
        )
        print("Conversion successful with metadata preserved!")
    except Exception as e:
        print(f"Error: {e}")

    # Batch conversion with metadata preservation
    try:
        converted = ImageConvert.batch_convert(
            "input_folder",
            "output_folder",
            ".png",
            recursive=True,
            preserve_metadata=True,
            preserve_timestamps=True
        )
        print(f"Converted {len(converted)} images with metadata preserved")
    except Exception as e:
        print(f"Error: {e}")

    # Get detailed image info including EXIF data
    try:
        info = ImageConvert.get_image_info("image.jpg", include_exif=True)

        # Print basic info
        print(f"Image dimensions: {info['width']}x{info['height']}")
        print(f"Format: {info['format']}")
        print(f"File size: {info['file_size_mb']} MB")

        # Print metadata if available
        if 'date_taken' in info:
            print(f"Date taken: {info['date_taken']}")
        if 'camera' in info:
            print(f"Camera: {info['camera']}")
        if 'gps' in info and 'latitude' in info['gps'] and 'longitude' in info['gps']:
            print(f"Location: {info['gps']['latitude']}, {info['gps']['longitude']}")
        elif 'gps_error' in info:
            print(f"GPS data available but could not be parsed: {info['gps_error']}")

        # Print timestamps
        print(f"Created: {info['creation_time']}")
        print(f"Modified: {info['modification_time']}")
    except Exception as e:
        print(f"Error: {e}")

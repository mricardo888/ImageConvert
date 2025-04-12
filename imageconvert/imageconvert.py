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
- AVIF (.avif)

Features:
- Preserves EXIF and other metadata during conversion
- Maintains file creation and modification timestamps
- Supports batch processing and directory recursion
- Extracts metadata including EXIF, camera info, and GPS

Usage examples:

    from imageconvert import ImageConvert

    # Convert a single image from PNG to AVIF
    ImageConvert.convert("input.png", "output.avif")

    # Batch convert an entire folder to WebP
    ImageConvert.batch_convert("folder_in", "folder_out", output_format=".webp", recursive=True)

    # Get detailed image information
    info = ImageConvert.get_image_info("image.jpg")
    print(info["width"], info["height"], info.get("camera"))

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

# Register HEIF/AVIF support
try:
    # Try different registration methods for different pillow_heif versions
    try:
        pillow_heif.register_heif_opener()
    except Exception:
        pass

    try:
        pillow_heif.register_avif_opener()
    except Exception:
        pass

    # Add PIL format registration
    try:
        Image.register_mime("AVIF", "image/avif")
        Image.register_extension(".avif", "AVIF")
        Image.register_mime("HEIF", "image/heif")
        Image.register_extension(".heif", "HEIF")
        Image.register_extension(".heic", "HEIF")
    except Exception:
        pass

    has_avif_support = True
except ImportError:
    has_avif_support = False

try:
    from win32_setctime import setctime
except ImportError:
    def setctime(path, time):
        pass

class ImageConvert:
    """
    A class for converting images between different formats while preserving metadata.

    This class provides static methods for converting individual images, batch processing
    directories, and extracting image metadata.
    """

    # Supported file extensions
    SUPPORTED_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
        ".webp", ".heif", ".heic", ".svg", ".raw", ".avif"
    ]

    # Formats that support EXIF metadata
    EXIF_SUPPORTED_FORMATS = [
        ".jpg", ".jpeg", ".tiff", ".tif", ".webp"
    ]

    @staticmethod
    def get_extension(filename: str) -> str:
        """
        Extract the file extension from a filename.

        Args:
            filename (str): The path or filename to extract extension from.

        Returns:
            str: The lowercase file extension including the dot (e.g., '.jpg').
        """
        return os.path.splitext(filename)[1].lower()

    @classmethod
    def is_supported_format(cls, filename: str) -> bool:
        """
        Check if the file format is supported by the library.

        Args:
            filename (str): The path or filename to check.

        Returns:
            bool: True if the format is supported, False otherwise.

        Note:
            AVIF format requires the pillow-heif library to be properly installed.
        """
        ext = cls.get_extension(filename)
        if ext == '.avif' and not has_avif_support:
            return False
        return ext in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def _load_image(cls, input_path: Union[str, Path]) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Internal method to load an image and its metadata.

        Args:
            input_path (Union[str, Path]): Path to the input image.

        Returns:
            Tuple[Image.Image, Dict[str, Any]]: Tuple containing the image object and metadata dictionary.

        Raises:
            ValueError: If the file format is not supported.
        """
        input_path = str(input_path)
        ext = cls.get_extension(input_path)
        metadata = {'file_timestamps': {
            'created': os.path.getctime(input_path),
            'modified': os.path.getmtime(input_path),
            'accessed': os.path.getatime(input_path)
        }}

        if ext in cls.SUPPORTED_EXTENSIONS:
            image = Image.open(input_path)
            if ext in cls.EXIF_SUPPORTED_FORMATS or ext in ['.heif', '.heic', '.avif']:
                try:
                    exif_dict = piexif.load(image.info.get('exif', b''))
                    metadata['exif'] = exif_dict
                except Exception:
                    pass
            for key, value in image.info.items():
                if key != 'exif':
                    metadata[key] = value
            return image, metadata

        elif ext == '.svg':
            drawing = svg2rlg(input_path)
            image = Image.open(io.BytesIO(renderPM.drawToString(drawing, fmt='PNG')))
            return image, metadata

        elif ext == '.raw':
            with rawpy.imread(input_path) as raw:
                rgb = raw.postprocess()
                try:
                    if hasattr(raw, 'metadata') and raw.metadata is not None:
                        metadata['raw_metadata'] = raw.metadata
                except Exception:
                    pass
            image = Image.fromarray(rgb)
            return image, metadata

        else:
            raise ValueError(f"Unsupported file format: {ext}")

    @staticmethod
    def _apply_metadata(image: Image.Image, metadata: Dict[str, Any], output_ext: str) -> Tuple[Image.Image, Dict[str, Any]]:
        """
        Internal method to apply metadata to an image.

        Args:
            image (Image.Image): The image object.
            metadata (Dict[str, Any]): Metadata dictionary.
            output_ext (str): The output file extension.

        Returns:
            Tuple[Image.Image, Dict[str, Any]]: Tuple containing the image with metadata and save options.
        """
        save_options = {}
        if output_ext in ImageConvert.EXIF_SUPPORTED_FORMATS and 'exif' in metadata:
            try:
                exif_bytes = piexif.dump(metadata['exif'])
                save_options['exif'] = exif_bytes
            except Exception as e:
                print(f"Warning: Could not apply EXIF data: {e}")
        for key, value in metadata.items():
            if key not in ['exif', 'file_timestamps', 'raw_metadata']:
                if isinstance(value, (str, int, float, bytes)):
                    image.info[key] = value
        return image, save_options

    @staticmethod
    def _apply_file_timestamps(output_path: str, timestamps: Dict[str, float]) -> None:
        """
        Internal method to apply original timestamps to a file.

        Args:
            output_path (str): Path to the output file.
            timestamps (Dict[str, float]): Dictionary containing timestamp information.
        """
        os.utime(output_path, (timestamps['accessed'], timestamps['modified']))
        if os.name == 'nt':
            setctime(output_path, timestamps['created'])

    @classmethod
    def convert(cls, input_path: Union[str, Path], output_path: Union[str, Path], quality: int = 95,
                dpi: Optional[tuple] = None, preserve_metadata: bool = True,
                preserve_timestamps: bool = True) -> str:
        """
        Convert an image from one format to another.

        Args:
            input_path (Union[str, Path]): Path to the input image file.
            output_path (Union[str, Path]): Path for the output image file.
            quality (int, optional): Quality setting for lossy formats (1-100). Defaults to 95.
            dpi (Optional[tuple], optional): DPI setting as (x, y) tuple. Defaults to None.
            preserve_metadata (bool, optional): Whether to preserve image metadata. Defaults to True.
            preserve_timestamps (bool, optional): Whether to preserve file timestamps. Defaults to True.

        Returns:
            str: Path to the output file.

        Raises:
            FileNotFoundError: If the input file does not exist.
            ValueError: If input or output format is not supported.
            RuntimeError: If AVIF support is required but not available.
            NotImplementedError: If conversion to SVG or RAW is attempted.

        Examples:
            >>> ImageConvert.convert("input.jpg", "output.png")
            'output.png'

            >>> ImageConvert.convert("input.raw", "output.tiff", quality=100, preserve_metadata=True)
            'output.tiff'
        """
        input_path = str(input_path)
        output_path = str(output_path)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        input_ext = cls.get_extension(input_path)
        output_ext = cls.get_extension(output_path)

        if (input_ext == '.avif' or output_ext == '.avif') and not has_avif_support:
            raise RuntimeError("AVIF format requires 'pillow-heif'. Install with: pip install pillow-heif")

        if not cls.is_supported_format(input_path):
            raise ValueError(f"Unsupported input format: {input_ext}")
        if not cls.is_supported_format(output_path):
            raise ValueError(f"Unsupported output format: {output_ext}")

        image, metadata = cls._load_image(input_path)
        if dpi:
            image.info['dpi'] = dpi

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
            save_options['method'] = 6
        elif output_ext == '.bmp':
            pass
        elif output_ext == '.avif':
            save_options['quality'] = quality
            save_options['lossless'] = False
        elif output_ext in ['.heif', '.heic']:
            save_options['quality'] = quality
        elif output_ext == '.svg':
            raise NotImplementedError("Conversion to SVG is not supported")
        elif output_ext == '.raw':
            raise NotImplementedError("Conversion to RAW is not supported")

        if preserve_metadata:
            image, metadata_options = cls._apply_metadata(image, metadata, output_ext)
            save_options.update(metadata_options)

        ext_to_format = {
            '.jpg': 'JPEG',
            '.jpeg': 'JPEG',
            '.png': 'PNG',
            '.bmp': 'BMP',
            '.tiff': 'TIFF',
            '.tif': 'TIFF',
            '.webp': 'WEBP',
            '.avif': 'AVIF',
            '.heif': 'HEIF',
            '.heic': 'HEIF',
        }

        image_format = ext_to_format.get(output_ext, None)

        # Special handling for AVIF and HEIF formats
        if output_ext in ['.avif', '.heif', '.heic']:
            try:
                # Convert to RGB if needed
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                # Try multiple approaches to handle different pillow_heif versions

                # Approach 1: Try using from_pillow method (common in many versions)
                try:
                    heif_image = pillow_heif.from_pillow(image)
                    if output_ext == '.avif':
                        heif_image.save(output_path, quality=save_options.get('quality', 95), codec='av1')
                    else:
                        heif_image.save(output_path, quality=save_options.get('quality', 95))
                    return output_path
                except (AttributeError, TypeError):
                    pass

                # Approach 2: Try direct PIL save after registration (works in some versions)
                try:
                    image.save(output_path, format=image_format, **save_options)
                    return output_path
                except (KeyError, ValueError, AttributeError):
                    pass

                # If we got here, both approaches failed
                raise RuntimeError("Could not find a compatible method to save HEIF/AVIF images")

            except Exception as e:
                raise RuntimeError(f"Error saving {output_ext} format: {e}. Make sure pillow_heif is installed correctly.")
        else:
            image.save(output_path, format=image_format, **save_options)

        if preserve_timestamps and 'file_timestamps' in metadata:
            cls._apply_file_timestamps(output_path, metadata['file_timestamps'])

        return output_path

    @classmethod
    def batch_convert(cls, input_dir: Union[str, Path], output_dir: Union[str, Path],
                     output_format: str = None, recursive: bool = False, quality: int = 95,
                     preserve_metadata: bool = True, preserve_timestamps: bool = True,
                     skip_existing: bool = True) -> List[str]:
        """
        Convert multiple images in a directory to a specified format.

        Args:
            input_dir (Union[str, Path]): Input directory containing images.
            output_dir (Union[str, Path]): Output directory for converted images.
            output_format (str, optional): Target format with dot (e.g., '.webp').
                                          If None, preserves original format. Defaults to None.
            recursive (bool, optional): Whether to process subdirectories. Defaults to False.
            quality (int, optional): Quality setting for lossy formats (1-100). Defaults to 95.
            preserve_metadata (bool, optional): Whether to preserve image metadata. Defaults to True.
            preserve_timestamps (bool, optional): Whether to preserve file timestamps. Defaults to True.
            skip_existing (bool, optional): Skip files that already exist in the output directory. Defaults to True.

        Returns:
            List[str]: List of paths to all converted files.

        Raises:
            FileNotFoundError: If the input directory does not exist.
            ValueError: If the output format is not supported.

        Examples:
            >>> ImageConvert.batch_convert("photos", "converted", output_format=".webp")
            ['converted/img1.webp', 'converted/img2.webp', ...]

            >>> ImageConvert.batch_convert("raw_photos", "processed", recursive=True, preserve_metadata=False)
            ['processed/img1.jpg', 'processed/vacation/img2.jpg', ...]
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        if output_format and not cls.is_supported_format(f"dummy{output_format}"):
            raise ValueError(f"Unsupported output format: {output_format}")

        output_dir.mkdir(parents=True, exist_ok=True)
        converted_files = []

        # Determine which files to process
        if recursive:
            all_files = list(input_dir.glob('**/*'))
        else:
            all_files = list(input_dir.glob('*'))

        image_files = [f for f in all_files if f.is_file() and cls.is_supported_format(str(f))]

        for input_file in image_files:
            # Calculate relative path to maintain directory structure
            rel_path = input_file.relative_to(input_dir)

            if output_format:
                output_file = output_dir / rel_path.with_suffix(output_format)
            else:
                output_file = output_dir / rel_path

            # Create parent directories if needed
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # Skip if output file exists and skip_existing is True
            if skip_existing and output_file.exists():
                continue

            try:
                result = cls.convert(
                    input_file,
                    output_file,
                    quality=quality,
                    preserve_metadata=preserve_metadata,
                    preserve_timestamps=preserve_timestamps
                )
                converted_files.append(result)
            except Exception as e:
                print(f"Error converting {input_file}: {e}")

        return converted_files

    @classmethod
    def get_image_info(cls, image_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Extract detailed information from an image file.

        Args:
            image_path (Union[str, Path]): Path to the image file.

        Returns:
            Dict[str, Any]: Dictionary containing image information including:
                - dimensions (width, height)
                - format (image format)
                - mode (color mode)
                - timestamps (created, modified, accessed)
                - EXIF data (if available)
                - camera information (if available in EXIF)
                - GPS data (if available in EXIF)
                - other metadata

        Raises:
            FileNotFoundError: If the image file does not exist.
            ValueError: If the file format is not supported.

        Examples:
            >>> info = ImageConvert.get_image_info("vacation.jpg")
            >>> print(f"Image size: {info['width']}x{info['height']}")
            Image size: 3840x2160

            >>> if 'gps' in info:
            ...     print(f"Location: {info['gps']}")
            Location: {'latitude': 37.7749, 'longitude': -122.4194}
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        if not cls.is_supported_format(str(image_path)):
            raise ValueError(f"Unsupported image format: {image_path.suffix}")

        # Load the image and metadata
        image, metadata = cls._load_image(image_path)

        # Basic image information
        info = {
            'filename': image_path.name,
            'path': str(image_path),
            'width': image.width,
            'height': image.height,
            'format': image.format,
            'mode': image.mode,
            'timestamps': metadata.get('file_timestamps', {})
        }

        # Process EXIF data if available
        if 'exif' in metadata:
            exif_data = metadata['exif']

            # Extract camera information
            if '0th' in exif_data and piexif.ImageIFD.Make in exif_data['0th']:
                make = exif_data['0th'][piexif.ImageIFD.Make]
                model = exif_data['0th'].get(piexif.ImageIFD.Model, b'')

                if isinstance(make, bytes):
                    make = make.decode('utf-8', errors='replace').strip('\x00')
                if isinstance(model, bytes):
                    model = model.decode('utf-8', errors='replace').strip('\x00')

                info['camera'] = {
                    'make': make,
                    'model': model
                }

                # Add exposure settings if available
                if 'Exif' in exif_data:
                    exif = exif_data['Exif']
                    exposure_settings = {}

                    if piexif.ExifIFD.ExposureTime in exif:
                        num, den = exif[piexif.ExifIFD.ExposureTime]
                        exposure_settings['exposure_time'] = f"{num}/{den}s"

                    if piexif.ExifIFD.FNumber in exif:
                        num, den = exif[piexif.ExifIFD.FNumber]
                        exposure_settings['f_number'] = f"f/{num/den:.1f}"

                    if piexif.ExifIFD.ISOSpeedRatings in exif:
                        exposure_settings['iso'] = exif[piexif.ExifIFD.ISOSpeedRatings]

                    if exposure_settings:
                        info['camera']['exposure'] = exposure_settings

            # Extract GPS information if available
            if 'GPS' in exif_data and exif_data['GPS']:
                gps_data = exif_data['GPS']
                gps_info = {}

                # Extract latitude
                if (piexif.GPSIFD.GPSLatitudeRef in gps_data and
                    piexif.GPSIFD.GPSLatitude in gps_data):
                    lat_ref = gps_data[piexif.GPSIFD.GPSLatitudeRef]
                    lat = gps_data[piexif.GPSIFD.GPSLatitude]

                    if isinstance(lat_ref, bytes):
                        lat_ref = lat_ref.decode('ascii')

                    if len(lat) == 3:
                        lat_value = lat[0][0]/lat[0][1] + lat[1][0]/(lat[1][1]*60) + lat[2][0]/(lat[2][1]*3600)
                        if lat_ref == 'S':
                            lat_value = -lat_value
                        gps_info['latitude'] = lat_value

                # Extract longitude
                if (piexif.GPSIFD.GPSLongitudeRef in gps_data and
                    piexif.GPSIFD.GPSLongitude in gps_data):
                    lon_ref = gps_data[piexif.GPSIFD.GPSLongitudeRef]
                    lon = gps_data[piexif.GPSIFD.GPSLongitude]

                    if isinstance(lon_ref, bytes):
                        lon_ref = lon_ref.decode('ascii')

                    if len(lon) == 3:
                        lon_value = lon[0][0]/lon[0][1] + lon[1][0]/(lon[1][1]*60) + lon[2][0]/(lon[2][1]*3600)
                        if lon_ref == 'W':
                            lon_value = -lon_value
                        gps_info['longitude'] = lon_value

                # Extract altitude
                if piexif.GPSIFD.GPSAltitude in gps_data:
                    alt = gps_data[piexif.GPSIFD.GPSAltitude]
                    alt_ref = gps_data.get(piexif.GPSIFD.GPSAltitudeRef, 0)

                    alt_value = alt[0] / alt[1]
                    if alt_ref == 1:
                        alt_value = -alt_value
                    gps_info['altitude'] = alt_value

                if gps_info:
                    info['gps'] = gps_info

            # Add raw EXIF data for advanced users
            info['exif_raw'] = metadata['exif']

        # Include any RAW metadata if available
        if 'raw_metadata' in metadata:
            info['raw_metadata'] = metadata['raw_metadata']

        # Include any other metadata
        for key, value in metadata.items():
            if key not in ['exif', 'file_timestamps', 'raw_metadata'] and isinstance(value, (str, int, float)):
                info[key] = value

        return info
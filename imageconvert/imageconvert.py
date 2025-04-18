"""
ImageConvert - A Python library for converting between different image formats

Author: Ricardo (https://github.com/mricardo888)

Supported formats:
- JPEG (.jpg, .jpeg, .jfif)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- WebP (.webp)
- SVG (.svg)
- RAW (.raw)
- HEIF/HEIC (.heif, .heic)
- AVIF (.avif)
- PDF (.pdf)

Features:
- Preserves EXIF and other metadata during conversion
- Maintains file creation and modification timestamps
- Supports batch processing and directory recursion
- Extracts metadata including EXIF, camera info, and GPS
- PDF support for both reading and writing images

Usage examples:

    from imageconvert import ImageConvert

    # Convert a single image from PNG to AVIF
    ImageConvert.convert("input.png", "output.avif")

    # Batch convert an entire folder to WebP
    ImageConvert.batch_convert("folder_in", "folder_out", output_format=".webp", recursive=True)

    # Get detailed image information
    info = ImageConvert.get_image_info("image.jpg")
    print(info["width"], info["height"], info.get("camera"))

    # Convert PDF to images
    ImageConvert.pdf_to_images("document.pdf", "output_folder", format=".jpg")

    # Convert images to PDF
    ImageConvert.images_to_pdf(["img1.jpg", "img2.png"], "output.pdf")

"""

import io
import os
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple

import fitz
import piexif
import pillow_heif
import rawpy
from PIL import Image
from reportlab.graphics import renderPM
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
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

# Register JFIF as JPEG variant
try:
    Image.register_mime("JFIF", "image/jpeg")
    Image.register_extension(".jfif", "JPEG")
except Exception:
    pass

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
        ".webp", ".heif", ".heic", ".svg", ".raw", ".avif",
        ".jfif", ".pdf"
    ]

    # Formats that support EXIF metadata
    EXIF_SUPPORTED_FORMATS = [
        ".jpg", ".jpeg", ".tiff", ".tif", ".webp", ".jfif"
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

        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.heif', '.heic', '.avif', '.jfif']:
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

        elif ext == '.pdf':
            # Extract the first page of the PDF as an image
            pdf_document = fitz.open(input_path)
            if len(pdf_document) > 0:
                metadata['pdf_info'] = {
                    'page_count': len(pdf_document),
                    'title': pdf_document.metadata.get('title', ''),
                    'author': pdf_document.metadata.get('author', ''),
                    'subject': pdf_document.metadata.get('subject', ''),
                    'keywords': pdf_document.metadata.get('keywords', '')
                }

                # Convert first page to image
                first_page = pdf_document.load_page(0)
                pix = first_page.get_pixmap(alpha=False)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                pdf_document.close()
                return image, metadata
            else:
                pdf_document.close()
                raise ValueError(f"PDF file has no pages: {input_path}")

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
            if key not in ['exif', 'file_timestamps', 'raw_metadata', 'pdf_info']:
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

            >>> ImageConvert.convert("input.pdf", "output.jpg", quality=95)
            'output.jpg'
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

        # Special handling for PDF as output format
        if output_ext == '.pdf':
            # If input is already a PDF, use PyMuPDF to copy/optimize it
            if input_ext == '.pdf':
                doc = fitz.open(input_path)
                doc.save(output_path, garbage=4, deflate=True)
                doc.close()
                if preserve_timestamps and os.path.exists(input_path):
                    timestamps = {
                        'created': os.path.getctime(input_path),
                        'modified': os.path.getmtime(input_path),
                        'accessed': os.path.getatime(input_path)
                    }
                    cls._apply_file_timestamps(output_path, timestamps)
                return output_path

            # Convert single image to PDF
            else:
                image, metadata = cls._load_image(input_path)

                # Create PDF with same aspect ratio as the image
                width, height = image.size
                pdf_w, pdf_h = letter  # default to letter size

                # Create a new PDF with reportlab
                c = canvas.Canvas(output_path, pagesize=(pdf_w, pdf_h))

                # Calculate positioning to center the image on the page
                ratio = min(pdf_w/width, pdf_h/height)
                new_width = width * ratio
                new_height = height * ratio
                x_pos = (pdf_w - new_width) / 2
                y_pos = (pdf_h - new_height) / 2

                # Save image to a temporary buffer
                img_buffer = io.BytesIO()
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(img_buffer, format='JPEG', quality=quality)
                img_buffer.seek(0)

                # Draw the image on the PDF
                c.drawImage(img_buffer, x_pos, y_pos, width=new_width, height=new_height)

                # If metadata exists, add it to the PDF
                if preserve_metadata and 'exif' in metadata:
                    try:
                        exif = metadata['exif']
                        if '0th' in exif:
                            if piexif.ImageIFD.DocumentName in exif['0th']:
                                doc_name = exif['0th'][piexif.ImageIFD.DocumentName]
                                if isinstance(doc_name, bytes):
                                    doc_name = doc_name.decode('utf-8', errors='replace')
                                c.setTitle(doc_name)

                            if piexif.ImageIFD.Artist in exif['0th']:
                                artist = exif['0th'][piexif.ImageIFD.Artist]
                                if isinstance(artist, bytes):
                                    artist = artist.decode('utf-8', errors='replace')
                                c.setAuthor(artist)
                    except Exception as e:
                        print(f"Warning: Could not apply metadata to PDF: {e}")

                c.save()

                if preserve_timestamps and 'file_timestamps' in metadata:
                    cls._apply_file_timestamps(output_path, metadata['file_timestamps'])

                return output_path

        # Handle PDF as input with non-PDF output
        if input_ext == '.pdf' and output_ext != '.pdf':
            # Convert first page of PDF to image format
            pdf_document = fitz.open(input_path)
            if len(pdf_document) == 0:
                pdf_document.close()
                raise ValueError(f"PDF file has no pages: {input_path}")

            # Get the first page
            first_page = pdf_document.load_page(0)

            # Higher resolution for better quality
            zoom_factor = 2.0  # Adjust as needed for quality
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = first_page.get_pixmap(matrix=mat, alpha=False)

            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            metadata = {'file_timestamps': {
                'created': os.path.getctime(input_path),
                'modified': os.path.getmtime(input_path),
                'accessed': os.path.getatime(input_path)
            }}

            # Add some PDF metadata
            metadata['pdf_info'] = {
                'page_count': len(pdf_document),
                'title': pdf_document.metadata.get('title', ''),
                'author': pdf_document.metadata.get('author', '')
            }

            pdf_document.close()
        else:
            # Regular image handling
            image, metadata = cls._load_image(input_path)

        if dpi:
            image.info['dpi'] = dpi

        save_options = {}
        if output_ext in ['.jpg', '.jpeg', '.jfif']:
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
            '.jfif': 'JPEG',
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

        # Special handling for PDF files
        if image_path.suffix.lower() == '.pdf':
            try:
                pdf_doc = fitz.open(str(image_path))
                page_count = len(pdf_doc)

                info = {
                    'filename': image_path.name,
                    'path': str(image_path),
                    'format': 'PDF',
                    'page_count': page_count,
                    'timestamps': {
                        'created': os.path.getctime(str(image_path)),
                        'modified': os.path.getmtime(str(image_path)),
                        'accessed': os.path.getatime(str(image_path))
                    }
                }

                # Extract PDF metadata
                metadata = pdf_doc.metadata
                if metadata:
                    info['pdf_metadata'] = {
                        'title': metadata.get('title', ''),
                        'author': metadata.get('author', ''),
                        'subject': metadata.get('subject', ''),
                        'keywords': metadata.get('keywords', ''),
                        'creator': metadata.get('creator', ''),
                        'producer': metadata.get('producer', '')
                    }

                # Get first page dimensions
                if page_count > 0:
                    first_page = pdf_doc.load_page(0)
                    rect = first_page.rect
                    info['width'] = rect.width
                    info['height'] = rect.height

                pdf_doc.close()
                return info
            except Exception as e:
                raise ValueError(f"Error reading PDF file: {e}")

        # Load the image and metadata for non-PDF files
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

        # Include any PDF metadata if available
        if 'pdf_info' in metadata:
            info['pdf_info'] = metadata['pdf_info']

        # Include any other metadata
        for key, value in metadata.items():
            if key not in ['exif', 'file_timestamps', 'raw_metadata', 'pdf_info'] and isinstance(value, (str, int, float)):
                info[key] = value

        return info

    @classmethod
    def pdf_to_images(cls,
                      pdf_path: Union[str, Path],
                      output_dir: Union[str, Path],
                      format: str = '.jpg',
                      quality: int = 95,
                      dpi: int = 300,
                      pages: Union[List[int], None] = None) -> List[str]:
        """
        Convert a PDF file to a series of images, one per page.

        This method converts each page of a PDF into a separate image file in the specified format.
        It first renders pages as PNG and then converts to the target format if different from PNG.

        Parameters:
            pdf_path (str or Path): Path to the PDF file to be converted
            output_dir (str or Path): Directory where output images will be saved
            format (str): Output image format (e.g., '.jpg', '.png', '.tiff'), default is '.jpg'
            quality (int): Image quality (1-100) for formats that support quality settings, default is 95
            dpi (int): Resolution of output images in dots per inch, default is 300
            pages (List[int] or None): List of specific page indices to convert (zero-based);
                                      if None, converts all pages

        Returns:
            List[str]: A list of paths to the generated image files

        Raises:
            FileNotFoundError: If the specified PDF file does not exist
            ValueError: If the PDF has no pages or if no valid pages are specified to process

        Examples:
            # Convert all pages in a PDF to JPG images
            image_paths = ImageConverter.pdf_to_images(
                pdf_path="document.pdf",
                output_dir="output_images"
            )

            # Convert specific pages to PNG format with high resolution
            image_paths = ImageConverter.pdf_to_images(
                pdf_path="document.pdf",
                output_dir="output_images",
                format="png",
                dpi=600,
                pages=[0, 2, 4]  # Convert only the first, third, and fifth pages
            )

        Notes:
            - The method creates a temporary directory during processing that is automatically cleaned up afterward.
            - For PNG output, the method directly uses the rendered images; for other formats,
              it delegates to the class's convert() method.
            - The resolution is controlled by the dpi parameter, which affects the size and quality of the output images.
            - Page indexing is zero-based (the first page is index 0).
        """
        from pathlib import Path
        import shutil

        pdf_path = Path(pdf_path)
        output_dir = Path(output_dir)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        # Normalize format
        if not format.startswith('.'):
            format = f'.{format}'

        output_dir.mkdir(parents=True, exist_ok=True)
        tmp_dir = output_dir / "__pdf_tmp"
        tmp_dir.mkdir(exist_ok=True)

        zoom = dpi / 72.0
        doc = fitz.open(str(pdf_path))
        total = len(doc)
        if total == 0:
            doc.close()
            raise ValueError(f"PDF has no pages: {pdf_path}")

        pages_to_process = range(total) if pages is None else [p for p in pages if 0 <= p < total]
        if not pages_to_process:
            doc.close()
            raise ValueError(f"No valid pages to process: {pages}")

        output_files: List[str] = []
        # Render each page as PNG first
        for p in pages_to_process:
            page = doc.load_page(p)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            tmp_png = tmp_dir / f"page_{p}.png"
            pix.save(str(tmp_png))

            final_out = output_dir / f"page_{p}{format}"
            if format == '.png':
                # Just move the PNG into place
                tmp_png.replace(final_out)
            else:
                # Use the library’s own convert() to do the heavy lifting
                cls.convert(
                    str(tmp_png),
                    str(final_out),
                    quality=quality,
                    preserve_metadata=False,
                    preserve_timestamps=False
                )
            output_files.append(str(final_out))

        doc.close()
        # Clean up
        shutil.rmtree(tmp_dir)
        return output_files

    @classmethod
    def images_to_pdf(cls, image_paths: List[Union[str, Path]], output_pdf: Union[str, Path],
                      page_size: str = 'A4', fit_method: str = 'contain',
                      quality: int = 95, metadata: Dict[str, str] = None) -> str:
        """
        Convert multiple images to a single PDF file, with one image per page.

        Args:
            image_paths (List[Union[str, Path]]): List of paths to image files.
            output_pdf (Union[str, Path]): Path for the output PDF file.
            page_size (str, optional): Page size ('A4', 'letter', etc.). Defaults to 'A4'.
            fit_method (str, optional): How to fit images to pages - 'contain' (preserve aspect ratio),
                                       'cover' (fill page), 'stretch' (distort to fill). Defaults to 'contain'.
            quality (int, optional): JPEG compression quality for images in PDF (1-100). Defaults to 95.
            metadata (Dict[str, str], optional): PDF metadata such as title, author, etc. Defaults to None.

        Returns:
            str: Path to the created PDF file.

        Raises:
            FileNotFoundError: If any image file does not exist.
            ValueError: If no valid images are provided.
        """
        # Validate inputs
        if not image_paths:
            raise ValueError("No images provided")

        # Convert all paths to Path objects
        image_paths = [Path(p) for p in image_paths]
        output_pdf = Path(output_pdf)

        # Check if images exist
        missing_files = [str(p) for p in image_paths if not p.exists()]
        if missing_files:
            raise FileNotFoundError(f"Image files not found: {', '.join(missing_files)}")

        # Filter for supported image formats
        valid_images = [p for p in image_paths if cls.is_supported_format(str(p))]
        if not valid_images:
            raise ValueError("No valid image formats found in the provided list")

        # Determine page size dimensions
        page_sizes = {
            'a4': (595, 842),  # A4 in points
            'letter': (612, 792),  # US Letter in points
            'legal': (612, 1008),  # US Legal in points
            'a3': (842, 1191),  # A3 in points
            'a5': (420, 595),  # A5 in points
        }
        page_width, page_height = page_sizes.get(page_size.lower(), page_sizes['a4'])

        # Create a new PDF document
        c = canvas.Canvas(str(output_pdf), pagesize=(page_width, page_height))

        # Add metadata if provided
        if metadata:
            if 'title' in metadata:
                c.setTitle(metadata['title'])
            if 'author' in metadata:
                c.setAuthor(metadata['author'])
            if 'subject' in metadata:
                c.setSubject(metadata['subject'])
            if 'keywords' in metadata:
                c.setKeywords(metadata['keywords'])
            if 'creator' in metadata:
                c.setCreator(metadata['creator'])

        # Process each image
        for img_path in valid_images:
            try:
                img, img_metadata = cls._load_image(img_path)
                img_width, img_height = img.size

                # Determine scaling and positioning
                if fit_method == 'contain':
                    scale = min(page_width / img_width, page_height / img_height)
                elif fit_method == 'cover':
                    scale = max(page_width / img_width, page_height / img_height)
                elif fit_method == 'stretch':
                    scale = None
                else:
                    scale = min(page_width / img_width, page_height / img_height)

                if fit_method == 'stretch' or scale is None:
                    new_width, new_height = page_width, page_height
                    x_pos, y_pos = 0, 0
                else:
                    new_width = img_width * scale
                    new_height = img_height * scale
                    x_pos = (page_width - new_width) / 2
                    y_pos = (page_height - new_height) / 2

                # Save to buffer
                img_buffer = io.BytesIO()
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(img_buffer, format='JPEG', quality=quality)
                img_buffer.seek(0)

                # ← key change: wrap buffer in ImageReader
                reader = ImageReader(img_buffer)
                c.drawImage(reader, x_pos, y_pos, width=new_width, height=new_height)

                c.showPage()
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                continue

        c.save()
        return str(output_pdf)

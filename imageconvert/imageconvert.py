"""
ImageConvert - A Python library for converting between different image formats

Author: Ricardo (https://github.com/mricardo888)

Supported formats:
- JPEG (.jpg, .jpeg, .jfif)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)
- WebP (.webp)
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

"""

import io
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Tuple, Iterable, Generator, Callable

import fitz
import piexif
import pillow_heif
import rawpy
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

try:
    try:
        pillow_heif.register_heif_opener()
    except Exception:
        pass

    try:
        pillow_heif.register_avif_opener()
    except Exception:
        pass

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

    SUPPORTED_EXTENSIONS = [
        ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif",
        ".webp", ".heif", ".heic", ".raw", ".avif",
        ".jfif", ".pdf"
    ]

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
            pdf_document = fitz.open(input_path)
            if len(pdf_document) > 0:
                metadata['pdf_info'] = {
                    'page_count': len(pdf_document),
                    'title': pdf_document.metadata.get('title', ''),
                    'author': pdf_document.metadata.get('author', ''),
                    'subject': pdf_document.metadata.get('subject', ''),
                    'keywords': pdf_document.metadata.get('keywords', '')
                }

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
    def _apply_metadata(image: Image.Image, metadata: Dict[str, Any], output_ext: str) -> Tuple[
        Image.Image, Dict[str, Any]]:
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
            NotImplementedError: If conversion to RAW is attempted.

        Examples:
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

        if output_ext == '.pdf':
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

            else:
                image, metadata = cls._load_image(input_path)

                width, height = image.size
                pdf_w, pdf_h = letter

                c = canvas.Canvas(output_path, pagesize=(pdf_w, pdf_h))

                ratio = min(pdf_w / width, pdf_h / height)
                new_width = width * ratio
                new_height = height * ratio
                x_pos = (pdf_w - new_width) / 2
                y_pos = (pdf_h - new_height) / 2

                img_buffer = io.BytesIO()
                if image.mode != 'RGB':
                    image = image.convert('RGB')
                image.save(img_buffer, format='JPEG', quality=quality)
                img_buffer.seek(0)

                reader = ImageReader(img_buffer)
                c.drawImage(reader, x_pos, y_pos, width=new_width, height=new_height)

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

        if input_ext == '.pdf' and output_ext != '.pdf':
            pdf_document = fitz.open(input_path)
            if len(pdf_document) == 0:
                pdf_document.close()
                raise ValueError(f"PDF file has no pages: {input_path}")

            first_page = pdf_document.load_page(0)

            zoom_factor = 2.0
            mat = fitz.Matrix(zoom_factor, zoom_factor)
            pix = first_page.get_pixmap(matrix=mat, alpha=False)

            img_data = pix.tobytes("png")
            image = Image.open(io.BytesIO(img_data))

            metadata = {'file_timestamps': {
                'created': os.path.getctime(input_path),
                'modified': os.path.getmtime(input_path),
                'accessed': os.path.getatime(input_path)
            }, 'pdf_info': {
                'page_count': len(pdf_document),
                'title': pdf_document.metadata.get('title', ''),
                'author': pdf_document.metadata.get('author', '')
            }}

            pdf_document.close()
        else:
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

        if output_ext in ['.avif', '.heif', '.heic']:
            try:
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                try:
                    heif_image = pillow_heif.from_pillow(image)
                    if output_ext == '.avif':
                        heif_image.save(output_path, quality=save_options.get('quality', 95), codec='av1')
                    else:
                        heif_image.save(output_path, quality=save_options.get('quality', 95))
                    return output_path
                except (AttributeError, TypeError):
                    pass

                try:
                    image.save(output_path, format=image_format, **save_options)
                    return output_path
                except (KeyError, ValueError, AttributeError):
                    pass

                raise RuntimeError("Could not find a compatible method to save HEIF/AVIF images")

            except Exception as e:
                raise RuntimeError(
                    f"Error saving {output_ext} format: {e}. Make sure pillow_heif is installed correctly.")
        else:
            image.save(output_path, format=image_format, **save_options)

        if preserve_timestamps and 'file_timestamps' in metadata:
            cls._apply_file_timestamps(output_path, metadata['file_timestamps'])

        return output_path

    @classmethod
    def batch_convert(cls, input_dir: Union[str, Path], output_dir: Union[str, Path],
                      output_format: str = None, recursive: bool = False, quality: int = 95,
                      preserve_metadata: bool = True, preserve_timestamps: bool = True,
                      skip_existing: bool = True, workers: int = 1, stream: bool = False,
                      progress_callback: Optional[Callable[[Path, Path, Optional[Exception]], None]] = None
                      ) -> Union[List[str], Generator[str, None, List[str]]]:
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
            workers (int, optional): Number of parallel worker processes. Defaults to 1 (sequential).
            stream (bool, optional): If True, yields each converted file path as it finishes instead of returning a list.
                                     Defaults to False.
            progress_callback (Callable, optional): Called as progress_callback(input_path, output_path, error) after
                                                    each attempt. Defaults to None.

        Returns:
            List[str] | Generator[str, None, List[str]]: List of paths to all converted files or a generator if stream=True.

        Raises:
            FileNotFoundError: If the input directory does not exist.
            ValueError: If the output format is not supported.
        """
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)

        if not input_dir.exists():
            raise FileNotFoundError(f"Input directory not found: {input_dir}")

        if output_format and not cls.is_supported_format(f"dummy{output_format}"):
            raise ValueError(f"Unsupported output format: {output_format}")

        output_dir.mkdir(parents=True, exist_ok=True)

        def iter_files() -> Iterable[Tuple[Path, Path]]:
            globber = input_dir.rglob('*') if recursive else input_dir.glob('*')
            for input_file in globber:
                if not input_file.is_file():
                    continue
                if not cls.is_supported_format(str(input_file)):
                    continue

                rel_path = input_file.relative_to(input_dir)
                output_file = (output_dir / rel_path.with_suffix(output_format)) if output_format else (output_dir / rel_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)

                if skip_existing and output_file.exists():
                    try:
                        if os.path.getmtime(output_file) >= os.path.getmtime(input_file):
                            continue
                    except OSError:
                        continue

                yield input_file, output_file

        def stream_sequential(files_iter: Iterable[Tuple[Path, Path]]) -> Generator[str, None, None]:
            for input_file, output_file in files_iter:
                try:
                    result = cls.convert(
                        input_file,
                        output_file,
                        quality=quality,
                        preserve_metadata=preserve_metadata,
                        preserve_timestamps=preserve_timestamps
                    )
                    if progress_callback:
                        progress_callback(input_file, output_file, None)
                    yield result
                except Exception as e:
                    print(f"Error converting {input_file}: {e}")
                    if progress_callback:
                        progress_callback(input_file, output_file, e)

        def stream_parallel(files_list: List[Tuple[Path, Path]]) -> Generator[str, None, None]:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                future_to_paths = {
                    executor.submit(
                        _convert_worker,
                        (input_file, output_file, quality, preserve_metadata, preserve_timestamps)
                    ): (input_file, output_file)
                    for input_file, output_file in files_list
                }
                for future in as_completed(future_to_paths):
                    input_file, output_file = future_to_paths[future]
                    result_path, err = future.result()
                    if err:
                        print(f"Error converting {input_file}: {err}")
                        if progress_callback:
                            progress_callback(input_file, output_file, err)
                        continue
                    if result_path:
                        if progress_callback:
                            progress_callback(input_file, output_file, None)
                        yield result_path

        files_iter = iter_files()

        if stream:
            if workers and workers > 1:
                return stream_parallel(list(files_iter))
            return stream_sequential(files_iter)

        if workers and workers > 1:
            return list(stream_parallel(list(files_iter)))
        return list(stream_sequential(files_iter))

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
        """
        image_path = Path(image_path)

        if not image_path.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")

        if not cls.is_supported_format(str(image_path)):
            raise ValueError(f"Unsupported image format: {image_path.suffix}")

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

                if page_count > 0:
                    first_page = pdf_doc.load_page(0)
                    rect = first_page.rect
                    info['width'] = rect.width
                    info['height'] = rect.height

                pdf_doc.close()
                return info
            except Exception as e:
                raise ValueError(f"Error reading PDF file: {e}")

        image, metadata = cls._load_image(image_path)

        info = {
            'filename': image_path.name,
            'path': str(image_path),
            'width': image.width,
            'height': image.height,
            'format': image.format,
            'mode': image.mode,
            'timestamps': metadata.get('file_timestamps', {})
        }

        if 'exif' in metadata:
            exif_data = metadata['exif']

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

                if 'Exif' in exif_data:
                    exif = exif_data['Exif']
                    exposure_settings = {}

                    if piexif.ExifIFD.ExposureTime in exif:
                        num, den = exif[piexif.ExifIFD.ExposureTime]
                        exposure_settings['exposure_time'] = f"{num}/{den}s"

                    if piexif.ExifIFD.FNumber in exif:
                        num, den = exif[piexif.ExifIFD.FNumber]
                        exposure_settings['f_number'] = f"f/{num / den:.1f}"

                    if piexif.ExifIFD.ISOSpeedRatings in exif:
                        exposure_settings['iso'] = exif[piexif.ExifIFD.ISOSpeedRatings]

                    if exposure_settings:
                        info['camera']['exposure'] = exposure_settings

            if 'GPS' in exif_data and exif_data['GPS']:
                gps_data = exif_data['GPS']
                gps_info = {}

                if (piexif.GPSIFD.GPSLatitudeRef in gps_data and
                        piexif.GPSIFD.GPSLatitude in gps_data):
                    lat_ref = gps_data[piexif.GPSIFD.GPSLatitudeRef]
                    lat = gps_data[piexif.GPSIFD.GPSLatitude]

                    if isinstance(lat_ref, bytes):
                        lat_ref = lat_ref.decode('ascii')

                    if len(lat) == 3:
                        lat_value = lat[0][0] / lat[0][1] + lat[1][0] / (lat[1][1] * 60) + lat[2][0] / (
                                lat[2][1] * 3600)
                        if lat_ref == 'S':
                            lat_value = -lat_value
                        gps_info['latitude'] = lat_value

                if (piexif.GPSIFD.GPSLongitudeRef in gps_data and
                        piexif.GPSIFD.GPSLongitude in gps_data):
                    lon_ref = gps_data[piexif.GPSIFD.GPSLongitudeRef]
                    lon = gps_data[piexif.GPSIFD.GPSLongitude]

                    if isinstance(lon_ref, bytes):
                        lon_ref = lon_ref.decode('ascii')

                    if len(lon) == 3:
                        lon_value = lon[0][0] / lon[0][1] + lon[1][0] / (lon[1][1] * 60) + lon[2][0] / (
                                lon[2][1] * 3600)
                        if lon_ref == 'W':
                            lon_value = -lon_value
                        gps_info['longitude'] = lon_value

                if piexif.GPSIFD.GPSAltitude in gps_data:
                    alt = gps_data[piexif.GPSIFD.GPSAltitude]
                    alt_ref = gps_data.get(piexif.GPSIFD.GPSAltitudeRef, 0)

                    alt_value = alt[0] / alt[1]
                    if alt_ref == 1:
                        alt_value = -alt_value
                    gps_info['altitude'] = alt_value

                if gps_info:
                    info['gps'] = gps_info

            info['exif_raw'] = metadata['exif']

        if 'raw_metadata' in metadata:
            info['raw_metadata'] = metadata['raw_metadata']

        if 'pdf_info' in metadata:
            info['pdf_info'] = metadata['pdf_info']

        for key, value in metadata.items():
            if key not in ['exif', 'file_timestamps', 'raw_metadata', 'pdf_info'] and isinstance(value,
                                                                                                 (str, int, float)):
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
        for p in pages_to_process:
            page = doc.load_page(p)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            tmp_png = tmp_dir / f"page_{p}.png"
            pix.save(str(tmp_png))

            final_out = output_dir / f"page_{p}{format}"
            if format == '.png':
                tmp_png.replace(final_out)
            else:
                cls.convert(
                    str(tmp_png),
                    str(final_out),
                    quality=quality,
                    preserve_metadata=False,
                    preserve_timestamps=False
                )
            output_files.append(str(final_out))

        doc.close()
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
        if not image_paths:
            raise ValueError("No images provided")

        image_paths = [Path(p) for p in image_paths]
        output_pdf = Path(output_pdf)

        missing_files = [str(p) for p in image_paths if not p.exists()]
        if missing_files:
            raise FileNotFoundError(f"Image files not found: {', '.join(missing_files)}")

        valid_images = [p for p in image_paths if cls.is_supported_format(str(p))]
        if not valid_images:
            raise ValueError("No valid image formats found in the provided list")

        page_sizes = {
            'a4': (595, 842),
            'letter': (612, 792),
            'legal': (612, 1008),
            'a3': (842, 1191),
            'a5': (420, 595),
        }
        page_width, page_height = page_sizes.get(page_size.lower(), page_sizes['a4'])

        c = canvas.Canvas(str(output_pdf), pagesize=(page_width, page_height))

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

        for img_path in valid_images:
            try:
                img, img_metadata = cls._load_image(img_path)
                img_width, img_height = img.size

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

                img_buffer = io.BytesIO()
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(img_buffer, format='JPEG', quality=quality)
                img_buffer.seek(0)

                reader = ImageReader(img_buffer)
                c.drawImage(reader, x_pos, y_pos, width=new_width, height=new_height)

                c.showPage()
            except Exception as e:
                print(f"Error processing image {img_path}: {e}")
                continue

        c.save()
        return str(output_pdf)


def _convert_worker(args: Tuple[Path, Path, int, bool, bool]) -> Tuple[Optional[str], Optional[Exception]]:
    input_file, output_file, quality, preserve_metadata, preserve_timestamps = args
    try:
        result = ImageConvert.convert(
            input_file,
            output_file,
            quality=quality,
            preserve_metadata=preserve_metadata,
            preserve_timestamps=preserve_timestamps
        )
        return result, None
    except Exception as exc:
        return None, exc

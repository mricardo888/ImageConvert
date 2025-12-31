
# 📚 ImageConvert API Reference

This document provides detailed documentation for the `ImageConvert` class and its methods.

## Class: `ImageConvert`

The main class for converting images between different formats while preserving metadata.

### Constants

* **SUPPORTED_EXTENSIONS**: `['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.heif', '.heic', '.svg', '.raw', '.avif', '.jfif', '.pdf']`
* **EXIF_SUPPORTED_FORMATS**: `['.jpg', '.jpeg', '.tiff', '.tif', '.webp', '.jfif']`

---

## 🛠️ Core Methods

### `convert`
Converts a single image or PDF from one format to another.

```python
ImageConvert.convert(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    quality: int = 95,
    dpi: Optional[tuple] = None,
    preserve_metadata: bool = True,
    preserve_timestamps: bool = True
) -> str

```

**Parameters:**

* `input_path`: Path to the source file.
* `output_path`: Path for the destination file.
* `quality`: Quality setting for lossy formats (1-100). Default: `95`.
* `dpi`: DPI setting as (x, y) tuple. Default: `None`.
* `preserve_metadata`: Whether to copy EXIF/metadata. Default: `True`.
* `preserve_timestamps`: Whether to keep original created/modified times. Default: `True`.

**Returns:**

* `str`: Path to the output file.

**Raises:**

* `FileNotFoundError`: If input does not exist.
* `ValueError`: If formats are unsupported.
* `RuntimeError`: If AVIF/HEIC dependencies are missing.

---

### `batch_convert`

Recursively converts images in a directory.

```python
ImageConvert.batch_convert(
    input_dir: Union[str, Path],
    output_dir: Union[str, Path],
    output_format: str = None,
    recursive: bool = False,
    quality: int = 95,
    preserve_metadata: bool = True,
    preserve_timestamps: bool = True,
    skip_existing: bool = True
) -> List[str]

```

**Parameters:**

* `input_dir`: Source directory.
* `output_dir`: Destination directory.
* `output_format`: Target extension (e.g., `.webp`). If `None`, keeps original.
* `recursive`: Process subdirectories. Default: `False`.
* `quality`: Image quality (1-100). Default: `95`.
* `skip_existing`: Skip files if they already exist in output. Default: `True`.

**Returns:**

* `List[str]`: List of paths to successfully converted files.

---

### `get_image_info`

Extracts metadata, EXIF, GPS, and technical details.

```python
ImageConvert.get_image_info(image_path: Union[str, Path]) -> Dict[str, Any]

```

**Returns:**
A dictionary containing:

* Dimensions (`width`, `height`)
* Format and Mode
* `timestamps` (created, modified, accessed)
* `camera` (make, model, exposure settings)
* `gps` (latitude, longitude, altitude)
* `pdf_info` (page count, author - if PDF)

---

## 📄 PDF Tools

### `pdf_to_images`

Converts specific pages (or all) of a PDF into separate images.

```python
ImageConvert.pdf_to_images(
    pdf_path: Union[str, Path],
    output_dir: Union[str, Path],
    format: str = '.jpg',
    quality: int = 95,
    dpi: int = 300,
    pages: Union[List[int], None] = None
) -> List[str]

```

**Parameters:**

* `pdf_path`: Path to source PDF.
* `output_dir`: Directory to save images.
* `format`: Output format (e.g., `.png`). Default: `.jpg`.
* `dpi`: Resolution (dots per inch). Default: `300`.
* `pages`: List of page indices (0-based) to convert. If `None`, converts all.

---

### `images_to_pdf`

Compiles multiple images into a single PDF file.

```python
ImageConvert.images_to_pdf(
    image_paths: List[Union[str, Path]],
    output_pdf: Union[str, Path],
    page_size: str = 'A4',
    fit_method: str = 'contain',
    quality: int = 95,
    metadata: Dict[str, str] = None
) -> str

```

**Parameters:**

* `image_paths`: List of image file paths.
* `output_pdf`: Destination PDF path.
* `page_size`: 'A4', 'letter', 'legal', 'a3', or 'a5'. Default: `'A4'`.
* `fit_method`:
* `'contain'`: Preserves aspect ratio, fits within page.
* `'cover'`: Fills page, may crop.
* `'stretch'`: Distorts to fill page.


* `metadata`: Dict for PDF metadata (title, author, subject).

---

## 🔍 Utilities

### `is_supported_format`

Checks if a file extension is supported.

```python
ImageConvert.is_supported_format(filename: str) -> bool

```

### `get_extension`

Helper to extract lowercase extension.

```python
ImageConvert.get_extension(filename: str) -> str

```

# 🖼️ ImageConvert

[![PyPI version](https://img.shields.io/pypi/v/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![Python version](https://img.shields.io/pypi/pyversions/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**ImageConvert** is a Python library for converting images between different formats, while preserving metadata (EXIF) and timestamps.

## 🚀 Key Features

- **Format Support:** Convert between JPEG, PNG, TIFF, WebP, BMP, SVG, RAW, HEIC/HEIF, and AVIF
- **Metadata Preservation:** Keep EXIF data and other metadata intact
- **Timestamp Preservation:** Maintain file creation and modification times
- **Batch Processing:** Convert entire directories with optional recursion
- **Image Info Extraction:** Get detailed image metadata including GPS and camera details

## 📋 Quick Usage Examples

**Simple Conversion:**
```python
from imageconvert import ImageConvert

# Convert from JPG to PNG (preserves metadata by default)
ImageConvert.convert("photo.jpg", "photo.png")

# Convert from any format to AVIF with quality control
ImageConvert.convert("image.png", "image.avif", quality=80)
```

**Batch Conversion:**
```python
# Convert all supported images in a directory to WebP
ImageConvert.batch_convert(
    input_dir="photos", 
    output_dir="converted",
    output_format=".webp",
    recursive=True
)
```

**Get Image Info:**
```python
# Extract detailed image information
info = ImageConvert.get_image_info("photo.jpg")
print(f"Dimensions: {info['width']}x{info['height']}")
print(f"Camera: {info.get('camera', 'Unknown')}")
if 'gps' in info:
    print(f"Location: {info['gps']['latitude']}, {info['gps']['longitude']}")
```

## 📦 Installation

```bash
pip install imageconvert
```

✅ **Compatible with Python 3.7 and above**  
ℹ️ **AVIF, HEIC, and HEIF read/write support requires `pillow-heif` (installed automatically)**

## 🧰 Supported Formats

| Format | Extensions       | Read | Write | Notes                           |
|--------|------------------|------|-------|---------------------------------|
| JPEG   | `.jpg`, `.jpeg`  | ✓    | ✓     | Full metadata preservation      |
| PNG    | `.png`           | ✓    | ✓     | Lossless compression            |
| TIFF   | `.tiff`, `.tif`  | ✓    | ✓     | Full metadata preservation      |
| WebP   | `.webp`          | ✓    | ✓     | Modern web format               |
| BMP    | `.bmp`           | ✓    | ✓     | Basic bitmap format             |
| HEIF   | `.heif`, `.heic` | ✓    | ✓     | ✅ Now supports saving too       |
| AVIF   | `.avif`          | ✓    | ✓     | ✅ Requires pillow-heif          |
| RAW    | `.raw`           | ✓    | ✗     | Camera raw format (read only)   |
| SVG    | `.svg`           | ✓    | ✗     | Vector format (read only)       |

## 📄 License

This project is licensed under the MIT License.  
See the [LICENSE](./LICENSE) file for details.
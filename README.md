# 🖼️ ImageConvert

[![PyPI version](https://img.shields.io/pypi/v/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![Python version](https://img.shields.io/pypi/pyversions/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/imageconvert)](https://pypi.org/project/imageconvert/)

**ImageConvert** is a robust Python library designed for seamless conversion between modern image formats and PDFs. Unlike basic converters, it prioritizes **data integrity**—preserving EXIF metadata, GPS coordinates, and original file timestamps during the process.

## ✨ Key Features

* **🔄 Universal Conversion:** Support for JPEG, PNG, WebP, HEIC/AVIF, TIFF, BMP, and more.
* **📄 PDF Power Tools:**
    * **PDF to Image:** Render PDF pages as high-quality images.
    * **Image to PDF:** Compile multiple images into a single document.
* **💾 Metadata Safe:** Preserves EXIF data (Camera model, ISO, GPS) during conversion.
* **⏱️ Time Travel:** Retains original file creation, access, and modification timestamps (Windows/Linux/macOS supported).
* **📂 Batch Processing:** Recursively convert entire folder structures with a single command (stream results, optional multi-core).

## 📃 Full Documentation

For a complete guide on all classes, methods, and parameters, please see the [API Reference](docs/API_REFERENCE.md).

Explore the complete documentation and examples here:  
👉 [https://ricardos-projects.gitbook.io/imageconvert-docs](https://ricardos-projects.gitbook.io/imageconvert-docs)

## 📦 Installation

```bash
pip install imageconvert
```

*Note: This automatically installs necessary dependencies like `pillow-heif` (for AVIF/HEIC) and `pymupdf` (for PDF).*

## 🚀 Quick Start

### 1. Basic Conversion

Convert single images easily. Metadata is preserved by default.

```python
from imageconvert import ImageConvert

ImageConvert.convert("vacation.heic", "vacation.jpg")

ImageConvert.convert("input.png", "output.webp", quality=85)

```

### 2. PDF Operations

Handle PDF documents without external tools.

```python
# Extract all pages from a PDF as High-Res JPEGs
ImageConvert.pdf_to_images("contract.pdf", "output_folder", dpi=300)

# Create a PDF from a list of images (A4 size, contained fit)
ImageConvert.images_to_pdf(
    ["scan1.jpg", "scan2.jpg"], 
    "combined_doc.pdf",
    fit_method="contain"
)

```

### 3. Batch Processing

Convert an entire directory tree. Useful for optimizing libraries or web assets. Stream results as they finish and optionally use multiple processes.

```python
results = ImageConvert.batch_convert(
    input_dir="./raw_photos", 
    output_dir="./web_ready", 
    output_format=".webp", 
    recursive=True,
    skip_existing=True,
    workers=4,           # optional parallelism
    stream=True          # yields as soon as a file is done
)

for out_path in results:
    print("converted:", out_path)

```

`skip_existing` now compares modification times, so edited sources are re-converted even if an older output file exists.

```

### 4. Extracting Metadata

Get technical details, including GPS coordinates and PDF info.

```python
info = ImageConvert.get_image_info("photo.jpg")

print(f"Camera: {info.get('camera')}")
# Output: {'make': 'Apple', 'model': 'iPhone 13 Pro', 'exposure': {'iso': 120...}}

if 'gps' in info:
    print(f"Location: {info['gps']}")
    # Output: {'latitude': 40.7128, 'longitude': -74.0060}

```

## 🩰 Supported Formats

| Format | Extension | Read | Write | Notes |
| --- | --- | --- | --- | --- |
| **JPEG** | `.jpg`, `.jpeg`, `.jfif` | ✅ | ✅ | Optimized encoding |
| **PNG** | `.png` | ✅ | ✅ | Lossless |
| **WebP** | `.webp` | ✅ | ✅ | Google's web format |
| **HEIC** | `.heic`, `.heif` | ✅ | ✅ | iOS High Efficiency |
| **AVIF** | `.avif` | ✅ | ✅ | Next-gen compression |
| **TIFF** | `.tiff`, `.tif` | ✅ | ✅ | High quality archival |
| **PDF** | `.pdf` | ✅ | ✅ | Multi-page support |
| **RAW** | `.raw` | ✅ | ❌ | Read-only |
| **BMP** | `.bmp` | ✅ | ✅ | Basic bitmap |

## 🤝 Contributing

Contributions are welcome! Please visit the [GitHub Repository](https://github.com/mricardo888/ImageConvert) to report bugs or submit pull requests.

## 📄 License

This project is licensed under the **[MIT License](LICENSE)**.

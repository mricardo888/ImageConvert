# 🖼️ ImageConvert

[![PyPI version](https://img.shields.io/pypi/v/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![Python version](https://img.shields.io/pypi/pyversions/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Docs](https://img.shields.io/badge/documentation-blue)](https://ricardos-projects.gitbook.io/imageconvert-docs)

**ImageConvert** is a Python library for converting images (and PDFs) between different formats, while preserving metadata (EXIF) and timestamps.

## 🚀 Key Features

- **Format Support:** Convert between JPEG, PNG, TIFF, WebP, BMP, SVG, RAW, HEIC/HEIF, AVIF, and PDF
- **PDF Conversion:**
  - **PDF → Images:** Extract pages from a PDF as high‑resolution images
  - **Images → PDF:** Assemble multiple images into a single PDF document
- **Metadata Preservation:** Keep EXIF data and other metadata intact
- **Timestamp Preservation:** Maintain file creation and modification times
- **Batch Processing:** Convert entire directories with optional recursion
- **Image Info Extraction:** Get detailed image metadata including GPS and camera details

## 📋 Quick Usage Examples

### Simple Image Conversion
```python
from imageconvert import ImageConvert

# Convert from JPG to PNG (preserves metadata by default)
ImageConvert.convert("photo.jpg", "photo.png")

# Convert from any format to AVIF with quality control
ImageConvert.convert("image.png", "image.avif", quality=80)
```

### PDF → Images
```python
# Convert each page of a PDF to separate JPEG files
pages = ImageConvert.pdf_to_images(
    pdf_path="document.pdf",
    output_dir="output_images",
    format=".jpg",
    quality=90,
    dpi=300
)
print(f"Extracted pages: {pages}")
```

### Images → PDF
```python
# Combine PNG images into a single PDF
output_pdf = ImageConvert.images_to_pdf(
    image_paths=["page1.png", "page2.png", "page3.png"],
    output_pdf="combined.pdf",
    page_size="A4",
    fit_method="contain",
    quality=85,
    metadata={"title": "My Album", "author": "Ricardo"}
)
print(f"Created PDF: {output_pdf}")
```

### Batch Conversion
```python
# Convert all supported images in a directory to WebP
converted = ImageConvert.batch_convert(
    input_dir="photos",
    output_dir="converted",
    output_format=".webp",
    recursive=True
)
print(f"Files converted: {len(converted)}")
```

### Get Image or PDF Info
```python
# For images
info = ImageConvert.get_image_info("photo.jpg")
print(f"Dimensions: {info['width']}x{info['height']}")
# For PDFs
pdf_info = ImageConvert.get_image_info("document.pdf")
print(f"Pages: {pdf_info['page_count']}, Size: {pdf_info['width']}x{pdf_info['height']}")
```

## 📦 Installation

```bash
pip install imageconvert
```

✅ **Requires Python 3.7+**

> **Note:**
> - AVIF, HEIC, and HEIF read/write support requires `pillow-heif` (installed automatically with `imageconvert`)

## 🩰 Supported Formats

| Format | Extensions        | Read | Write | Notes                                        |
|--------|-------------------|------|-------|----------------------------------------------|
| JPEG   | `.jpg`, `.jpeg`   | ✓    | ✓     | Full metadata preservation                   |
| PNG    | `.png`            | ✓    | ✓     | Lossless compression                         |
| TIFF   | `.tiff`, `.tif`   | ✓    | ✓     | Full metadata preservation                   |
| WebP   | `.webp`           | ✓    | ✓     | Modern web format                            |
| BMP    | `.bmp`            | ✓    | ✓     | Basic bitmap format                          |
| HEIF   | `.heif`, `.heic`  | ✓    | ✓     | Requires `pillow-heif`                       |
| AVIF   | `.avif`           | ✓    | ✓     | Requires `pillow-heif`                       |
| RAW    | `.raw`            | ✓    | ✗     | Camera raw format (read only)                |
| SVG    | `.svg`            | ✓    | ✗     | Vector format (read only)                    |
| PDF    | `.pdf`            | ✓    | ✓     | PDF→Images & Images→PDF conversion           |

## 📃 Full Documentation

Explore the complete documentation and examples here:  
👉 [https://ricardos-projects.gitbook.io/imageconvert-docs](https://ricardos-projects.gitbook.io/imageconvert-docs)

## 📄 License

This project is licensed under the MIT License.  
See the [LICENSE](https://github.com/mricardo888/ImageConvert/blob/main/LICENSE) file for details.


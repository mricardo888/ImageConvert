# 🖼️ ImageConvert

[![PyPI version](https://img.shields.io/pypi/v/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![Python version](https://img.shields.io/pypi/pyversions/imageconvert.svg)](https://pypi.org/project/imageconvert/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

**ImageConvert** is a Python library for converting images between different formats, while preserving metadata (EXIF) and timestamps.

✅ **Compatible with Python 3.7 and above**  
🔗 **Available on PyPI:** [https://pypi.org/project/imageconvert/](https://pypi.org/project/imageconvert/)

---

## 🔧 Features

- Convert between formats: JPEG, PNG, TIFF, WebP, BMP, SVG, RAW, HEIC/HEIF
- Preserve EXIF metadata and file timestamps
- Batch conversion with optional recursion
- Extract image metadata including GPS and camera details

---

## 🧰 Supported Formats

| Format | Extensions       |
|--------|------------------|
| JPEG   | `.jpg`, `.jpeg`  |
| PNG    | `.png`           |
| TIFF   | `.tiff`, `.tif`  |
| WebP   | `.webp`          |
| BMP    | `.bmp`           |
| HEIF   | `.heif`, `.heic` |
| RAW    | `.raw`           |
| SVG    | `.svg`           |

---

## 📦 Installation

```bash
pip install imageconvert
```

---

## 🚀 Usage

### 🔁 Easy Example

If you just want to convert one image to another format:

```python
from imageconvert import ImageConvert

ImageConvert.convert("photo.jpg", "photo.png")
```

That’s it!  
✅ Metadata and timestamps are preserved by default.  
✅ Output format is automatically detected from the file extension.

---

### ⚙️ Advanced Example with Options

```python
from imageconvert import ImageConvert

ImageConvert.convert(
    "input.jpg",
    "output.png",
    quality=90,
    dpi=(300, 300),
    preserve_metadata=True,
    preserve_timestamps=True
)
```

---

### 📂 Batch Convert a Directory

```python
ImageConvert.batch_convert(
    input_dir="input_folder",
    output_dir="output_folder",
    output_format=".webp",
    recursive=True
)
```

---

### 🕵️‍♂️ Get Image Metadata

```python
info = ImageConvert.get_image_info("photo.jpg", include_exif=True)
print(info)
```

---

## 📄 License

This project is licensed under the MIT License.  
See the [LICENSE](./LICENSE) file for details.
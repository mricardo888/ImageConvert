# 🖼️ ImageConverter

ImageConverter is a Python library that allows you to convert images between various formats while preserving metadata (EXIF) and timestamps.

## 🔧 Features

- Convert between common formats: JPEG, PNG, TIFF, WebP, BMP, SVG, RAW, HEIC/HEIF
- Preserve EXIF metadata and file timestamps
- Batch conversion with optional recursion
- Extract image information including GPS and camera metadata

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

## 📦 Installation

```bash
pip install imageconvert
```

## 🚀 Usage

### Convert a single image

```python
from imageconvert import ImageConverter

ImageConverter.convert(
    "input.jpg",
    "output.png",
    quality=90,
    preserve_metadata=True,
    preserve_timestamps=True
)
```

### Batch convert a directory

```python
ImageConverter.batch_convert(
    "input_folder",
    "output_folder",
    ".webp",
    recursive=True
)
```

### Get image metadata

```python
info = ImageConverter.get_image_info("photo.jpg", include_exif=True)
print(info)
```

## 📄 License

This project is licensed under the MIT License. See the [LICENSE](./LICENSE) file for details.
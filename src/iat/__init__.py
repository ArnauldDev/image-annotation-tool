"""Core package for the Image Annotation Tool (IAT)."""

from .config import AppConfig, config, load_dotenv

from .image_processor import (
    apply_brightness_contrast,
    load_image,
    process_image,
    resize_with_aspect_ratio,
    rotate_image,
)

from .qt_image_editor import ImageEditorWindow

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("image-annotation-tool")  # nom du projet dans pyproject.toml
except PackageNotFoundError:
    __version__ = (
        "0.0.0+unknown"  # package non installé (ex. exécution brute des sources)
    )

__all__ = [
    "load_image",
    "rotate_image",
    "apply_brightness_contrast",
    "resize_with_aspect_ratio",
    "process_image",
    "ImageEditorWindow",
    "AppConfig",
    "config",
    "load_dotenv",
]

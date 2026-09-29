#!/usr/bin/env python3
# File Name: image_processor.py
# Description: Moteur de traitement d'image et recette JSON (annotations, loupes, export).
# Developer: ArnauldDev
# Last Modified: 2026-09-23

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

#: Default longest-side dimension used for the low-resolution preview shown
#: in the interactive editor. Working on this much smaller image keeps the
#: UI fluid regardless of the resolution of the source photograph.
DEFAULT_PREVIEW_MAX_DIMENSION = 1600


def load_image(path: str | Path) -> Image.Image:
    """Load an image from disk and normalize it to RGB."""
    image_path = Path(path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    with Image.open(image_path) as image:
        return image.convert("RGB")


def rotate_image(image: Image.Image, angle: float) -> Image.Image:
    """Rotate an image by the given angle while preserving image content."""
    if angle % 360 == 0:
        return image.copy()
    return image.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)


def _perspective_coefficients(
    source_points: tuple[tuple[float, float], ...],
    destination_points: tuple[tuple[float, float], ...],
) -> tuple[float, ...]:
    """Return the inverse perspective mapping required by Pillow."""
    equations: list[list[float]] = []
    for (source_x, source_y), (destination_x, destination_y) in zip(source_points, destination_points):
        equations.append([
            destination_x,
            destination_y,
            1.0,
            0.0,
            0.0,
            0.0,
            -source_x * destination_x,
            -source_x * destination_y,
            source_x,
        ])
        equations.append([
            0.0,
            0.0,
            0.0,
            destination_x,
            destination_y,
            1.0,
            -source_y * destination_x,
            -source_y * destination_y,
            source_y,
        ])

    for pivot in range(8):
        pivot_row = max(range(pivot, 8), key=lambda row: abs(equations[row][pivot]))
        if abs(equations[pivot_row][pivot]) < 1e-12:
            raise ValueError("Les points de correction trapézoïdale sont dégénérés.")
        equations[pivot], equations[pivot_row] = equations[pivot_row], equations[pivot]
        pivot_value = equations[pivot][pivot]
        equations[pivot] = [value / pivot_value for value in equations[pivot]]
        for row in range(8):
            if row == pivot:
                continue
            factor = equations[row][pivot]
            if factor:
                equations[row] = [
                    value - factor * pivot_value_value
                    for value, pivot_value_value in zip(equations[row], equations[pivot])
                ]

    return tuple(equations[row][8] for row in range(8))


def apply_trapezoid_correction(
    image: Image.Image,
    top_inset: float = 0.0,
    bottom_inset: float = 0.0,
    left_inset: float = 0.0,
    right_inset: float = 0.0,
) -> Image.Image:
    """Correct a trapezoid distortion into a rectangle using perspective mapping.

    Horizontal perspective (top/bottom_inset): fractions of image *width*.
    Vertical perspective (left/right_inset): fractions of image *height*.
    Positive values narrow the corresponding edge; negative values expand it.
    """
    if abs(top_inset) < 1e-9 and abs(bottom_inset) < 1e-9 and abs(left_inset) < 1e-9 and abs(right_inset) < 1e-9:
        return image.copy()

    width, height = image.size
    top = max(-0.49, min(0.49, float(top_inset)))
    bottom = max(-0.49, min(0.49, float(bottom_inset)))
    left = max(-0.49, min(0.49, float(left_inset)))
    right = max(-0.49, min(0.49, float(right_inset)))
    # Four source corners: top-left, top-right, bottom-right, bottom-left
    source_points = (
        (width * top + height * left, height * left),
        (width * (1.0 - top) - height * right, height * right),
        (width * (1.0 - bottom) - height * right, float(height) - height * right),
        (width * bottom + height * left, float(height) - height * left),
    )
    destination_points = (
        (0.0, 0.0),
        (float(width), 0.0),
        (float(width), float(height)),
        (0.0, float(height)),
    )
    coefficients = _perspective_coefficients(source_points, destination_points)
    return image.transform(image.size, Image.Transform.PERSPECTIVE, coefficients, Image.Resampling.BICUBIC)


def apply_brightness_contrast(
    image: Image.Image,
    brightness: float = 0.0,
    contrast: float = 1.0,
) -> Image.Image:
    """Apply brightness and contrast adjustments to an image."""
    processed = image.copy()

    if brightness != 0:
        factor = 1 + brightness / 100
        processed = ImageEnhance.Brightness(processed).enhance(factor)

    if contrast != 1.0:
        processed = ImageEnhance.Contrast(processed).enhance(contrast)

    return processed


def resize_with_aspect_ratio(
    image: Image.Image,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Image.Image:
    """Resize an image proportionally.

    If both width and height are supplied, width takes precedence and height is derived.
    """
    if width is None and height is None:
        return image.copy()

    original_width, original_height = image.size

    if width is not None:
        target_width = max(1, int(width))
        target_height = max(1, int(round(original_height * target_width / original_width)))
    else:
        target_height = max(1, int(height))
        target_width = max(1, int(round(original_width * target_height / original_height)))

    return image.resize((target_width, target_height), resample=Image.Resampling.LANCZOS)


def process_image(
    input_path: str | Path,
    output_path: str | Path,
    *,
    angle: float = 0,
    brightness: float = 0.0,
    contrast: float = 1.0,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Path:
    """Load, transform, and export an image as JPEG."""
    image = load_image(input_path)
    if angle:
        image = rotate_image(image, angle)
    image = apply_brightness_contrast(image, brightness=brightness, contrast=contrast)
    image = resize_with_aspect_ratio(image, width=width, height=height)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, format="JPEG", quality=95)
    return output


def make_preview(
    image: Image.Image,
    max_dimension: int = DEFAULT_PREVIEW_MAX_DIMENSION,
) -> tuple[Image.Image, float]:
    """Build a lightweight preview of ``image`` for fluid on-screen editing.

    Returns a tuple ``(preview_image, scale)`` where ``scale`` is the factor
    that converts preview-space coordinates back to full-resolution
    coordinates (``full = preview * scale``). Editing UIs should always keep
    working on this downsized copy and only apply the accumulated recipe to
    the original, full-resolution image at export time.
    """
    width, height = image.size
    longest_side = max(width, height)
    if longest_side <= max_dimension:
        return image.copy(), 1.0

    scale = longest_side / max_dimension
    target_size = (max(1, round(width / scale)), max(1, round(height / scale)))
    preview = image.resize(target_size, resample=Image.Resampling.LANCZOS)
    return preview, scale


# ---------------------------------------------------------------------------
# JSON-scriptable processing recipe
# ---------------------------------------------------------------------------
#
# The interactive editor lets a user experiment on a low-resolution preview.
# Every decision (rotation, brightness/contrast, annotations, loupe overlay,
# export size) is recorded as plain data in a ``ProcessingRecipe``. All
# coordinates stored in the recipe are expressed in *original image* pixel
# space, so the very same recipe can be replayed later, headlessly, against
# the full-resolution source file with :func:`apply_recipe` to produce an
# identical, pixel-accurate result.


@dataclass
class Annotation:
    """A single annotation drawn on top of the image.

    ``label`` uses ``(x1, y1)`` as the label position and ``(x2, y2)`` as
    the annotated target. ``text`` remains supported for older recipes.
    """

    type: str  # "text" | "rect" | "circle" | "line" | "label"
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    text: str = ""
    color: str = "#FFFF00"
    stroke_width: int = 3
    font_size: int = 28
    #: Corner radius in pixels for rect/circle/label shapes (0 = sharp corners).
    border_radius: int = 0
    #: "label" only: show the pointer arrow towards the annotated target.
    show_arrow: bool = True
    #: "label" only: box shape, "rect" (rounded rectangle) or "round" (ellipse).
    shape: str = "rect"
    #: "label" only: arrow line/head thickness, independent of the box stroke.
    arrow_stroke_width: int = 2
    #: "label" only: show the text inside the box.
    show_text: bool = True
    #: "label" only: whether the box background is filled (True) or transparent.
    fill_enabled: bool = True
    #: "label" only: render the text in bold.
    bold_text: bool = False
    #: "line" only: draw an arrowhead at the start/end point.
    line_arrow_start: bool = False
    line_arrow_end: bool = False
    #: Unique, auto-incremented identifier of the annotation inside its
    #: recipe. Referenced from ``ProcessingRecipe.layer_order`` as
    #: ``"annotation:<id>"``. Older JSON files predate this field; see
    #: :func:`_annotations_from_dict` for how they are migrated on load.
    id: int = 1

    @property
    def layer_token(self) -> str:
        """Token identifying this annotation inside ``ProcessingRecipe.layer_order``."""
        return f"annotation:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
            "text": self.text,
            "color": self.color,
            "stroke_width": self.stroke_width,
            "font_size": self.font_size,
            "border_radius": self.border_radius,
            "show_arrow": self.show_arrow,
            "shape": self.shape,
            "arrow_stroke_width": self.arrow_stroke_width,
            "show_text": self.show_text,
            "fill_enabled": self.fill_enabled,
            "bold_text": self.bold_text,
            "line_arrow_start": self.line_arrow_start,
            "line_arrow_end": self.line_arrow_end,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Annotation":
        return Annotation(
            type=data["type"],
            x1=float(data.get("x1", 0.0)),
            y1=float(data.get("y1", 0.0)),
            x2=float(data.get("x2", 0.0)),
            y2=float(data.get("y2", 0.0)),
            text=data.get("text", ""),
            color=data.get("color", "#FFFF00"),
            stroke_width=int(data.get("stroke_width", 3)),
            font_size=int(data.get("font_size", 28)),
            border_radius=int(data.get("border_radius", 0)),
            show_arrow=bool(data.get("show_arrow", True)),
            shape=data.get("shape", "rect"),
            arrow_stroke_width=int(data.get("arrow_stroke_width", 2)),
            show_text=bool(data.get("show_text", True)),
            fill_enabled=bool(data.get("fill_enabled", True)),
            bold_text=bool(data.get("bold_text", False)),
            line_arrow_start=bool(data.get("line_arrow_start", False)),
            line_arrow_end=bool(data.get("line_arrow_end", False)),
            id=int(data.get("id", 1)),
        )


@dataclass
class LoupeSpec:
    """Magnifier ("loupe") overlay: a circular zoomed inset with an arrow.

    A recipe may hold several loupes; each one carries a unique ``id``
    (1, 2, 3...) referenced from ``layer_order`` as ``"loupe:<id>"``.
    """

    enabled: bool = False
    center_x: float = 0.0
    center_y: float = 0.0
    radius: float = 120.0
    zoom: float = 2.0
    arrow_start_x: float = 0.0
    arrow_start_y: float = 0.0
    arrow_end_x: float = 0.0
    arrow_end_y: float = 0.0
    color: str = "#66D9EF"
    stroke_width: int = 4
    #: Rotation (degrees, clockwise) applied to the magnified content only,
    #: independent of the whole-image rotation/trapezoid correction.
    rotation: float = 0.0
    #: Thickness of the arrow pointing to the magnified target, independent of stroke_width.
    arrow_stroke_width: int = 2
    #: Unique, auto-incremented identifier of the loupe inside its recipe.
    id: int = 1

    @property
    def layer_token(self) -> str:
        """Token identifying this loupe inside ``ProcessingRecipe.layer_order``."""
        return f"loupe:{self.id}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "enabled": self.enabled,
            "center_x": self.center_x,
            "center_y": self.center_y,
            "radius": self.radius,
            "zoom": self.zoom,
            "arrow_start_x": self.arrow_start_x,
            "arrow_start_y": self.arrow_start_y,
            "arrow_end_x": self.arrow_end_x,
            "arrow_end_y": self.arrow_end_y,
            "color": self.color,
            "stroke_width": self.stroke_width,
            "rotation": self.rotation,
            "arrow_stroke_width": self.arrow_stroke_width,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "LoupeSpec":
        return LoupeSpec(
            enabled=bool(data.get("enabled", False)),
            center_x=float(data.get("center_x", 0.0)),
            center_y=float(data.get("center_y", 0.0)),
            radius=float(data.get("radius", 120.0)),
            zoom=float(data.get("zoom", 2.0)),
            arrow_start_x=float(data.get("arrow_start_x", 0.0)),
            arrow_start_y=float(data.get("arrow_start_y", 0.0)),
            arrow_end_x=float(data.get("arrow_end_x", 0.0)),
            arrow_end_y=float(data.get("arrow_end_y", 0.0)),
            color=data.get("color", "#66D9EF"),
            stroke_width=int(data.get("stroke_width", 4)),
            rotation=float(data.get("rotation", 0.0)),
            arrow_stroke_width=int(data.get("arrow_stroke_width", 2)),
            id=int(data.get("id", 1)),
        )


def next_loupe_id(loupes: list[Any]) -> int:
    """Return the next free loupe identifier (highest existing ``id`` + 1)."""
    return max((int(getattr(loupe, "id", 0)) for loupe in loupes), default=0) + 1


def next_annotation_id(annotations: list[Any]) -> int:
    """Return the next free annotation identifier (highest existing ``id`` + 1)."""
    return max((int(getattr(annotation, "id", 0)) for annotation in annotations), default=0) + 1


def compute_associated_paths(image_path: str | Path, export_width: int | None = None) -> tuple[Path, Path]:
    """Compute the associated recipe JSON and default export JPEG paths.

    Conventions:
    - 'name-raw.jpg' -> ('name-iat.json', 'name-iat.jpg')
    - 'name_raw.jpg' -> ('name-iat.json', 'name-iat.jpg')
    - 'name.jpg'     -> ('name-iat.json', 'name-iat.jpg')
    - optional export width adds a suffix like '-x1400' before the extension
    """
    path = Path(image_path)
    stem = path.stem
    lower_stem = stem.lower()
    if lower_stem.endswith("-raw"):
        base_stem = stem[:-4]
    elif lower_stem.endswith("_raw"):
        base_stem = stem[:-4]
    else:
        base_stem = stem

    export_suffix = f"-x{int(export_width)}" if export_width and int(export_width) > 0 else ""
    json_path = path.parent / f"{base_stem}-iat.json"
    export_path = path.parent / f"{base_stem}-iat{export_suffix}.jpg"
    return json_path, export_path


@dataclass
class ProcessingRecipe:
    """Fully serializable description of every operation to apply.

    This is the JSON contract between the interactive editor (which works on
    a small preview image for fluidity) and the batch/script engine (which
    replays the exact same operations on the original, full-resolution
    image). See :func:`apply_recipe` and :func:`process_image_with_recipe`.
    """

    source_image: str = ""
    angle: float = 0.0
    brightness: float = 0.0
    contrast: float = 1.0
    #: Trapezoid correction: (top, bottom, left, right) fractions.
    #: Older JSON files may store only 2 values — padded to 4 on load.
    trapezoid: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    crop: Optional[tuple[float, float, float, float]] = None  # (x1, y1, x2, y2)
    export_width: Optional[int] = None
    export_height: Optional[int] = None
    stroke_width: int = 3
    annotations: list[Annotation] = field(default_factory=list)
    #: Magnifier overlays, each identified by a unique ``id``.
    loupes: list[LoupeSpec] = field(default_factory=list)
    #: User-defined swatches saved with the recipe so its annotation palette
    #: can travel with an image between workstations.
    custom_colors: list[str] = field(default_factory=list)
    #: Visual stacking order, from front to back. Older recipes omit it.
    layer_order: list[str] = field(default_factory=list)

    @property
    def loupe(self) -> LoupeSpec:
        """First loupe of the recipe (read-only shortcut kept for older scripts)."""
        return self.loupes[0] if self.loupes else LoupeSpec()

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_image": self.source_image,
            "angle": self.angle,
            "brightness": self.brightness,
            "contrast": self.contrast,
            "trapezoid": list(self.trapezoid),
            "crop": list(self.crop) if self.crop is not None else None,
            "export": {"width": self.export_width, "height": self.export_height},
            "stroke_width": self.stroke_width,
            "annotations": [a.to_dict() for a in self.annotations],
            "loupes": [loupe.to_dict() for loupe in self.loupes],
            "custom_colors": list(self.custom_colors),
            "layer_order": list(self.layer_order),
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "ProcessingRecipe":
        export = data.get("export", {}) or {}
        crop = data.get("crop")
        raw_trap = data.get("trapezoid", [0.0, 0.0, 0.0, 0.0])
        # Rétrocompatibilité : anciens JSON stockent [top, bottom] seulement
        if len(raw_trap) == 2:
            raw_trap = list(raw_trap) + [0.0, 0.0]
        trapezoid = tuple(float(v) for v in raw_trap[:4])  # type: ignore[assignment]
        raw_annotations = list(data.get("annotations") or [])
        annotations, legacy_annotation_ids = _annotations_from_dict(raw_annotations)
        loupes = _loupes_from_dict(data)
        # Un ancien fichier n'attribuait aucun id à ses annotations : dans ce
        # cas, "annotation:<N>" dans layer_order désigne la position N de
        # l'annotation dans le tableau, pas son id, et doit être converti.
        is_legacy_annotation_format = bool(raw_annotations) and not all("id" in raw for raw in raw_annotations)
        layer_order = [str(token) for token in data.get("layer_order", [])]
        if not layer_order:
            layer_order = [annotation.layer_token for annotation in annotations]
            layer_order.extend(loupe.layer_token for loupe in loupes if loupe.enabled)
        else:
            migrated_order: list[str] = []
            for token in layer_order:
                if token == "loupe" and loupes:
                    # Rétrocompatibilité : l'ancien jeton "loupe" désigne la première loupe.
                    migrated_order.append(loupes[0].layer_token)
                    continue
                if is_legacy_annotation_format and token.startswith("annotation:"):
                    suffix = token.split(":", 1)[1]
                    if suffix.isdigit() and int(suffix) in legacy_annotation_ids:
                        migrated_order.append(f"annotation:{legacy_annotation_ids[int(suffix)]}")
                        continue
                migrated_order.append(token)
            layer_order = migrated_order
        return ProcessingRecipe(
            source_image=data.get("source_image", ""),
            angle=float(data.get("angle", 0.0)),
            brightness=float(data.get("brightness", 0.0)),
            contrast=float(data.get("contrast", 1.0)),
            trapezoid=trapezoid,  # type: ignore[arg-type]
            crop=tuple(crop) if crop else None,  # type: ignore[arg-type]
            export_width=export.get("width"),
            export_height=export.get("height"),
            stroke_width=int(data.get("stroke_width", 3)),
            annotations=annotations,
            loupes=loupes,
            custom_colors=[str(color) for color in data.get("custom_colors", [])],
            layer_order=layer_order,
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @staticmethod
    def from_json(text: str) -> "ProcessingRecipe":
        return ProcessingRecipe.from_dict(json.loads(text))

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(self.to_json(), encoding="utf-8")
        return output

    @staticmethod
    def load(path: str | Path) -> "ProcessingRecipe":
        return ProcessingRecipe.from_json(Path(path).read_text(encoding="utf-8"))


def _annotations_from_dict(raw_annotations: list[Any]) -> tuple[list[Annotation], dict[int, int]]:
    """Parse the annotation list, assigning ids to entries that don't have any.

    Older recipes stored no ``id`` at all on annotations, relying on their
    position in the JSON array. Here, every annotation is guaranteed a
    unique ``id`` (missing or duplicated ones are renumbered, exactly like
    :func:`_loupes_from_dict` already does for loupes).

    Returns the parsed annotations together with a mapping from each
    annotation's original position in ``raw_annotations`` to the id it now
    carries, so :meth:`ProcessingRecipe.from_dict` can rewrite legacy
    ``"annotation:<index>"`` tokens found in ``layer_order`` into
    ``"annotation:<id>"`` ones without losing any data.
    """
    annotations: list[Annotation] = []
    legacy_index_to_id: dict[int, int] = {}
    for index, raw in enumerate(raw_annotations):
        annotation = Annotation.from_dict(raw)
        if "id" not in raw or any(existing.id == annotation.id for existing in annotations):
            annotation.id = next_annotation_id(annotations)
        legacy_index_to_id[index] = annotation.id
        annotations.append(annotation)
    return annotations, legacy_index_to_id


def _loupes_from_dict(data: dict[str, Any]) -> list[LoupeSpec]:
    """Read the loupe list, accepting the single ``"loupe"`` object of older recipes.

    Missing or duplicated identifiers are renumbered so every loupe keeps a
    unique ``id``.
    """
    if "loupes" in data:
        raw_loupes = list(data.get("loupes") or [])
    else:
        legacy = data.get("loupe") or {}
        # Un ancien fichier contenait toujours un objet loupe, même inutilisé.
        raw_loupes = [legacy] if legacy.get("enabled", False) or "center_x" in legacy else []
    loupes: list[LoupeSpec] = []
    for raw in raw_loupes:
        loupe = LoupeSpec.from_dict(raw)
        if "id" not in raw or any(existing.id == loupe.id for existing in loupes):
            loupe.id = next_loupe_id(loupes)
        loupes.append(loupe)
    return loupes


def _load_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    if bold:
        try:
            return ImageFont.truetype("arialbd.ttf", size)
        except OSError:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _hex_to_rgba(color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    """Convert a ``#RRGGBB`` (or ``#RGB``) string to an RGBA tuple."""
    value = color.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
    return (r, g, b, alpha)


def draw_annotations(image: Image.Image, annotations: list[Annotation]) -> Image.Image:
    """Burn a list of annotations into ``image`` (full-resolution coordinates)."""
    rendered = image.convert("RGBA")
    draw = ImageDraw.Draw(rendered)

    for item in reversed(annotations):
        if item.type == "text":
            font = _load_font(item.font_size)
            draw.text((item.x1, item.y1), item.text, fill=item.color, font=font)
        elif item.type == "label":
            font = _load_font(item.font_size, bold=item.bold_text)
            padding = max(6, item.font_size // 4)
            left, top = item.x1, item.y1
            text_box = draw.textbbox((left + padding, top + padding), item.text, font=font)
            right = text_box[2] + padding
            bottom = text_box[3] + padding
            box = (left, top, right, bottom)
            fill = (20, 24, 33) if item.fill_enabled else None
            if item.shape == "round":
                draw.ellipse(box, fill=fill, outline=item.color, width=item.stroke_width)
            else:
                draw.rounded_rectangle(
                    box,
                    radius=max(0, item.border_radius),
                    fill=fill,
                    outline=item.color,
                    width=item.stroke_width,
                )
            if item.show_text:
                center_x, center_y = (left + right) / 2, (top + bottom) / 2
                draw.text((center_x, center_y), item.text, fill=(255, 255, 255), font=font, anchor="mm")
            if item.show_arrow:
                anchor_x = min(max(item.x2, left), right)
                anchor_y = min(max(item.y2, top), bottom)
                draw.line((anchor_x, anchor_y, item.x2, item.y2), fill=item.color, width=item.arrow_stroke_width)
                _draw_arrow_head(draw, anchor_x, anchor_y, item.x2, item.y2, item.color, item.arrow_stroke_width)
        elif item.type == "rect":
            bbox = (min(item.x1, item.x2), min(item.y1, item.y2), max(item.x1, item.x2), max(item.y1, item.y2))
            if item.border_radius > 0:
                draw.rounded_rectangle(bbox, radius=item.border_radius, outline=item.color, width=item.stroke_width)
            else:
                draw.rectangle(bbox, outline=item.color, width=item.stroke_width)
        elif item.type == "circle":
            draw.ellipse(
                (min(item.x1, item.x2), min(item.y1, item.y2), max(item.x1, item.x2), max(item.y1, item.y2)),
                outline=item.color,
                width=item.stroke_width,
            )
        elif item.type == "line":
            draw.line((item.x1, item.y1, item.x2, item.y2), fill=item.color, width=item.stroke_width)
            if item.line_arrow_start:
                _draw_arrow_head(draw, item.x2, item.y2, item.x1, item.y1, item.color, item.stroke_width)
            if item.line_arrow_end:
                _draw_arrow_head(draw, item.x1, item.y1, item.x2, item.y2, item.color, item.stroke_width)

    return rendered.convert("RGB")


def draw_layers(
    image: Image.Image,
    annotations: list[Annotation],
    loupes: LoupeSpec | list[LoupeSpec],
    layer_order: list[str],
) -> Image.Image:
    """Render annotations and loupes in the persisted front-to-back order."""
    if isinstance(loupes, LoupeSpec):
        loupes = [loupes]
    rendered = image
    annotation_by_token = {annotation.layer_token: annotation for annotation in annotations}
    loupe_by_token = {loupe.layer_token: loupe for loupe in loupes}
    order = [
        loupes[0].layer_token if token == "loupe" and loupes else token
        for token in (layer_order or annotation_by_token)
    ]
    # Une loupe visible absente de l'ordre des calques est rendue à l'arrière-plan.
    order.extend(loupe.layer_token for loupe in loupes if loupe.enabled and loupe.layer_token not in order)

    for token in reversed(order):
        if token in loupe_by_token:
            rendered = draw_loupe(rendered, loupe_by_token[token])
        elif token in annotation_by_token:
            rendered = draw_annotations(rendered, [annotation_by_token[token]])
    return rendered


def _draw_arrow_head(
    draw: ImageDraw.ImageDraw,
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    color: str | tuple[int, int, int, int],
    width: int,
) -> None:
    """Draw a compact arrowhead at ``(end_x, end_y)``."""
    angle = math.atan2(end_y - start_y, end_x - start_x)
    length = max(8, width * 4)
    for offset in (math.radians(150), math.radians(-150)):
        draw.line(
            (end_x, end_y, end_x + length * math.cos(angle + offset), end_y + length * math.sin(angle + offset)),
            fill=color,
            width=width,
        )


def _circle_edge_toward(cx: float, cy: float, radius: float, target_x: float, target_y: float) -> tuple[float, float]:
    """Return the point on the circle (``cx``, ``cy``, ``radius``) closest to
    ``(target_x, target_y)``, i.e. where a line from the centre towards the
    target first exits the circle.
    """
    distance = math.hypot(target_x - cx, target_y - cy) or 1.0
    return (cx + (target_x - cx) * radius / distance, cy + (target_y - cy) * radius / distance)


def draw_loupe(image: Image.Image, loupe: LoupeSpec) -> Image.Image:
    """Compose the circular magnifier overlay defined by ``loupe`` onto ``image``."""
    if not loupe.enabled:
        return image

    rendered = image.convert("RGBA")
    overlay = Image.new("RGBA", rendered.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)

    radius = max(10, int(loupe.radius))
    cx, cy = int(loupe.center_x), int(loupe.center_y)
    # The stroke width is defined directly on the recipe (already scaled to
    # the image's own resolution when the recipe was built) so the ring and
    # arrow stay clearly visible after the final export resize.
    stroke_width = max(1, int(loupe.stroke_width))
    outline_color = _hex_to_rgba(loupe.color)

    target_x = loupe.arrow_end_x if loupe.arrow_end_x or loupe.arrow_end_y else loupe.center_x
    target_y = loupe.arrow_end_y if loupe.arrow_end_x or loupe.arrow_end_y else loupe.center_y
    zoom_radius = max(10, int(radius / max(loupe.zoom, 0.01)))
    crop_box = (
        max(0, int(target_x) - zoom_radius),
        max(0, int(target_y) - zoom_radius),
        min(rendered.width, int(target_x) + zoom_radius),
        min(rendered.height, int(target_y) + zoom_radius),
    )
    crop = rendered.crop(crop_box)
    if loupe.rotation:
        # PIL rotates counter-clockwise for positive angles; negate so a
        # positive value matches the clockwise convention used in the UI.
        crop = crop.rotate(-loupe.rotation, resample=Image.Resampling.BICUBIC, expand=False)
    zoomed = crop.resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)

    # Build the circular mask at the exact size of the zoomed patch so that
    # Image.paste receives a mask matching the pasted region, not the full
    # canvas (Pillow requires the mask size to match the source image).
    circle_mask = Image.new("L", (radius * 2, radius * 2), 0)
    ImageDraw.Draw(circle_mask).ellipse((0, 0, radius * 2, radius * 2), fill=255)

    masked = Image.new("RGBA", rendered.size, (0, 0, 0, 0))
    masked.paste(zoomed, (cx - radius, cy - radius), circle_mask)
    # Composite in place: reassigning ``overlay`` here would orphan
    # ``overlay_draw``, silently dropping the ring/arrow drawn below.
    overlay.alpha_composite(masked)

    overlay_draw.ellipse(
        (cx - radius, cy - radius, cx + radius, cy + radius), outline=outline_color, width=stroke_width
    )

    ex, ey = int(loupe.arrow_end_x), int(loupe.arrow_end_y)
    # Start the arrow at the circle's edge (not its stored, pre-drag start
    # point, which sits at the centre) so the shaft never crosses over the
    # magnified disc, matching what the interactive editor shows.
    sx, sy = _circle_edge_toward(cx, cy, radius, ex, ey)
    # L'épaisseur de la flèche est indépendante de l'épaisseur du contour du cercle.
    arrow_width = max(1, int(loupe.arrow_stroke_width))
    overlay_draw.line((sx, sy, ex, ey), fill=outline_color, width=arrow_width)
    _draw_arrow_head(overlay_draw, sx, sy, ex, ey, outline_color, arrow_width)

    return Image.alpha_composite(rendered, overlay).convert("RGB")


def apply_recipe(image: Image.Image, recipe: ProcessingRecipe) -> Image.Image:
    """Apply every step of ``recipe`` to a full-resolution ``image``.

    Steps are applied in a fixed, predictable order: rotation, crop,
    brightness/contrast, annotations, loupe overlay, then final resize. This
    is the single source of truth used both by the interactive preview and
    by the headless/batch script path, guaranteeing identical results.
    """
    processed = image
    if recipe.angle:
        processed = rotate_image(processed, recipe.angle)
    trap = recipe.trapezoid
    if any(abs(v) > 1e-9 for v in trap):
        processed = apply_trapezoid_correction(processed, *trap)
    if recipe.crop is not None:
        x1, y1, x2, y2 = recipe.crop
        processed = processed.crop((int(x1), int(y1), int(x2), int(y2)))
    processed = apply_brightness_contrast(processed, brightness=recipe.brightness, contrast=recipe.contrast)
    processed = draw_layers(processed, recipe.annotations, recipe.loupes, recipe.layer_order)
    processed = resize_with_aspect_ratio(processed, width=recipe.export_width, height=recipe.export_height)
    return processed


def process_image_with_recipe(recipe: ProcessingRecipe, output_path: str | Path) -> Path:
    """Load the recipe's source image at full resolution and export the result.

    This is the entry point for scripting: build (or load from JSON) a
    :class:`ProcessingRecipe`, then call this function to reproduce, on the
    original file, exactly what the user validated on the low-resolution
    preview inside the editor.
    """
    image = load_image(recipe.source_image)
    result = apply_recipe(image, recipe)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    result.save(output, format="JPEG", quality=95)
    return output


if __name__ == "__main__":
    output = process_image(
        "images/raw/IMG_20260720_174638.jpg",
        "images/output/processed_raw.jpg",
        width=1200,
        brightness=10,
        contrast=1.2,
    )
    print(f"Processed image saved to: {output}")

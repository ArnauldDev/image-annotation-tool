"""End-to-end regression test for the reported bug.

Repro (before the fix): reopening an image with a full JSON recipe, then
changing the export width, silently wiped ``annotations``, ``loupes``,
``layer_order`` and reset ``stroke_width`` in the JSON on disk.

Root cause: ``ImageEditorWindow.apply_recipe_to_ui()`` called
``self.width_spin.setValue(...)`` / ``self.height_spin.setValue(...)``
*before* restoring ``self.canvas.annotations`` / ``self.canvas.loupes`` /
``self.layer_order`` / ``self.canvas.current_stroke_width``, and without
blocking signals. That setValue() synchronously fired
``_on_export_width_changed`` / ``_on_export_height_changed``, which call
``auto_save_recipe(force=True)`` -> ``build_recipe()`` -> ``recipe.save()``,
serializing (and permanently persisting) the still-partially-restored, and
therefore incomplete, in-memory state -- overwriting the JSON that was just
loaded.

Requires PyQt6 (``pip install PyQt6``) and runs headless via the
``offscreen`` Qt platform plugin, so it works in CI without a display.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PIL import Image  # noqa: E402

try:
    from iat.image_processor import (  # noqa: E402
        Annotation,
        LoupeSpec,
        ProcessingRecipe,
        compute_associated_paths,
    )
    from iat.qt_image_editor import ImageEditorWindow  # noqa: E402
except ImportError:  # pragma: no cover - fallback for a flat (non-package) layout
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from image_processor import (  # noqa: E402
        Annotation,
        LoupeSpec,
        ProcessingRecipe,
        compute_associated_paths,
    )
    from qt_image_editor import ImageEditorWindow  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app


def _full_recipe(source_image: Path) -> ProcessingRecipe:
    """A recipe exercising every field, mirroring the reported bug's fixture."""
    return ProcessingRecipe(
        source_image=str(source_image),
        angle=0.5,
        brightness=0.0,
        contrast=1.0,
        trapezoid=(0.0, 0.0, 0.0, 0.0),
        crop=(30.7, 61.4, 5658.8, 4018.2),
        export_width=1024,
        export_height=720,
        stroke_width=4,
        annotations=[
            Annotation(type="label", x1=3146.0, y1=1208.4, x2=3227.2, y2=2110.5, text="MCU", color="#ff9500"),
            Annotation(type="line", x1=1607.2, y1=311.1, x2=1607.2, y2=803.7, color="#0a84ff", line_arrow_end=True),
            Annotation(type="line", x1=1472.6, y1=338.1, x2=1472.6, y2=792.3, color="#aa5500", line_arrow_end=True),
        ],
        loupes=[
            LoupeSpec(id=1, enabled=True, center_x=3384.8, center_y=762.4, radius=687.8, zoom=3.6,
                      arrow_end_x=3430.9, arrow_end_y=2321.1, color="#ff3b30", rotation=0.0),
            LoupeSpec(id=2, enabled=True, center_x=785.1, center_y=3189.7, radius=724.0, zoom=1.8,
                      arrow_end_x=985.0, arrow_end_y=2159.1, color="#ffffff", rotation=-180.0),
        ],
        custom_colors=["#aa5500"],
        layer_order=["loupe:2", "annotation:0", "loupe:1", "annotation:1", "annotation:2"],
    )


@pytest.fixture()
def source_image_with_recipe(tmp_path):
    """A real on-disk JPEG plus its matching '-iat.json' full recipe."""
    source_path = tmp_path / "photo-carte-electronique-raw.jpg"
    Image.new("RGB", (6000, 4200), color=(120, 120, 120)).save(source_path, format="JPEG")

    json_path, _ = compute_associated_paths(source_path)
    recipe = _full_recipe(source_path)
    recipe.save(json_path)
    return source_path, json_path, recipe


def test_reopening_image_then_resizing_export_preserves_full_recipe(qapp, source_image_with_recipe):
    """Load JSON -> change export width -> save -> reread -> assert nothing lost."""
    source_path, json_path, original_recipe = source_image_with_recipe

    window = ImageEditorWindow()
    try:
        window.load_source_image(source_path)

        # The JSON must have been fully restored into memory on load.
        assert len(window.canvas.annotations) == 3
        assert len(window.canvas.loupes) == 2
        assert window.layer_order == original_recipe.layer_order
        assert window.canvas.current_stroke_width == 4

        # User resizes the export -- this used to trigger a premature,
        # partial auto-save (see module docstring).
        window.width_spin.setValue(900)

        reloaded = ProcessingRecipe.load(json_path)
        assert reloaded.export_width == 900
        assert len(reloaded.annotations) == 3
        assert len(reloaded.loupes) == 2
        assert reloaded.layer_order == original_recipe.layer_order
        assert reloaded.stroke_width == 4
        assert reloaded.custom_colors == ["#aa5500"]
        assert reloaded.crop == original_recipe.crop
        assert reloaded.angle == original_recipe.angle
    finally:
        window.close()
        window.deleteLater()


def test_reopening_image_then_moving_annotation_preserves_full_recipe(qapp, source_image_with_recipe):
    """Load JSON -> move an annotation -> save -> reread -> assert nothing lost."""
    source_path, json_path, original_recipe = source_image_with_recipe

    window = ImageEditorWindow()
    try:
        window.load_source_image(source_path)
        assert len(window.canvas.annotations) == 3

        # "Move an object": drag the first annotation by (10, 10) in preview
        # space, then trigger the same persistence path the canvas uses.
        item = window.canvas.annotations[0]
        item.start.setX(item.start.x() + 10)
        item.start.setY(item.start.y() + 10)
        window.auto_save_recipe(force=True)

        reloaded = ProcessingRecipe.load(json_path)
        assert len(reloaded.annotations) == 3
        assert len(reloaded.loupes) == 2
        assert reloaded.layer_order == original_recipe.layer_order
        assert reloaded.stroke_width == 4
        assert reloaded.export_width == original_recipe.export_width
        assert reloaded.export_height == original_recipe.export_height
    finally:
        window.close()
        window.deleteLater()


def test_load_recipe_menu_action_also_restores_before_any_export_signal(qapp, source_image_with_recipe, monkeypatch):
    """The "Charger une recette" action goes through the same apply_recipe_to_ui
    path as load_source_image and must be equally safe."""
    from PyQt6.QtWidgets import QFileDialog

    source_path, json_path, original_recipe = source_image_with_recipe

    window = ImageEditorWindow()
    try:
        monkeypatch.setattr(
            QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(json_path), "JSON (*.json)"))
        )
        window.load_recipe()

        reloaded = ProcessingRecipe.load(json_path)
        assert len(reloaded.annotations) == 3
        assert len(reloaded.loupes) == 2
        assert reloaded.layer_order == original_recipe.layer_order
        assert reloaded.stroke_width == 4
    finally:
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

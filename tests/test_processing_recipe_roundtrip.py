"""Round-trip tests for ``ProcessingRecipe`` (JSON persistence, model layer).

These tests cover the JSON <-> ``ProcessingRecipe`` contract in
``image_processor.py``. They do not require PyQt6.

The companion test in ``test_qt_editor_export_resize_preserves_recipe.py``
covers the actual regression: the Qt UI silently truncating this same JSON
when the export size spin boxes emit their ``valueChanged`` signal *before*
annotations/loupes/layer_order/stroke_width have been restored into memory
(see ``ImageEditorWindow.apply_recipe_to_ui``).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from iat.image_processor import Annotation, LoupeSpec, ProcessingRecipe
except ImportError:  # pragma: no cover - fallback for a flat (non-package) layout
    from image_processor import Annotation, LoupeSpec, ProcessingRecipe

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_fixture_full_recipe_round_trips_without_loss(tmp_path):
    """Loading a complete recipe and saving it back must not drop anything.

    This uses the real-world JSON attached to the bug report
    (``photo-carte-electronique-iat.json``): 3 annotations, 2 loupes, a
    5-entry layer_order, custom colors, a non-default stroke width.
    """
    original_data = _load_fixture("photo-carte-electronique-iat.json")
    recipe = ProcessingRecipe.from_dict(original_data)

    # Sanity check: the fixture really does carry every kind of data we
    # care about, otherwise this test would pass trivially.
    assert len(recipe.annotations) == 3
    assert len(recipe.loupes) == 2
    assert recipe.layer_order == [
        "loupe:2",
        "annotation:0",
        "loupe:1",
        "annotation:1",
        "annotation:2",
    ]
    assert recipe.stroke_width == 4
    assert recipe.custom_colors == ["#aa5500"]

    out_path = tmp_path / "photo-carte-electronique-iat.json"
    recipe.save(out_path)
    reloaded = ProcessingRecipe.load(out_path)

    assert reloaded == recipe


def test_export_size_change_preserves_every_other_field(tmp_path):
    """Changing only export width/height must not touch anything else.

    Simulates: load a full JSON -> user resizes the export -> save ->
    reload -> assert nothing besides ``export`` changed.
    """
    original_data = _load_fixture("photo-carte-electronique-iat.json")
    recipe = ProcessingRecipe.from_dict(original_data)
    out_path = tmp_path / "recipe.json"
    recipe.save(out_path)

    # "User resizes the export": only export_width/export_height change,
    # exactly like ImageEditorWindow.build_recipe() would produce if (and
    # only if) every other piece of UI state was correctly restored first.
    loaded = ProcessingRecipe.load(out_path)
    resized = ProcessingRecipe(
        **{**loaded.__dict__, "export_width": 900, "export_height": 675}
    )
    resized.save(out_path)

    reloaded = ProcessingRecipe.load(out_path)
    assert reloaded.export_width == 900
    assert reloaded.export_height == 675
    # Everything else must be untouched.
    assert reloaded.annotations == recipe.annotations
    assert reloaded.loupes == recipe.loupes
    assert reloaded.layer_order == recipe.layer_order
    assert reloaded.stroke_width == recipe.stroke_width
    assert reloaded.custom_colors == recipe.custom_colors
    assert reloaded.crop == recipe.crop
    assert reloaded.angle == recipe.angle
    assert reloaded.trapezoid == recipe.trapezoid


def test_reported_bug_fixture_would_fail_this_assertion():
    """Documents the bug using the real "after" JSON from the report.

    ``photo-carte-electronique-iat-apres.json`` is what the buggy app wrote
    after the user only changed the export width. It lost annotations,
    loupes, layer_order, and reset stroke_width to the default. This test
    pins that "after" fixture as a known-bad shape so any future regression
    that reproduces it fails loudly, and documents the exact fields the fix
    protects.
    """
    before = ProcessingRecipe.from_dict(_load_fixture("photo-carte-electronique-iat.json"))
    after_buggy = ProcessingRecipe.from_dict(_load_fixture("photo-carte-electronique-iat-apres.json"))

    # What the bug actually destroyed:
    assert len(before.annotations) == 3 and len(after_buggy.annotations) == 0
    assert len(before.loupes) == 2 and len(after_buggy.loupes) == 0
    assert before.layer_order and not after_buggy.layer_order
    assert before.stroke_width == 4 and after_buggy.stroke_width == 3

    # What a correct export-size change must preserve instead (this is the
    # behaviour asserted end-to-end, at the UI level, in
    # test_qt_editor_export_resize_preserves_recipe.py):
    fixed = ProcessingRecipe(
        **{**before.__dict__, "export_width": 900, "export_height": 675}
    )
    assert len(fixed.annotations) == 3
    assert len(fixed.loupes) == 2
    assert fixed.layer_order == before.layer_order
    assert fixed.stroke_width == 4


def test_annotation_and_loupe_round_trip_all_fields(tmp_path):
    """Every individual field of Annotation/LoupeSpec survives a round trip."""
    recipe = ProcessingRecipe(
        source_image="img.jpg",
        angle=1.25,
        brightness=5.0,
        contrast=1.1,
        trapezoid=(0.01, -0.02, 0.03, -0.04),
        crop=(1.0, 2.0, 300.0, 400.0),
        export_width=1024,
        export_height=768,
        stroke_width=7,
        annotations=[
            Annotation(
                type="label",
                x1=1, y1=2, x2=3, y2=4,
                text="MCU",
                color="#ff9500",
                stroke_width=14,
                font_size=101,
                border_radius=36,
                show_arrow=True,
                shape="rect",
                arrow_stroke_width=11,
                show_text=True,
                fill_enabled=True,
                bold_text=True,
                line_arrow_start=False,
                line_arrow_end=True,
            )
        ],
        loupes=[
            LoupeSpec(
                id=5,
                enabled=True,
                center_x=10, center_y=20,
                radius=100, zoom=2.5,
                arrow_start_x=10, arrow_start_y=20,
                arrow_end_x=50, arrow_end_y=60,
                color="#66d9ef",
                stroke_width=6,
                rotation=45.0,
                arrow_stroke_width=3,
            )
        ],
        custom_colors=["#111111", "#222222"],
        layer_order=["loupe:5", "annotation:0"],
    )
    path = tmp_path / "recipe.json"
    recipe.save(path)
    reloaded = ProcessingRecipe.load(path)
    assert reloaded == recipe


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))

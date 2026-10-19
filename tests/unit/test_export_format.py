#!/usr/bin/env python3
"""
  File Name: test_export_format.py
  Description: Tests TASK-019 : choix du format d'export (JPEG ou TIFF) depuis le
               panneau « Exporter l'image ». Sélection exclusive sans checkbox
               (rendu actif / repos), persistance dans le JSON, export TIFF sans
               perte et rétrocompatibilité des anciennes recettes.
  Developer: ArnauldDev
  Created Date: 2026-10-19
  Last Modified: 2026-10-19
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication

import iat.qt_image_editor as editor
from iat.image_processor import (
    ProcessingRecipe,
    compute_associated_paths,
    normalize_export_format,
    process_image_with_recipe,
)
from iat.qt_image_editor import ImageEditorWindow, translator


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    return app


@pytest.fixture(autouse=True)
def french_interface():
    """Every test starts (and ends) with the French source texts."""
    translator.set_language(editor.SOURCE_LANGUAGE, editor._TRANSLATIONS_DIRECTORY)
    yield
    translator.set_language(editor.SOURCE_LANGUAGE, editor._TRANSLATIONS_DIRECTORY)


@pytest.fixture
def window(qapp, tmp_path):
    """Une image source 400x300 (le plafond d'export devient 400x300)."""
    raw_path = tmp_path / "carte-raw.jpg"
    Image.new("RGB", (400, 300), color="white").save(raw_path, format="JPEG")
    win = ImageEditorWindow()
    win.load_source_image(raw_path)
    yield win
    win.close()


# ---------------------------------------------------------------------------
# Modèle de recette (JSON)
# ---------------------------------------------------------------------------
def test_recipe_defaults_to_jpeg():
    assert ProcessingRecipe().export_format == "jpeg"
    assert ProcessingRecipe().to_dict()["export"]["format"] == "jpeg"


def test_recipe_round_trip_preserves_format():
    recipe = ProcessingRecipe(source_image="x.jpg", export_format="tiff")
    assert ProcessingRecipe.from_json(recipe.to_json()).export_format == "tiff"


def test_legacy_recipe_without_format_loads_as_jpeg():
    data = {"source_image": "old.jpg", "export": {"width": 800, "height": 600}}
    recipe = ProcessingRecipe.from_dict(data)
    assert recipe.export_format == "jpeg"
    assert recipe.export_width == 800


@pytest.mark.parametrize(
    "value,expected",
    [
        ("jpg", "jpeg"),
        ("JPG", "jpeg"),
        ("jpeg", "jpeg"),
        ("JPEG", "jpeg"),
        ("tif", "tiff"),
        ("TIFF", "tiff"),
        ("  tiff  ", "tiff"),
        ("", "jpeg"),
        (None, "jpeg"),
        ("bmp", "jpeg"),
    ],
)
def test_normalize_export_format(value, expected):
    assert normalize_export_format(value) == expected


def test_compute_associated_paths_follows_export_format():
    base = Path("images/photo-raw.jpg")
    _, jpg_path = compute_associated_paths(base, export_width=1400)
    _, tif_path = compute_associated_paths(base, export_width=1400, export_format="tiff")
    assert jpg_path.name == "photo-iat-x1400.jpg"
    assert tif_path.name == "photo-iat-x1400.tif"
    # Sans largeur d'export ni format, le comportement historique est conservé.
    _, default_path = compute_associated_paths(base)
    assert default_path.name == "photo-iat.jpg"


# ---------------------------------------------------------------------------
# Moteur d'export
# ---------------------------------------------------------------------------
def test_export_writes_tiff_without_loss(tmp_path):
    source = tmp_path / "src.jpg"
    Image.new("RGB", (120, 90), color=(10, 20, 30)).save(source, format="JPEG")
    recipe = ProcessingRecipe(
        source_image=str(source), export_width=120, export_height=90, export_format="tiff"
    )
    output = process_image_with_recipe(recipe, tmp_path / "out.tif")
    with Image.open(output) as exported:
        assert exported.format == "TIFF"
        assert exported.size == (120, 90)


def test_export_defaults_to_jpeg(tmp_path):
    source = tmp_path / "src.jpg"
    Image.new("RGB", (100, 80), color="grey").save(source, format="JPEG")
    recipe = ProcessingRecipe(source_image=str(source), export_width=100, export_height=80)
    output = process_image_with_recipe(recipe, tmp_path / "out.jpg")
    with Image.open(output) as exported:
        assert exported.format == "JPEG"


# ---------------------------------------------------------------------------
# Interface : sélection exclusive sans checkbox, état actif / repos
# ---------------------------------------------------------------------------
def test_new_image_defaults_to_jpeg(window):
    assert window.export_format == "jpeg"
    jpeg_button = window.export_format_buttons["jpeg"]
    tiff_button = window.export_format_buttons["tiff"]
    assert jpeg_button.property("exportFormatActive") == "true"
    assert tiff_button.property("exportFormatActive") == "false"
    # Aucun état coché : les deux boutons restent cliquables.
    assert not jpeg_button.isCheckable()
    assert not tiff_button.isCheckable()
    assert jpeg_button.isEnabled()
    assert tiff_button.isEnabled()


def test_switching_format_is_exclusive_and_saved(window):
    window._apply_export_format("tiff")
    assert window.export_format == "tiff"
    assert window.export_format_buttons["tiff"].property("exportFormatActive") == "true"
    assert window.export_format_buttons["jpeg"].property("exportFormatActive") == "false"
    # Les deux boutons restent cliquables pour permettre de revenir en arrière.
    assert window.export_format_buttons["jpeg"].isEnabled()
    # Le nom d'export proposé suit la nouvelle extension.
    assert window.default_export_path.suffix == ".tif"
    # Le JSON auto-sauvegardé contient le format sélectionné.
    assert window.current_json_path.exists()
    assert ProcessingRecipe.load(window.current_json_path).export_format == "tiff"


def test_format_is_restored_from_recipe(qapp, tmp_path):
    raw_path = tmp_path / "carte-raw.jpg"
    Image.new("RGB", (400, 300), color="white").save(raw_path, format="JPEG")

    first = ImageEditorWindow()
    first.load_source_image(raw_path)
    first._apply_export_format("tiff")
    first.close()

    # Réouverture de la même image : le format est restauré depuis le JSON.
    second = ImageEditorWindow()
    second.load_source_image(raw_path)
    try:
        assert second.export_format == "tiff"
        assert second.export_format_buttons["tiff"].property("exportFormatActive") == "true"
        assert second.default_export_path.suffix == ".tif"
    finally:
        second.close()


def test_new_image_resets_format_to_jpeg(qapp, tmp_path):
    tiff_source = tmp_path / "premiere-raw.jpg"
    Image.new("RGB", (400, 300), color="white").save(tiff_source, format="JPEG")
    other_source = tmp_path / "seconde-raw.jpg"
    Image.new("RGB", (400, 300), color="black").save(other_source, format="JPEG")

    window = ImageEditorWindow()
    window.load_source_image(tiff_source)
    window._apply_export_format("tiff")
    # Une nouvelle image (sans JSON associé) repart toujours en JPEG.
    window.load_source_image(other_source)
    try:
        assert window.export_format == "jpeg"
        assert window.export_format_buttons["jpeg"].property("exportFormatActive") == "true"
        assert window.default_export_path.suffix == ".jpg"
    finally:
        window.close()

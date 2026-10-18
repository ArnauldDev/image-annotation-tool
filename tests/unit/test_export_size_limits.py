#!/usr/bin/env python3
"""
  File Name: test_export_size_limits.py
  Description: Tests TASK-018 : la taille d'export ne peut pas dépasser celle de
               l'image source. Bornes appliquées au chargement, erreur modale à la
               saisie et aux préréglages, reclamp silencieux d'un ancien JSON et
               contrôle que le JPEG exporté reste dans les dimensions de la source.
  Developer: ArnauldDev
  Created Date: 2026-10-19
  Last Modified: 2026-10-19
"""

from __future__ import annotations

import pytest
from PIL import Image
from PyQt6.QtWidgets import QApplication

import iat.qt_image_editor as editor
from iat.image_processor import (
    Annotation,
    ProcessingRecipe,
    compute_associated_paths,
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


@pytest.fixture
def warnings(monkeypatch):
    """Capture les erreurs modales sans bloquer (QMessageBox.warning est modal)."""
    recorded = []
    monkeypatch.setattr(editor.QMessageBox, "warning", lambda *args, **kwargs: recorded.append(args))
    return recorded


# ---------------------------------------------------------------------------
# Plafonds suivant la taille de l'image source
# ---------------------------------------------------------------------------
def test_export_limits_follow_the_source_image_size(window):
    assert window._export_max_width() == 400
    assert window._export_max_height() == 300
    # Les valeurs par défaut (1200x800) ont été reclampées au chargement.
    assert window.width_spin.value() == 400
    assert window.height_spin.value() == 300
    # Le nom d'export proposé reflète bien la largeur réelle.
    assert "-x400" in window.default_export_path.name


def test_without_image_the_historical_limits_still_apply(qapp, warnings):
    window = ImageEditorWindow()
    try:
        assert window._export_max_width() == 20000
        assert window._export_max_height() == 20000
        # Un préréglage reste applicable tant qu'aucune image n'est chargée.
        window.export_preset_buttons[1920].click()
        assert window.width_spin.value() == 1920
        assert warnings == []
    finally:
        window.close()


# ---------------------------------------------------------------------------
# Saisie trop grande -> message d'erreur modal + recalage
# ---------------------------------------------------------------------------
def test_typing_a_larger_width_shows_a_modal_error_and_clamps(window, warnings):
    window.width_spin.setValue(5000)

    assert len(warnings) == 1
    assert "400 px" in warnings[0][2]
    assert window.width_spin.value() == 400
    # La hauteur dérivée reste proportionnelle et dans les bornes.
    assert window.height_spin.value() == 300


def test_typing_a_larger_height_shows_a_modal_error_and_clamps(window, warnings):
    window.height_spin.setValue(2000)

    assert len(warnings) == 1
    assert "300 px" in warnings[0][2]
    assert window.height_spin.value() == 300
    assert window.width_spin.value() <= 400


def test_valid_sizes_stay_silent(window, warnings):
    window.width_spin.setValue(320)

    assert warnings == []
    assert window.width_spin.value() == 320
    assert window.height_spin.value() == 240  # proportions 4:3 conservées


# ---------------------------------------------------------------------------
# Préréglage plus large que la source -> message d'erreur modal
# ---------------------------------------------------------------------------
def test_preset_larger_than_source_is_rejected_with_a_modal_error(window, warnings):
    window.export_preset_buttons[1920].click()

    assert len(warnings) == 1
    assert "400 px" in warnings[0][2]
    assert window.width_spin.value() == 400
    # Le clic a basculé le bouton : l'affichage doit rester synchronisé.
    assert not window.export_preset_buttons[1920].isChecked()
    assert "400 px" in window.statusBar().currentMessage()


def test_preset_within_source_size_is_applied(qapp, tmp_path, warnings):
    raw_path = tmp_path / "grande-raw.jpg"
    Image.new("RGB", (2400, 1800), color="white").save(raw_path, format="JPEG")
    window = ImageEditorWindow()
    try:
        window.load_source_image(raw_path)
        window.export_preset_buttons[1920].click()
        assert warnings == []
        assert window.width_spin.value() == 1920
        assert window.height_spin.value() == 1440  # proportions 4:3 conservées
        assert window.export_preset_buttons[1920].isChecked()
    finally:
        window.close()


# ---------------------------------------------------------------------------
# Ancien JSON porte-à-soutenir : reclamp silencieux, aucune perte de données
# ---------------------------------------------------------------------------
def test_oversized_recipe_export_is_clamped_silently_on_load(qapp, tmp_path, warnings):
    raw_path = tmp_path / "ancienne-raw.jpg"
    Image.new("RGB", (400, 300), color="white").save(raw_path, format="JPEG")
    json_path, _ = compute_associated_paths(raw_path)
    ProcessingRecipe(
        source_image=str(raw_path),
        export_width=4000,
        export_height=3000,
        annotations=[Annotation(type="rect", x1=10, y1=10, x2=80, y2=60, stroke_width=3, color="#FF0000")],
        layer_order=["annotation:1"],
    ).save(json_path)

    window = ImageEditorWindow()
    try:
        window.load_source_image(raw_path)

        # Pas de modal à l'ouverture d'un fichier : ce n'est pas une saisie.
        assert warnings == []
        assert window.width_spin.value() == 400
        assert window.height_spin.value() == 300
        assert len(window.canvas.annotations) == 1

        # Le JSON n'est pas réécrit au chargement.
        assert ProcessingRecipe.load(json_path).export_width == 4000

        # Le premier changement utilisateur sauvegarde l'état complet avec la
        # valeur contrainte (régression TASK-004 : rien d'autre n'est perdu).
        window.width_spin.setValue(350)
        reloaded = ProcessingRecipe.load(json_path)
        assert reloaded.export_width == 350
        assert reloaded.export_height == window.height_spin.value()
        assert reloaded.export_height <= 300
        assert len(reloaded.annotations) == 1
        assert reloaded.annotations[0].stroke_width == 3
    finally:
        window.close()


# ---------------------------------------------------------------------------
# Contrôle de bout en bout : le JPEG final reste dans la source
# ---------------------------------------------------------------------------
def test_exported_jpeg_never_exceeds_the_source_image(window, tmp_path, monkeypatch, warnings):
    target = tmp_path / "export.jpg"
    monkeypatch.setattr(editor.QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), ""))
    monkeypatch.setattr(editor.QMessageBox, "information", lambda *args, **kwargs: None)

    window.width_spin.setValue(5000)  # rejeté -> 400 px
    window.export_image()

    assert warnings != []  # la tentative a bien été signalée
    with Image.open(target) as exported:
        assert exported.size == (400, 300)

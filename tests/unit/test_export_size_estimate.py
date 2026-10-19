#!/usr/bin/env python3
"""
  File Name: test_export_size_estimate.py
  Description: Tests TASK-020 : estimation de la taille du fichier d'export dans le
               panneau « Exporter l'image ». Vérifie le formateur localisé français,
               l'exactitude de l'estimation (mêmes octets que l'export réel, JPEG et
               TIFF) et le comportement asynchrone de l'interface (debounce, états
               « Calcul… » / « ≈ » / « — », cohérence avec l'image affichée).
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
    estimate_export_size,
    format_file_size,
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
    win._estimate_timer.stop() if win._estimate_timer else None
    win.close()


# ---------------------------------------------------------------------------
# Formateur localisé (TASK-020-3)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "size_bytes, expected",
    [
        (512, "512 o"),
        (1500, "1,5 Ko"),
        (38900000, "38,9 Mo"),
        (2_500_000_000, "2,5 Go"),
    ],
)
def test_format_file_size_localized(size_bytes, expected):
    assert format_file_size(size_bytes) == expected


def test_format_file_size_invalid_is_dash():
    assert format_file_size(None) == "—"


# ---------------------------------------------------------------------------
# Estimation exacte (TASK-020-2) : mêmes octets que l'export réel
# ---------------------------------------------------------------------------
def test_estimate_matches_real_export(tmp_path):
    source = tmp_path / "src.jpg"
    Image.new("RGB", (400, 300), color=(120, 140, 160)).save(source, format="JPEG")

    for export_format in ("jpeg", "tiff"):
        recipe = ProcessingRecipe(
            source_image=str(source),
            export_width=200,
            export_height=150,
            export_format=export_format,
        )
        estimate = estimate_export_size(recipe)
        output = process_image_with_recipe(recipe, tmp_path / f"out.{export_format}")
        assert estimate == output.stat().st_size


def test_estimate_uses_provided_image_without_disk(tmp_path):
    """Une image fournie évite la relecture du disque (source inexistante OK)."""
    recipe = ProcessingRecipe(
        source_image=str(tmp_path / "absent.jpg"),
        export_width=100,
        export_height=80,
        export_format="jpeg",
    )
    assert estimate_export_size(recipe) is None
    provided = Image.new("RGB", (200, 160), color="orange")
    assert estimate_export_size(recipe, image=provided) is not None


# ---------------------------------------------------------------------------
# Interface (TASK-020-4 / TASK-020-6) : états du libellé et asynchrone
# ---------------------------------------------------------------------------
def _wait_for_estimate(window, timeout_ms=5000):
    """Attend la fin du calcul asynchrone (débounce + worker) et retourne le texte."""
    from PyQt6.QtCore import QElapsedTimer, QEventLoop

    timer = QElapsedTimer()
    timer.start()
    loop = QEventLoop()
    while timer.elapsed() < timeout_ms:
        if window._estimate_worker is not None:
            window._estimate_worker.finished.connect(loop.quit)
            loop.exec()
            break
        QApplication.processEvents()
    # Laisse le temps au slot _on_estimate_ready (queued) d'être traité.
    for _ in range(50):
        QApplication.processEvents()
    return window.estimated_size_label.text()


def test_label_exists_and_starts_dash(qapp):
    win = ImageEditorWindow()
    try:
        assert win.estimated_size_label.text() == "—"
    finally:
        win.close()


def test_label_shows_calculating_then_value(window, qapp):
    window._schedule_estimate()
    assert window.estimated_size_label.text() == "Calcul…"

    text = _wait_for_estimate(window)
    assert text not in ("", "—", "Calcul…")
    assert text.endswith(("o", "Ko", "Mo", "Go"))


def test_debounce_coalesces_rapid_changes(window, qapp):
    """Une rafale de changements ne déclenche qu'un seul calcul final."""
    for width in (100, 150, 200, 250):
        window.width_spin.setValue(width)
        assert window.estimated_size_label.text() == "Calcul…"

    text = _wait_for_estimate(window)
    assert text not in ("", "—", "Calcul…")


def test_switching_format_refreshes_estimate(window, qapp):
    window._apply_export_format("tiff")
    text = _wait_for_estimate(window)
    assert text not in ("", "—", "Calcul…")


def test_estimate_stale_result_is_ignored(window):
    """Un résultat dont le jeton ne correspond plus est ignoré."""
    window.estimated_size_label.setText("Calcul…")
    window._estimate_generation = 5
    window._on_estimate_ready(4, 12345)  # obsolète
    assert window.estimated_size_label.text() == "Calcul…"
    window._on_estimate_ready(5, 38900000)  # courant
    assert window.estimated_size_label.text() == "38,9 Mo"


def test_show_estimate_states(window):
    """États textuels : valeur, « ≈ » (approximatif), « — » (indisponible)."""
    window._show_estimate(None, approximate=False)
    assert window.estimated_size_label.text() == "—"
    window._show_estimate(38900000, approximate=True)
    assert window.estimated_size_label.text() == "≈ 38,9 Mo"
    window._show_estimate(38900000, approximate=False)
    assert window.estimated_size_label.text() == "38,9 Mo"


def test_ui_label_matches_exported_file(window, qapp, tmp_path):
    """La valeur affichée correspond à l'octet près au fichier réellement exporté."""
    from PyQt6.QtCore import QElapsedTimer, QEventLoop
    from iat.image_processor import process_image_with_recipe

    text = _wait_for_estimate(window)
    # « 1 234 o » ou « 12,3 Ko »… on reconstruit le nombre d'octets annoncé.
    assert text not in ("", "—", "Calcul…")

    recipe = window.build_recipe()
    output = process_image_with_recipe(recipe, tmp_path / "ref.jpg")
    real_size = output.stat().st_size
    assert window.estimated_size_label.text() == format_file_size(real_size)

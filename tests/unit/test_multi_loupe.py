#!/usr/bin/env python3
"""
  File Name: test_multi_loupe.py
  Description: Tests des loupes multiples (identifiants, JSON, rendu) et de la sauvegarde
               en direct de l'épaisseur du contour d'une loupe.
  Developer: ArnauldDev
  Created Date: 2026-09-23
"""

from __future__ import annotations

import json

import pytest
from PIL import Image
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import QApplication

from iat.image_processor import LoupeSpec, ProcessingRecipe, draw_layers, next_loupe_id
from iat.qt_image_editor import ImageEditorWindow, LoupeOverlay, TOOL_LOUPE


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _window_with_image(tmp_path, size=(400, 300), name="board-raw.jpg") -> ImageEditorWindow:
    raw_path = tmp_path / name
    Image.new("RGB", size, color="white").save(raw_path)
    window = ImageEditorWindow()
    window.load_source_image(raw_path)
    return window


# ---------------------------------------------------------------------------
# Moteur : recette JSON
# ---------------------------------------------------------------------------
def test_recipe_serializes_several_loupes_with_ids_and_layer_tokens():
    recipe = ProcessingRecipe(
        loupes=[LoupeSpec(id=1, enabled=True), LoupeSpec(id=2, enabled=True, zoom=3.0)],
        layer_order=["loupe:2", "loupe:1"],
    )

    data = json.loads(recipe.to_json())
    assert [loupe["id"] for loupe in data["loupes"]] == [1, 2]
    assert "loupe" not in data

    reloaded = ProcessingRecipe.from_json(recipe.to_json())
    assert [loupe.id for loupe in reloaded.loupes] == [1, 2]
    assert reloaded.loupes[1].zoom == 3.0
    assert reloaded.layer_order == ["loupe:2", "loupe:1"]


def test_legacy_single_loupe_json_is_upgraded_to_loupe_1():
    legacy = {
        "annotations": [{"type": "rect"}],
        "loupe": {"enabled": True, "center_x": 10, "stroke_width": 7},
        "layer_order": ["loupe", "annotation:0"],
    }

    recipe = ProcessingRecipe.from_dict(legacy)

    assert len(recipe.loupes) == 1
    assert recipe.loupes[0].id == 1
    assert recipe.loupes[0].stroke_width == 7
    assert recipe.layer_order == ["loupe:1", "annotation:0"]
    assert recipe.loupe is recipe.loupes[0]


def test_legacy_unused_loupe_object_does_not_create_a_loupe():
    assert ProcessingRecipe.from_dict({"loupe": {}}).loupes == []


def test_duplicated_or_missing_loupe_ids_are_renumbered():
    recipe = ProcessingRecipe.from_dict({"loupes": [{"id": 3}, {"id": 3}, {}]})

    ids = [loupe.id for loupe in recipe.loupes]
    assert len(set(ids)) == 3
    assert ids[0] == 3


def test_next_loupe_id_increments_the_highest_identifier():
    assert next_loupe_id([]) == 1
    assert next_loupe_id([LoupeSpec(id=1), LoupeSpec(id=4)]) == 5


def test_draw_layers_renders_every_visible_loupe():
    image = Image.new("RGB", (200, 100), color="white")
    left = LoupeSpec(id=1, enabled=True, center_x=40, center_y=50, radius=20, color="#FF0000", stroke_width=3,
                     arrow_end_x=40, arrow_end_y=50)
    right = LoupeSpec(id=2, enabled=True, center_x=160, center_y=50, radius=20, color="#0000FF", stroke_width=3,
                      arrow_end_x=160, arrow_end_y=50)

    rendered = draw_layers(image, [], [left, right], ["loupe:1", "loupe:2"])

    assert rendered.getpixel((40, 31))[0] > 200  # anneau rouge de la loupe 1
    assert rendered.getpixel((160, 31))[2] > 200  # anneau bleu de la loupe 2


# ---------------------------------------------------------------------------
# Interface : création et sélection de loupes
# ---------------------------------------------------------------------------
def test_new_loupe_button_creates_loupes_with_incremented_ids(qapp, tmp_path):
    window = _window_with_image(tmp_path)

    assert window.new_loupe_button.isEnabled()
    window.new_loupe_button.click()
    window.new_loupe_button.click()

    assert [loupe.id for loupe in window.canvas.loupes] == [1, 2]
    assert window.canvas.tool == TOOL_LOUPE
    assert window.canvas.selected_item is window.canvas.loupes[1]
    assert window.current_loupe_label.text() == "Loupe #2"
    # La nouvelle loupe est placée au premier plan de la liste des calques.
    assert window.layer_order[0] == "loupe:2"
    saved = ProcessingRecipe.load(window.current_json_path)
    assert [loupe.id for loupe in saved.loupes] == [1, 2]
    assert set(saved.layer_order) == {"loupe:1", "loupe:2"}


def test_loupe_panel_controls_follow_the_selected_loupe(qapp, tmp_path):
    window = _window_with_image(tmp_path)
    first = window.create_new_loupe()
    second = window.create_new_loupe()
    first.zoom, second.zoom = 2.0, 5.0
    window.refresh_objects_list()

    window.canvas.item_selected.emit(first)
    assert window.loupe_zoom_spin.value() == 2.0
    window.loupe_zoom_spin.setValue(3.0)
    assert first.zoom == 3.0 and second.zoom == 5.0

    window.canvas.item_selected.emit(second)
    assert window.loupe_zoom_spin.value() == 5.0


def test_deleting_one_loupe_keeps_the_others(qapp, tmp_path):
    window = _window_with_image(tmp_path)
    first = window.create_new_loupe()
    second = window.create_new_loupe()

    window._select_payload_in_list(first)
    window.delete_selected_object()

    assert window.canvas.loupes == [second]
    assert "loupe:1" not in window.layer_order
    assert [loupe.id for loupe in ProcessingRecipe.load(window.current_json_path).loupes] == [2]
    # L'identifiant suivant reste unique même après une suppression.
    assert window.create_new_loupe().id == 3


def test_multi_loupe_feature_flag_hides_the_new_loupe_button(qapp, tmp_path, monkeypatch):
    from iat.config import config

    monkeypatch.setattr(config, "feature_multi_loupe", False)
    window = _window_with_image(tmp_path)

    assert window.new_loupe_button.isHidden()
    assert window.create_new_loupe() is not None  # la première loupe reste possible
    assert window.create_new_loupe() is None


def test_dragging_in_empty_area_with_loupe_tool_creates_a_loupe_when_none_is_selected(qapp, tmp_path):
    window = _window_with_image(tmp_path)
    window.select_tool(TOOL_LOUPE)
    window.canvas.selected_item = None

    loupe = window.canvas.add_loupe(QPointF(50, 50))

    assert isinstance(loupe, LoupeOverlay) and loupe.id == 1
    assert window.canvas.add_loupe(QPointF(80, 80)).id == 2


# ---------------------------------------------------------------------------
# Bug : épaisseur du contour de la loupe mal sauvegardée en direct
# ---------------------------------------------------------------------------
def test_loupe_stroke_width_is_saved_live_and_round_trips(qapp, tmp_path):
    # Image plus grande que l'aperçu (1600 px) : facteur d'échelle 2.
    window = _window_with_image(tmp_path, size=(3200, 2400), name="big-raw.jpg")
    assert window.preview_scale == pytest.approx(2.0)
    loupe = window.create_new_loupe()

    window.loupe_stroke_width_spin.setValue(7)

    assert loupe.stroke_width == 7
    saved = ProcessingRecipe.load(window.current_json_path)
    assert saved.loupes[0].stroke_width == 14  # 7 px d'aperçu × 2

    reloaded = ImageEditorWindow()
    reloaded.load_source_image(window.source_path)
    reloaded.select_tool(TOOL_LOUPE)
    # Le panneau affiche la valeur d'aperçu, pas la valeur pleine résolution du
    # JSON (qui saturait la borne du champ et bloquait son bouton « + »).
    assert reloaded.loupe_stroke_width_spin.value() == 7
    assert reloaded.loupe_radius_spin.value() == loupe.radius
    reloaded.loupe_stroke_width_spin.setValue(8)
    assert ProcessingRecipe.load(window.current_json_path).loupes[0].stroke_width == 16

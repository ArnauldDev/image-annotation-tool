#!/usr/bin/env python3
"""
  File Name: test_circle_numbering.py
  Description: Tests du mode « Numérotation » de l'outil Cercle : compteur sérialisé
               dans la recette JSON, placement par simple clic, activation de
               l'interface selon l'outil, bouton RAZ et rendu (aperçu + export).
  Developer: ArnauldDev
  Created Date: 2026-10-18
"""

from __future__ import annotations

import json
import math

import pytest
from PIL import Image
from PyQt6.QtCore import QEvent, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QImage, QMouseEvent, QPainter
from PyQt6.QtWidgets import QApplication

import iat.qt_image_editor as editor
from iat.image_processor import LABEL_BACKGROUND_RGB, Annotation, ProcessingRecipe, draw_annotations
from iat.qt_image_editor import (
    DEFAULT_NUMBERED_CIRCLE_DIAMETER,
    AnnotationItem,
    ImageCanvas,
    ImageEditorWindow,
    TOOL_CIRCLE,
    TOOL_LINE,
    TOOL_RECT,
    TOOL_TEXT,
    translator,
)


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    return app


@pytest.fixture(autouse=True)
def french_interface():
    """Chaque test démarre (et se termine) avec les textes sources français."""
    translator.set_language(editor.SOURCE_LANGUAGE, editor._TRANSLATIONS_DIRECTORY)
    yield
    translator.set_language(editor.SOURCE_LANGUAGE, editor._TRANSLATIONS_DIRECTORY)


@pytest.fixture
def window(qapp, tmp_path):
    raw_path = tmp_path / "carte-raw.jpg"
    Image.new("RGB", (400, 300), color="white").save(raw_path)
    win = ImageEditorWindow()
    win.load_source_image(raw_path)
    yield win
    win.close()


def _mouse(kind, x, y, modifiers=Qt.KeyboardModifier.NoModifier):
    buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
    point = QPointF(x, y)
    return QMouseEvent(kind, point, point, point, Qt.MouseButton.LeftButton, buttons, modifiers)


def _widget_point(canvas: ImageCanvas, image_point: QPointF) -> QPointF:
    """Convertit un point de l'image (espace aperçu) en coordonnées widget."""
    bounds = canvas._display_bounds()
    scale_x = bounds.width() / canvas.preview_image.width
    scale_y = bounds.height() / canvas.preview_image.height
    return QPointF(
        image_point.x() * scale_x + bounds.left(),
        image_point.y() * scale_y + bounds.top(),
    )


def _enable_numbering(window: ImageEditorWindow) -> None:
    window.select_tool(TOOL_CIRCLE)
    window.numbering_toggle_button.setChecked(True)


# ---------------------------------------------------------------------------
# Recette JSON : compteur et flag "numbered"
# ---------------------------------------------------------------------------
def test_circle_counter_and_numbered_flag_round_trip_and_default_for_legacy_json():
    recipe = ProcessingRecipe(
        circle_counter=7,
        annotations=[Annotation(type="circle", text="6", numbered=True)],
    )

    data = json.loads(recipe.to_json())
    assert data["circle_counter"] == 7
    assert data["annotations"][0]["numbered"] is True

    reloaded = ProcessingRecipe.from_json(recipe.to_json())
    assert reloaded.circle_counter == 7
    assert reloaded.annotations[0].numbered is True

    # Rétrocompatibilité : un ancien JSON sans ces clés garde les défauts.
    legacy = ProcessingRecipe.from_dict({"annotations": [{"type": "circle", "text": "2"}]})
    assert legacy.circle_counter == 1
    assert legacy.annotations[0].numbered is False


# ---------------------------------------------------------------------------
# Interface : la numérotation n'est activable que pour l'outil Cercle
# ---------------------------------------------------------------------------
def test_numbering_controls_are_enabled_only_for_the_circle_tool(window):
    window.select_tool(TOOL_CIRCLE)
    _enable_numbering(window)
    assert window.numbering_toggle_button.isEnabled()
    assert window.counter_label.isEnabled()
    assert window.counter_raz_button.isEnabled()

    for tool in (TOOL_RECT, TOOL_LINE, TOOL_TEXT):
        window.select_tool(tool)
        assert not window.numbering_toggle_button.isEnabled()
        assert not window.counter_label.isEnabled()
        assert not window.counter_raz_button.isEnabled()

    # L'état de la bascule est conservé quand on revient à l'outil Cercle.
    window.select_tool(TOOL_CIRCLE)
    assert window.numbering_toggle_button.isChecked()


def test_radius_spin_follows_the_numbering_toggle(window):
    """« Rayon » n'est activé pour l'outil Cercle qu'en mode numérotation."""
    window.select_tool(TOOL_CIRCLE)
    assert not window.border_radius_spin.isEnabled()

    _enable_numbering(window)
    assert window.border_radius_spin.isEnabled()
    assert "numérotés" in window.border_radius_spin.toolTip()

    window.numbering_toggle_button.setChecked(False)
    assert not window.border_radius_spin.isEnabled()

    # Rectangle : le spin garde son sens « arrondi des coins ».
    window.select_tool(TOOL_RECT)
    assert window.border_radius_spin.isEnabled()
    assert "Arrondi des coins" in window.border_radius_spin.toolTip()

    # Étiquette : arrondi des coins également.
    window.select_tool(TOOL_TEXT)
    assert window.border_radius_spin.isEnabled()
    assert "Arrondi des coins" in window.border_radius_spin.toolTip()

    window.select_tool(TOOL_LINE)
    assert not window.border_radius_spin.isEnabled()


# ---------------------------------------------------------------------------
# Taille des cercles numérotés pilotée par le spin « Rayon »
# ---------------------------------------------------------------------------
def test_numbered_circle_size_follows_the_radius_spin(window):
    _enable_numbering(window)
    canvas = window.canvas

    window.border_radius_spin.setValue(40)
    item = canvas.add_numbered_circle(QPointF(120, 90))
    assert abs((item.end.x() - item.start.x()) - 80) <= 0.01
    assert abs((item.end.y() - item.start.y()) - 80) <= 0.01

    # Rayon 0 = diamètre par défaut, rétrocompatible avec le placement historique.
    window.border_radius_spin.setValue(0)
    default_item = canvas.add_numbered_circle(QPointF(60, 40))
    assert abs((default_item.end.x() - default_item.start.x()) - DEFAULT_NUMBERED_CIRCLE_DIAMETER) <= 0.01
    assert abs((default_item.end.y() - default_item.start.y()) - DEFAULT_NUMBERED_CIRCLE_DIAMETER) <= 0.01


def test_changing_the_radius_spin_resizes_the_selected_numbered_circle(window):
    _enable_numbering(window)
    canvas = window.canvas
    item = canvas.add_numbered_circle(QPointF(120, 90))

    window.border_radius_spin.setValue(12)

    # Redimensionné autour de son centre, en restant parfaitement proportionné.
    center = QPointF((item.start.x() + item.end.x()) / 2, (item.start.y() + item.end.y()) / 2)
    assert abs(center.x() - 120) <= 0.01 and abs(center.y() - 90) <= 0.01
    assert abs((item.end.x() - item.start.x()) - 24) <= 0.01
    assert abs((item.end.y() - item.start.y()) - 24) <= 0.01
    # Le contour reste piloté par « Épaisseur ».
    assert item.stroke_width == canvas.current_stroke_width

    # La nouvelle taille est sérialisée dans la recette (géométrie pleine résolution).
    saved = ProcessingRecipe.load(window.current_json_path)
    saved_item = saved.annotations[-1]
    scale = window.preview_scale
    assert saved_item.numbered is True
    assert abs((saved_item.x2 - saved_item.x1) - 24 * scale) <= 1


def test_selecting_a_numbered_circle_shows_its_radius_in_the_spin(window):
    _enable_numbering(window)
    canvas = window.canvas
    item = canvas.add_numbered_circle(QPointF(120, 90))

    window._sync_panel_to_payload(item)
    assert window.border_radius_spin.value() == round(DEFAULT_NUMBERED_CIRCLE_DIAMETER / 2)

    # Redimensionné par une poignée : le spin suit la géométrie, sans valeur périmée.
    canvas._begin_item_drag(("shape_end", item), QPointF(item.end.x(), item.end.y()))
    canvas._drag_to(QPointF(item.start.x() + 60, item.start.y() + 60), snap=False)
    window._sync_panel_to_payload(item)
    assert window.border_radius_spin.value() == 30


# ---------------------------------------------------------------------------
# Placement par simple clic + incrémentation automatique
# ---------------------------------------------------------------------------
def test_a_plain_click_in_numbering_mode_places_the_next_numbered_circle(window):
    _enable_numbering(window)
    canvas = window.canvas

    target = _widget_point(canvas, QPointF(120, 90))
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, target.x(), target.y()))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target.x(), target.y()))

    assert len(canvas.annotations) == 1
    item = canvas.annotations[0]
    assert item.kind == "circle"
    assert item.numbered is True
    assert item.text == "1"
    # Cercle parfait de diamètre fixe, centré sur le clic.
    center = QPointF((item.start.x() + item.end.x()) / 2, (item.start.y() + item.end.y()) / 2)
    assert abs(center.x() - 120) <= 1 and abs(center.y() - 90) <= 1
    assert abs((item.end.x() - item.start.x()) - DEFAULT_NUMBERED_CIRCLE_DIAMETER) <= 0.01
    assert abs((item.end.y() - item.start.y()) - DEFAULT_NUMBERED_CIRCLE_DIAMETER) <= 0.01

    # Le compteur s'incrémente, s'affiche et se sauvegarde dans la recette.
    assert canvas.circle_counter == 2
    assert window.counter_label.text() == "Compteur : 2"
    saved = ProcessingRecipe.load(window.current_json_path)
    assert saved.circle_counter == 2
    assert saved.annotations[0].numbered is True
    assert saved.annotations[0].text == "1"


def test_click_without_numbering_does_not_place_a_circle(window):
    window.select_tool(TOOL_CIRCLE)
    canvas = window.canvas

    target = _widget_point(canvas, QPointF(120, 90))
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, target.x(), target.y()))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, target.x(), target.y()))

    # Mode normal : sans glisser, aucun cercle n'est créé.
    assert canvas.annotations == []
    assert canvas.circle_counter == 1


# ---------------------------------------------------------------------------
# Incrémentation, RAZ et rechargement de la recette
# ---------------------------------------------------------------------------
def test_numbering_increments_and_the_raz_button_resets_the_counter(window):
    _enable_numbering(window)
    canvas = window.canvas

    canvas.add_numbered_circle(QPointF(60, 40))
    canvas.add_numbered_circle(QPointF(320, 240))

    assert [item.text for item in canvas.annotations] == ["1", "2"]
    assert canvas.circle_counter == 3
    assert window.counter_label.text() == "Compteur : 3"

    window.counter_raz_button.click()

    assert canvas.circle_counter == 1
    assert window.counter_label.text() == "Compteur : 1"
    assert ProcessingRecipe.load(window.current_json_path).circle_counter == 1

    canvas.add_numbered_circle(QPointF(60, 240))
    assert canvas.annotations[-1].text == "1"


def test_counter_and_numbered_circles_are_restored_when_the_recipe_is_reloaded(window):
    _enable_numbering(window)
    canvas = window.canvas
    canvas.add_numbered_circle(QPointF(60, 40))
    canvas.add_numbered_circle(QPointF(140, 40))

    window.apply_recipe_to_ui(ProcessingRecipe.load(window.current_json_path))

    assert len(canvas.annotations) == 2
    assert all(item.numbered for item in canvas.annotations)
    assert canvas.circle_counter == 3
    assert window.counter_label.text() == "Compteur : 3"


def test_undo_restores_the_counter_value(window):
    _enable_numbering(window)
    canvas = window.canvas
    canvas.add_numbered_circle(QPointF(60, 40))
    assert canvas.circle_counter == 2

    assert window.undo() is True

    assert canvas.annotations == []
    assert canvas.circle_counter == 1
    assert window.counter_label.text() == "Compteur : 1"


def test_opening_a_new_image_resets_the_numbering_counter(window, tmp_path):
    """Ouvrir une image sans recette JSON fait repartir le compteur à 1."""
    _enable_numbering(window)
    canvas = window.canvas
    canvas.add_numbered_circle(QPointF(60, 40))
    canvas.add_numbered_circle(QPointF(140, 40))
    assert canvas.circle_counter == 3

    second_path = tmp_path / "seconde-carte.jpg"
    Image.new("RGB", (320, 240), color="white").save(second_path)
    window.load_source_image(second_path)

    assert canvas.circle_counter == 1
    assert window.counter_label.text() == "Compteur : 1"

    # Le premier cercle ajouté à la nouvelle image est toujours numéroté « 1 ».
    item = canvas.add_numbered_circle(QPointF(80, 60))
    assert item.text == "1"
    assert canvas.circle_counter == 2
    assert ProcessingRecipe.load(window.current_json_path).circle_counter == 2


def test_reopening_an_image_with_a_recipe_restores_its_counter(window):
    """La recette associée restaure la continuité de la numérotation."""
    _enable_numbering(window)
    canvas = window.canvas
    canvas.add_numbered_circle(QPointF(60, 40))
    canvas.add_numbered_circle(QPointF(140, 40))
    assert canvas.circle_counter == 3

    window.load_source_image(window.source_path)

    assert canvas.circle_counter == 3
    assert window.counter_label.text() == "Compteur : 3"


# ---------------------------------------------------------------------------
# Cercle parfait : redimensionnement contraint par les poignées
# ---------------------------------------------------------------------------
def test_numbered_circle_keeps_a_perfect_proportion_when_resized(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    item = AnnotationItem(
        kind="circle",
        start=QPointF(50, 50),
        end=QPointF(98, 98),
        numbered=True,
        id=1,
    )
    canvas.annotations = [item]
    canvas.tool = TOOL_CIRCLE

    # Poignée "end" tirée hors proportion : le cercle reste carré.
    canvas._begin_item_drag(("shape_end", item), QPointF(98, 98))
    canvas._drag_to(QPointF(150, 100), snap=False)

    assert item.end == QPointF(150, 150)
    assert item.start == QPointF(50, 50)


# ---------------------------------------------------------------------------
# Rendu aperçu (canvas) et export (moteur)
# ---------------------------------------------------------------------------
def test_preview_paints_the_numbered_circle_on_the_label_background(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    item = AnnotationItem(
        kind="circle",
        start=QPointF(60, 40),
        end=QPointF(108, 88),
        text="7",
        color=QColor("red"),
        stroke_width=3,
        numbered=True,
        id=1,
    )

    rendered = QImage(400, 300, QImage.Format.Format_RGB32)
    rendered.fill(QColor("white"))
    painter = QPainter(rendered)
    canvas.paint_annotations(painter, QRectF(0, 0, 400, 300), [item])
    painter.end()

    # Échelle 2 : centre écran (168, 128), rayon 48. Fond du label (alpha 230
    # sur blanc) à l'intérieur du cercle, loin du glyphe blanc.
    fill_pixel = rendered.pixelColor(168, 88)
    assert fill_pixel.red() < 90 and fill_pixel.green() < 90 and fill_pixel.blue() < 90
    # Le numéro est tracé en blanc autour du centre (disque de rayon 30, à
    # l'abri du contour rouge tracé au rayon 48).
    has_white_text = any(
        rendered.pixelColor(x, y) == QColor(255, 255, 255)
        for x in range(138, 199)
        for y in range(98, 159)
        if math.hypot(x - 168, y - 128) < 30
    )
    assert has_white_text


def test_export_renders_the_numbered_circle_with_a_white_number():
    image = Image.new("RGB", (200, 200), "white")
    numbered = Annotation(
        type="circle",
        x1=50,
        y1=50,
        x2=150,
        y2=150,
        text="3",
        color="#FF0000",
        stroke_width=4,
        numbered=True,
    )

    rendered = draw_annotations(image, [numbered])

    # Fond des étiquettes à l'intérieur du cercle, loin du glyphe.
    assert rendered.getpixel((100, 65)) == LABEL_BACKGROUND_RGB
    # Numéro blanc centré.
    has_white_text = any(
        rendered.getpixel((x, y)) == (255, 255, 255)
        for x in range(85, 116)
        for y in range(85, 116)
    )
    assert has_white_text
    # Contour rouge en haut du cercle.
    assert any(rendered.getpixel((x, 51)) == (255, 0, 0) for x in range(90, 111))

    # Un cercle ordinaire reste non rempli.
    plain = draw_annotations(
        image,
        [Annotation(type="circle", x1=50, y1=50, x2=150, y2=150, text="3", color="#FF0000", stroke_width=4)],
    )
    assert plain.getpixel((100, 65)) == (255, 255, 255)

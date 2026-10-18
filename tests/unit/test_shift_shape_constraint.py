#!/usr/bin/env python3
"""
  File Name: test_shift_shape_constraint.py
  Description: Tests de la contrainte Shift (TASK-013) : rectangle et cercle
               parfaitement proportionnés lors du dessin, de la reprise du
               tracé par-dessus une forme existante, du redimensionnement par
               poignées et du relâchement avec la touche Shift maintenue.
  Developer: ArnauldDev
  Created Date: 2026-10-18
  Last Modified: 2026-10-18
"""

from __future__ import annotations

import pytest
from PIL import Image
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QApplication

import iat.qt_image_editor as editor
from iat.qt_image_editor import (
    DEFAULT_NUMBERED_CIRCLE_DIAMETER,
    AnnotationItem,
    ImageCanvas,
    TOOL_CIRCLE,
    TOOL_LINE,
    TOOL_RECT,
    TOOL_VIEW,
    translator,
)

NO_MOD = Qt.KeyboardModifier.NoModifier
SHIFT = Qt.KeyboardModifier.ShiftModifier


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
def canvas(qapp):
    """Canevas 400×300 pour une image 400×300 : coordonnées écran == coordonnées image.

    Dans l'application, ``refresh_objects_list`` réconcilie ``layer_order`` à
    chaque ``annotation_changed`` ; le canevas isolé fait de même pour que le
    hit-test voie toutes les formes (sinon la 1re forme, sans jeton, disparaît).
    """
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (400, 300), color="white"))
    canvas.resize(400, 300)
    canvas.annotation_changed.connect(lambda: _sync_layer_order(canvas))
    yield canvas
    canvas.deleteLater()


def _sync_layer_order(canvas):
    annotation_tokens = [item.layer_token for item in canvas.annotations]
    loupe_tokens = [loupe.layer_token for loupe in canvas.loupes]
    valid_tokens = set(annotation_tokens) | set(loupe_tokens)
    order = [token for token in canvas.layer_order if token in valid_tokens]
    order.extend(token for token in [*annotation_tokens, *loupe_tokens] if token not in order)
    canvas.layer_order = order


def _mouse(kind, x, y, modifiers=NO_MOD):
    buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
    point = QPointF(x, y)
    return QMouseEvent(kind, point, point, point, Qt.MouseButton.LeftButton, buttons, modifiers)


def _press(x, y, modifiers=NO_MOD):
    return _mouse(QEvent.Type.MouseButtonPress, x, y, modifiers)


def _move(x, y, modifiers=NO_MOD):
    return _mouse(QEvent.Type.MouseMove, x, y, modifiers)


def _release(x, y, modifiers=NO_MOD):
    return _mouse(QEvent.Type.MouseButtonRelease, x, y, modifiers)


def _draw(canvas, start, end, press_mods=NO_MOD, move_mods=NO_MOD, release_mods=NO_MOD):
    """Trace une forme du point de départ au point d'arrivée et renvoie l'objet engagé."""
    canvas.mousePressEvent(_press(*start, press_mods))
    canvas.mouseMoveEvent(_move(*end, move_mods))
    canvas.mouseReleaseEvent(_release(*end, release_mods))
    return canvas.selected_item


def _size(item):
    return abs(item.end.x() - item.start.x()), abs(item.end.y() - item.start.y())


def _is_square(item):
    width, height = _size(item)
    return width == pytest.approx(height)


# ---------------------------------------------------------------------------
# Dessin : Shift contraint la forme pendant toute la gestuelle
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tool,kind", [(TOOL_RECT, "rect"), (TOOL_CIRCLE, "circle")])
def test_shift_drag_draws_a_perfectly_proportioned_shape(canvas, tool, kind):
    canvas.tool = tool

    item = _draw(canvas, (50, 50), (200, 130), press_mods=SHIFT, move_mods=SHIFT, release_mods=SHIFT)

    assert isinstance(item, AnnotationItem)
    assert item.kind == kind
    assert _is_square(item)


@pytest.mark.parametrize("tool", [TOOL_RECT, TOOL_CIRCLE])
def test_without_shift_the_shape_follows_the_pointer_freely(canvas, tool):
    canvas.tool = tool

    item = _draw(canvas, (50, 50), (200, 130))

    width, height = _size(item)
    assert width != pytest.approx(height)


@pytest.mark.parametrize("tool", [TOOL_RECT, TOOL_CIRCLE])
def test_shift_held_at_release_reconstrains_the_committed_shape(canvas, tool):
    """Shift appuyé pendant le drag sans mouvement suivant : la contrainte est
    réappliquée au relâchement, l'objet engagé reste parfaitement proportionné."""
    canvas.tool = tool

    item = _draw(canvas, (50, 50), (200, 130), move_mods=NO_MOD, release_mods=SHIFT)

    assert _is_square(item)


# ---------------------------------------------------------------------------
# Reprise du dessin par-dessus une forme existante (corps)
# ---------------------------------------------------------------------------
def test_shift_press_on_a_shape_body_starts_a_constrained_draw(canvas):
    canvas.tool = TOOL_RECT
    first = _draw(canvas, (10, 10), (120, 120))
    existing = len(canvas.annotations)

    # Reprise du dessin avec Shift, à partir du corps de la première forme :
    # Shift pilote la proportion, pas la bascule de sélection.
    canvas.mousePressEvent(_press(60, 60, SHIFT))
    assert canvas.dragging is True
    assert canvas.draft_annotation is None

    canvas.mouseMoveEvent(_move(200, 220, SHIFT))
    draft = canvas.draft_annotation
    canvas.mouseReleaseEvent(_release(200, 220, SHIFT))

    assert draft is not None
    assert _is_square(draft)
    assert len(canvas.annotations) == existing + 1
    assert canvas.selected_item is not first


def test_shift_click_still_extends_the_selection_with_the_view_tool(canvas):
    """Le périmètre de la contrainte se limite aux outils Rectangle/Cercle :
    avec l'outil Déplacer, Shift+clic ajoute toujours l'objet à la sélection."""
    canvas.tool = TOOL_RECT
    first = _draw(canvas, (10, 10), (120, 120))
    second = _draw(canvas, (200, 150), (350, 260))
    canvas.tool = TOOL_VIEW

    canvas.mousePressEvent(_press(60, 60, SHIFT))
    canvas.mouseReleaseEvent(_release(60, 60, SHIFT))

    assert set(canvas.selected_objects()) == {first, second}


def test_shift_click_still_extends_the_selection_with_the_line_tool(canvas):
    """Hors rectangle/cercle, la sélection Shift+clic reste inchangée."""
    canvas.tool = TOOL_RECT
    first = _draw(canvas, (10, 10), (120, 120))
    second = _draw(canvas, (200, 150), (350, 260))
    canvas.tool = TOOL_LINE

    canvas.mousePressEvent(_press(60, 60, SHIFT))
    canvas.mouseReleaseEvent(_release(60, 60, SHIFT))

    assert set(canvas.selected_objects()) == {first, second}


# ---------------------------------------------------------------------------
# Redimensionnement d'une forme existante par ses poignées
# ---------------------------------------------------------------------------
def test_shift_press_on_a_shape_handle_resizes_proportionally(canvas):
    canvas.tool = TOOL_RECT
    item = _draw(canvas, (10, 10), (120, 120))
    existing = len(canvas.annotations)

    # Poignée d'angle inférieur droit (écran 120,120) saisie avec Shift.
    canvas.mousePressEvent(_press(120, 120, SHIFT))
    assert canvas.draft_annotation is None
    assert canvas.drag_mode == "shape_end"

    canvas.mouseMoveEvent(_move(300, 240, SHIFT))
    canvas.mouseReleaseEvent(_release(300, 240, SHIFT))

    assert len(canvas.annotations) == existing
    assert _is_square(item)
    width, _height = _size(item)
    assert width == pytest.approx(290)


def test_shape_handle_resizes_freely_without_shift(canvas):
    canvas.tool = TOOL_RECT
    item = _draw(canvas, (10, 10), (120, 120))

    canvas.mousePressEvent(_press(120, 120))
    canvas.mouseMoveEvent(_move(300, 240))
    canvas.mouseReleaseEvent(_release(300, 240))

    width, height = _size(item)
    assert width == pytest.approx(290)
    assert height == pytest.approx(230)


def test_numbered_circle_handle_stays_proportional_without_shift(canvas):
    """Non-régression TASK-012 : le cercle numéroté contraint sa proportion
    même sans Shift maintenu."""
    canvas.tool = TOOL_CIRCLE
    canvas.numbering_enabled = True
    canvas.mousePressEvent(_press(100, 100))
    canvas.mouseReleaseEvent(_release(100, 100))
    item = canvas.selected_item

    radius = DEFAULT_NUMBERED_CIRCLE_DIAMETER / 2.0
    handle = (100 + radius, 100 + radius)
    canvas.mousePressEvent(_press(*handle))
    canvas.mouseMoveEvent(_move(handle[0] + 40, handle[1]))
    canvas.mouseReleaseEvent(_release(handle[0] + 40, handle[1]))

    assert _is_square(item)
    assert item.numbered is True

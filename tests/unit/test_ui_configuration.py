#!/usr/bin/env python3
"""
  File Name: test_ui_configuration.py
  Description: Tests du menu Configuration, de la barre horizontale texte, des thèmes
               (fusion avec le .env, lisibilité des menus, boutons « + »), de la fenêtre
               « À propos » et de l'accrochage à la grille avec la touche Ctrl.
  Developer: ArnauldDev
  Created Date: 2026-09-23
"""

from __future__ import annotations

import re

import pytest
from PIL import Image
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QStyle,
    QStyleOptionSpinBox,
    QToolBar,
)

import iat.qt_image_editor as editor
from iat.config import AppConfig, update_config_in_place
from iat.qt_image_editor import AnnotationItem, ImageCanvas, ImageEditorWindow, TOOL_RECT, TOOL_VIEW

THEME_NAMES = ("cbi", "clair", "sombre")


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    return app


def _theme(window: ImageEditorWindow, name: str):
    return next(path for path in window._available_themes() if path.stem == name)


# ---------------------------------------------------------------------------
# Menus
# ---------------------------------------------------------------------------
def test_configuration_menu_sits_between_file_and_help(qapp):
    window = ImageEditorWindow()

    titles = [action.text() for action in window.menuBar().actions()]
    assert titles == ["Fichier", "Édition", "Configuration", "Aide"]
    entries = [action.text() for action in window.configuration_menu.actions() if not action.isSeparator()]
    assert entries == [
        "Charger une configuration .env",
        "À propos des fichiers .env",
        "Thèmes disponibles",
        "Charger un thème personnalisé",
        "Langue",
        "Chemins des ressources…",
        "Notification après l'export",
        "Afficher/Masquer la barre horizontale des outils",
        "Afficher/Masquer la palette graphique des outils",
        "Réinitialiser les paramètres…",
    ]
    file_entries = {action.text() for action in window.menuBar().actions()[0].menu().actions()}
    assert "Charger une configuration .env" not in file_entries


def test_toolbar_visibility_can_be_toggled_from_the_configuration_menu(qapp):
    window = ImageEditorWindow()
    window.show()

    assert window.toggle_toolbar_action.isChecked()
    window.toggle_toolbar_action.trigger()
    assert window.main_toolbar.isHidden()
    assert not window.toggle_toolbar_action.isChecked()
    window.toggle_toolbar_action.trigger()
    assert not window.main_toolbar.isHidden()
    window.close()


def test_available_themes_submenu_marks_the_active_theme(qapp):
    window = ImageEditorWindow()
    window._load_theme_path(_theme(window, "sombre"))

    checked = [action.text() for action in window.themes_menu.actions() if action.isChecked()]
    assert checked == ["Sombre"]


# ---------------------------------------------------------------------------
# Barre horizontale : boutons texte + icône « outils »
# ---------------------------------------------------------------------------
def test_main_toolbar_uses_text_buttons_and_the_tools_icon(qapp):
    window = ImageEditorWindow()
    toolbar = window.findChild(QToolBar, "main_toolbar")

    assert toolbar.toolButtonStyle() == Qt.ToolButtonStyle.ToolButtonTextOnly
    first_widget = toolbar.widgetForAction(toolbar.actions()[0])
    assert first_widget is window.toolbar_tools_icon
    assert not window.toolbar_tools_icon.pixmap().isNull()
    texts = [
        toolbar.widgetForAction(action).text()
        for action in toolbar.actions()
        if not action.isSeparator() and toolbar.widgetForAction(action) is not window.toolbar_tools_icon
    ]
    assert texts == ["Ouvrir une image", "Transformation", "Annotation", "Outil loupe", "Exporter l'image"]
    # Le logo CBI a quitté la barre d'outils pour la barre d'état.
    assert toolbar.findChild(QLabel, "status_logo_cbi") is None
    assert window.statusBar().findChild(QLabel, "status_logo_cbi") is not None


def test_graphical_palette_has_explicit_svg_icons_and_rich_tooltips(qapp):
    window = ImageEditorWindow()

    for key, action in window.graphical_tool_actions.items():
        assert not action.icon().isNull(), key
        assert action.toolTip().startswith("<b>"), key


# ---------------------------------------------------------------------------
# Thèmes : source unique de l'apparence
# ---------------------------------------------------------------------------
def _rule(stylesheet: str, selector: str) -> str:
    # Le sélecteur peut faire partie d'une liste (« A, B { … } »).
    match = re.search(r"(?m)^" + re.escape(selector) + r"\s*(?:,[^{]*)?\{([^}]*)\}", stylesheet)
    assert match, f"règle {selector} absente"
    return match.group(1)


def _luminance(hex_color: str) -> float:
    color = QColor(hex_color)

    def channel(value: int) -> float:
        value = value / 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(color.red()) + 0.7152 * channel(color.green()) + 0.0722 * channel(color.blue())


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


@pytest.mark.parametrize("name", THEME_NAMES)
def test_bundled_themes_keep_menus_and_submenus_readable(qapp, name):
    stylesheet = (editor._THEMES_DIRECTORY / f"{name}.qss").read_text(encoding="utf-8")

    for selector in ("QMenuBar", "QMenu", "QMenu::item:selected", "QMenuBar::item:selected"):
        block = _rule(stylesheet, selector)
        background = re.search(r"background-color:\s*(#[0-9A-Fa-f]{6})", block).group(1)
        text = re.search(r"(?<!-)color:\s*(#[0-9A-Fa-f]{6})", block).group(1)
        assert _contrast(background, text) >= 4.5, (name, selector, background, text)
    assert editor._THEME_ICON_COLOR_RE.search(stylesheet)


def test_default_theme_comes_from_app_theme_and_user_choice_wins(qapp, monkeypatch):
    from iat.config import config

    monkeypatch.setattr(config, "app_theme", "clair")
    window = ImageEditorWindow()
    assert window.current_theme_path.stem == "clair"

    window._load_theme_path(_theme(window, "sombre"))
    again = ImageEditorWindow()  # même profil QSettings isolé : le choix est mémorisé
    assert again.current_theme_path.stem == "sombre"


def test_env_file_with_app_theme_applies_that_theme(qapp, tmp_path, monkeypatch):
    env_file = tmp_path / "custom.env"
    env_file.write_text("APP_THEME=sombre\nDEFAULT_STROKE_WIDTH=6\n", encoding="utf-8")
    monkeypatch.setenv("APP_THEME", "cbi")
    monkeypatch.setenv("DEFAULT_STROKE_WIDTH", "3")
    window = ImageEditorWindow()
    try:
        window.load_environment_file(str(env_file))

        assert window.current_theme_path.stem == "sombre"
        assert window.stroke_width_spin.value() == 6
    finally:
        monkeypatch.undo()
        update_config_in_place(AppConfig())


def test_theme_icon_urls_are_resolved_to_tinted_svg_copies(qapp):
    window = ImageEditorWindow()
    window._load_theme_path(_theme(window, "sombre"))

    assert "url(@icons/" not in window.styleSheet()
    paths = re.findall(r"url\(([^)]+plus\.svg)\)", window.styleSheet())
    assert paths
    assert "#00f5ff" in open(paths[0], encoding="utf-8").read().lower()


@pytest.mark.parametrize("name", THEME_NAMES)
def test_spin_box_plus_buttons_are_large_and_clickable_in_every_theme(qapp, name):
    window = ImageEditorWindow()
    window._load_theme_path(_theme(window, name))
    window.showNormal()
    window.resize(1600, 1000)
    window.select_tool("text")
    QApplication.processEvents()
    spin = window.stroke_width_spin
    spin.setValue(3)

    option = QStyleOptionSpinBox()
    option.initFrom(spin)
    option.subControls = QStyle.SubControl.SC_All
    option.stepEnabled = spin.stepEnabled()
    up_rect = spin.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, QStyle.SubControl.SC_SpinBoxUp, spin)

    assert up_rect.width() >= 16 and up_rect.height() >= 9, up_rect
    QTest.mouseClick(spin, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, up_rect.center())
    assert spin.value() == 4
    window.close()


# ---------------------------------------------------------------------------
# Fenêtre « À propos »
# ---------------------------------------------------------------------------
def test_about_dialog_shows_the_logo_left_and_information_right(qapp):
    window = ImageEditorWindow()
    dialog = window._build_about_dialog()
    dialog.show()
    QApplication.processEvents()

    logo = dialog.findChild(QLabel, "about_logo")
    information = dialog.findChild(QLabel, "about_information")
    close_button = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Fermer")
    assert not logo.pixmap().isNull()
    assert logo.geometry().right() < information.geometry().left()
    assert close_button.geometry().left() >= information.geometry().left()
    assert "Image Annotation Tool" in information.text()
    source_link = dialog.findChild(QLabel, "about_link_source")
    assert "Accéder au dépôt du code source" in source_link.text()
    assert source_link.geometry().left() >= information.geometry().left()
    dialog.close()


# ---------------------------------------------------------------------------
# Accrochage à la grille uniquement avec Ctrl
# ---------------------------------------------------------------------------
def _mouse(kind, x, y, modifiers=Qt.KeyboardModifier.NoModifier):
    buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
    point = QPointF(x, y)
    return QMouseEvent(kind, point, point, point, Qt.MouseButton.LeftButton, buttons, modifiers)


def _canvas_with_rect():
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)  # échelle d'affichage ×2 : grille fine de 50 px image
    item = AnnotationItem(kind="rect", start=QPointF(20, 20), end=QPointF(60, 60))
    canvas.annotations = [item]
    canvas.tool = TOOL_VIEW
    return canvas, item


def _drag(canvas, modifiers):
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 80, 80, modifiers))
    canvas.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 97, 93, modifiers))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 97, 93, modifiers))


def test_objects_move_freely_without_ctrl_even_when_the_grid_is_visible(qapp):
    canvas, item = _canvas_with_rect()
    canvas.show_rotation_grid = True

    _drag(canvas, Qt.KeyboardModifier.NoModifier)

    assert (item.start.x(), item.start.y()) == pytest.approx((28.5, 26.5))
    assert (item.end.x(), item.end.y()) == pytest.approx((68.5, 66.5))


def test_holding_ctrl_snaps_moved_objects_to_the_grid(qapp):
    canvas, item = _canvas_with_rect()

    _drag(canvas, Qt.KeyboardModifier.ControlModifier)

    # Grille fine centrée sur l'image (100, 75) avec un pas de 50 px.
    assert (item.start.x(), item.start.y()) == pytest.approx((50.0, 25.0))
    # Le déplacement conserve la taille de l'objet.
    assert (item.end.x() - item.start.x(), item.end.y() - item.start.y()) == pytest.approx((40.0, 40.0))


def test_holding_ctrl_snaps_new_shapes_to_the_grid(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    canvas.tool = TOOL_RECT
    ctrl = Qt.KeyboardModifier.ControlModifier

    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 110, 60, ctrl))
    canvas.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 290, 240, ctrl))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 290, 240, ctrl))

    rect = canvas.annotations[-1]
    assert (rect.start.x(), rect.start.y()) == pytest.approx((50.0, 25.0))
    assert (rect.end.x(), rect.end.y()) == pytest.approx((150.0, 125.0))

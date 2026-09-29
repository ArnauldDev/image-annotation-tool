#!/usr/bin/env python3
"""
  File Name: test_editing_features.py
  Description: Tests des fonctions d'édition et de configuration ajoutées : export sans double
               confirmation, notification après l'export, chemins des ressources, langue,
               réinitialisation des paramètres, fenêtre « À propos », sélection des lignes,
               sélection multiple, alignement, copier/coller, annuler/rétablir,
               glisser-déposer d'une image et préréglages de largeur d'export.
  Developer: ArnauldDev
  Created Date: 2026-09-23
  Last Modified: 2026-09-23
"""

from __future__ import annotations

import ast
import json

import pytest
from PIL import Image
from PyQt6.QtCore import QEvent, QMimeData, QPointF, QUrl, Qt
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton, QToolButton

import iat.qt_image_editor as editor
from iat.image_processor import ProcessingRecipe
from iat.qt_image_editor import (
    AnnotationItem,
    ImageCanvas,
    ImageEditorWindow,
    LoupeOverlay,
    TOOL_VIEW,
    Translator,
    translator,
)


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
    raw_path = tmp_path / "carte-raw.jpg"
    Image.new("RGB", (400, 300), color="white").save(raw_path)
    win = ImageEditorWindow()
    win.load_source_image(raw_path)
    yield win
    win.close()


def _rect(x1, y1, x2, y2, color="yellow"):
    return AnnotationItem(kind="rect", start=QPointF(x1, y1), end=QPointF(x2, y2), color=QColor(color))


def _add(window, *items):
    window.canvas.annotations.extend(items)
    window.canvas.annotation_changed.emit()


def _mouse(kind, x, y, modifiers=Qt.KeyboardModifier.NoModifier):
    buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
    point = QPointF(x, y)
    return QMouseEvent(kind, point, point, point, Qt.MouseButton.LeftButton, buttons, modifiers)


# ---------------------------------------------------------------------------
# Export : une seule confirmation, notification optionnelle
# ---------------------------------------------------------------------------
def test_export_over_an_existing_file_asks_no_second_confirmation(window, tmp_path, monkeypatch):
    target = tmp_path / "export.jpg"
    target.write_bytes(b"old")
    monkeypatch.setattr(editor.QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), ""))
    questions, notifications = [], []
    monkeypatch.setattr(editor.QMessageBox, "question", lambda *args, **kwargs: questions.append(args))
    monkeypatch.setattr(editor.QMessageBox, "information", lambda *args, **kwargs: notifications.append(args))

    window.export_image()

    assert questions == []
    assert len(notifications) == 1
    assert target.stat().st_size > 3
    assert "Exporté vers" in window.statusBar().currentMessage()


def test_export_notification_can_be_disabled_but_status_message_remains(window, tmp_path, monkeypatch):
    target = tmp_path / "export.jpg"
    monkeypatch.setattr(editor.QFileDialog, "getSaveFileName", lambda *args, **kwargs: (str(target), ""))
    notifications = []
    monkeypatch.setattr(editor.QMessageBox, "information", lambda *args, **kwargs: notifications.append(args))

    assert window.export_notification_action.isChecked()
    window.export_notification_action.trigger()
    assert not window.export_notification_enabled()
    window.export_image()

    assert notifications == []
    assert target.exists()
    assert "Exporté vers" in window.statusBar().currentMessage()
    # Le choix est mémorisé pour les sessions suivantes.
    assert not ImageEditorWindow().export_notification_action.isChecked()


# ---------------------------------------------------------------------------
# Chemins des ressources et réinitialisation
# ---------------------------------------------------------------------------
def test_resource_paths_default_to_bundled_folders_and_can_be_changed(qapp, tmp_path):
    window = ImageEditorWindow()
    assert window.resource_paths == editor.DEFAULT_RESOURCE_PATHS

    themes = tmp_path / "mes-themes"
    themes.mkdir()
    (themes / "maison.qss").write_text("QWidget { color: #111111; }", encoding="utf-8")
    assert window.apply_resource_paths({"themes": themes})

    assert window.resource_paths["themes"] == themes
    assert [path.name for path in window._available_themes()] == ["maison.qss"]
    assert ImageEditorWindow().resource_paths["themes"].resolve() == themes.resolve()
    # Une icône absente du dossier personnalisé reste celle livrée avec l'application.
    assert window._icon_path("tools.svg") == editor.ICONS_DIRECTORY / "tools.svg"


def test_invalid_resource_path_is_rejected(qapp, tmp_path, monkeypatch):
    window = ImageEditorWindow()
    warnings = []
    monkeypatch.setattr(editor.QMessageBox, "warning", lambda *args, **kwargs: warnings.append(args))

    assert not window.apply_resource_paths({"icons": tmp_path / "absent"})
    assert warnings
    assert window.resource_paths["icons"] == editor.ICONS_DIRECTORY


def test_resource_paths_dialog_offers_a_field_per_resource(qapp):
    window = ImageEditorWindow()
    dialog, edits = window._build_resource_paths_dialog()
    assert set(edits) == {"icons", "themes", "translations"}
    assert edits["themes"].text() == str(editor.DEFAULT_RESOURCE_PATHS["themes"])
    dialog.close()


def test_reset_settings_restores_every_default(qapp, tmp_path):
    window = ImageEditorWindow()
    themes = tmp_path / "themes"
    themes.mkdir()
    (themes / "perso.qss").write_text("QWidget { color: #222222; }", encoding="utf-8")
    window.apply_resource_paths({"themes": themes})
    window._load_theme_path(themes / "perso.qss")
    window.set_export_notification_enabled(False)
    window.set_language("en")
    window._remember_custom_color(QColor("#123456"))
    window.main_toolbar.hide()

    assert window.reset_settings(confirm=False)

    assert window.resource_paths == editor.DEFAULT_RESOURCE_PATHS
    assert window.current_theme_path.stem == "cbi"
    assert window.export_notification_enabled()
    assert window.export_notification_action.isChecked()
    assert translator.language == "fr"
    assert window._custom_colors() == []
    assert not window.main_toolbar.isHidden()
    assert window._settings.value("theme_path", "") == ""


# ---------------------------------------------------------------------------
# Langue de l'interface
# ---------------------------------------------------------------------------
def test_translation_files_list_french_and_english():
    languages = Translator.available_languages(editor._TRANSLATIONS_DIRECTORY)
    assert languages["fr"] == "Français"
    assert languages["en"] == "English"


def test_every_english_translation_matches_a_text_of_the_code():
    # Les chaînes concaténées implicitement sont réunies par ast : une clé du
    # catalogue doit correspondre exactement à un texte du code.
    tree = ast.parse(editor.Path(editor.__file__).read_text(encoding="utf-8"))
    texts = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str)}
    catalog = json.loads((editor._TRANSLATIONS_DIRECTORY / "en.json").read_text(encoding="utf-8"))
    missing = [key for key in catalog if key != "_language_name" and key not in texts]
    assert missing == []


def test_interface_switches_to_english_and_back(window):
    window.set_language("en")

    titles = [action.text() for action in window.menuBar().actions()]
    assert titles == ["File", "Edit", "Settings", "Help"]
    assert window.export_button.text() == "Export the annotated image"
    assert window.toolbar_tool_buttons[editor.TOOL_LOUPE].text() == "Loupe tool"
    assert window.graphical_tool_actions["open"].toolTip().startswith("<b>Open an image</b>")
    assert window._settings.value("language") == "en"
    assert next(a for a in window.language_menu.actions() if a.data() == "en").isChecked()

    window.set_language("fr")
    titles = [action.text() for action in window.menuBar().actions()]
    assert titles == ["Fichier", "Édition", "Configuration", "Aide"]
    assert window.export_button.text() == "Exporter l'image annotée"


def test_saved_language_is_applied_at_start_up(qapp):
    ImageEditorWindow().set_language("en")
    restarted = ImageEditorWindow()
    assert restarted.menuBar().actions()[0].text() == "File"


def test_unknown_language_is_refused_quietly(qapp):
    window = ImageEditorWindow()
    assert not window.set_language("xx", quiet=True)
    assert translator.language == "fr"


# ---------------------------------------------------------------------------
# Fenêtre « À propos »
# ---------------------------------------------------------------------------
def test_about_links_have_an_icon_on_their_left_and_show_the_address_on_hover(qapp):
    window = ImageEditorWindow()
    dialog = window._build_about_dialog()
    dialog.show()
    QApplication.processEvents()

    for key, address in (
        ("source", editor.APP_SOURCE),
        ("mail", editor.APP_CONTACT_EMAIL),
        ("web", editor.APP_LAB_URL),
        ("ut", editor.APP_UT_URL),
    ):
        icon = dialog.findChild(QToolButton, f"about_icon_{key}")
        link = dialog.findChild(QLabel, f"about_link_{key}")
        assert not icon.icon().isNull(), key
        assert icon.geometry().right() < link.geometry().left(), key
        assert icon.toolTip() == address and link.toolTip() == address, key
    assert "mailto:arnauld.biganzoli@utoulouse.fr" in dialog.findChild(QLabel, "about_link_mail").text()

    copy_button = dialog.findChild(QPushButton, "about_copy_email")
    close_button = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Fermer")
    assert copy_button.geometry().right() < close_button.geometry().left()
    dialog.close()


def test_mail_link_without_mail_program_explains_and_offers_to_copy(qapp, monkeypatch):
    window = ImageEditorWindow()
    shown = []
    monkeypatch.setattr(editor.QDesktopServices, "openUrl", lambda _url: False)
    monkeypatch.setattr(editor.QMessageBox, "exec", lambda box: shown.append(box) or 0)

    assert not window._open_about_link(f"mailto:{editor.APP_CONTACT_EMAIL}")

    assert len(shown) == 1
    box = shown[0]
    assert editor.APP_CONTACT_EMAIL in box.text()
    copy_button = box.findChild(QPushButton, "mail_copy_button")
    copy_button.click()
    assert QApplication.clipboard().text() == editor.APP_CONTACT_EMAIL
    labels = [button.text() for button in box.buttons()]
    assert "Fermer" in labels and "Copier l'adresse" in labels


# ---------------------------------------------------------------------------
# Sélection d'une ligne
# ---------------------------------------------------------------------------
def test_clicking_anywhere_on_a_line_selects_and_moves_it(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    line = AnnotationItem(kind="line", start=QPointF(20, 20), end=QPointF(120, 20), stroke_width=2)
    canvas.annotations = [line]
    canvas.tool = editor.TOOL_LINE

    # Milieu de la ligne (60, 20) image → (140, 40) écran, 3 px à côté du trait.
    assert canvas._hit_test(QPointF(140, 43))[0] == "line_body"
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 140, 43))
    canvas.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 160, 63))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 160, 63))

    assert canvas.annotations == [line]  # aucune nouvelle ligne créée
    assert canvas.selected_item is line
    assert line.start == QPointF(30, 30) and line.end == QPointF(130, 30)


# ---------------------------------------------------------------------------
# Sélection multiple et alignement
# ---------------------------------------------------------------------------
def test_objects_list_allows_shift_and_ctrl_multi_selection(window):
    first, second, third = _rect(10, 10, 40, 40), _rect(100, 50, 140, 90), _rect(200, 20, 230, 60)
    _add(window, first, second, third)

    window.objects_list.setCurrentRow(0)
    window.objects_list.item(2).setSelected(True)  # Ctrl + clic

    selected = window.canvas.selected_objects()
    assert len(selected) == 2
    assert window.canvas.is_selected(window.objects_list.item(0).data(Qt.ItemDataRole.UserRole))
    assert window.canvas.is_selected(window.objects_list.item(2).data(Qt.ItemDataRole.UserRole))

    window.delete_selected_object()
    assert len(window.canvas.annotations) == 1
    assert window.objects_list.count() == 1


def test_shift_click_on_the_canvas_extends_the_selection_and_group_drag_moves_all(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    first, second = _rect(10, 10, 30, 30), _rect(100, 60, 120, 80)
    canvas.annotations = [first, second]
    canvas.tool = TOOL_VIEW

    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 40, 40))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 40, 40))
    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 220, 140, Qt.KeyboardModifier.ShiftModifier))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 220, 140, Qt.KeyboardModifier.ShiftModifier))
    assert canvas.selected_objects() == [first, second]

    canvas.mousePressEvent(_mouse(QEvent.Type.MouseButtonPress, 40, 40))
    canvas.mouseMoveEvent(_mouse(QEvent.Type.MouseMove, 60, 50))
    canvas.mouseReleaseEvent(_mouse(QEvent.Type.MouseButtonRelease, 60, 50))
    assert first.start == QPointF(20, 15)
    assert second.start == QPointF(110, 65)


def test_alignment_between_objects_and_on_the_image(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    first, second, third = _rect(10, 10, 30, 30), _rect(50, 40, 90, 60), _rect(150, 100, 160, 110)
    canvas.annotations = [first, second, third]

    canvas.set_selection([first, second])
    assert canvas.align_selection("left")
    assert first.start.x() == 10 and second.start.x() == 10

    canvas.set_selection([first, second, third])
    assert canvas.align_selection("top")
    assert {item.start.y() for item in (first, second, third)} == {10}

    canvas.selected_item = third
    assert canvas.align_selection("hcenter")  # un seul objet : centré sur l'image
    assert canvas.item_bounds(third).center().x() == pytest.approx(100)


def test_distribution_spreads_centres_evenly(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    first, middle, last = _rect(0, 0, 10, 10), _rect(20, 0, 30, 10), _rect(90, 0, 100, 10)
    canvas.annotations = [first, middle, last]
    canvas.set_selection([first, middle])
    assert not canvas.align_selection("hdistribute")  # au moins trois objets

    canvas.set_selection([first, middle, last])
    assert canvas.align_selection("hdistribute")
    assert canvas.item_bounds(middle).center().x() == pytest.approx(50)


def test_context_menu_offers_alignment_distribution_and_edition(window):
    first, second = _rect(10, 10, 40, 40), _rect(100, 50, 140, 90)
    _add(window, first, second)
    window.canvas.set_selection([first, second])

    menu = window.canvas.build_context_menu()
    entries = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert entries[0].startswith("Aligner (entre eux)")
    assert "Distribuer" in entries and "Accrocher à la grille" in entries
    assert {"Copier", "Coller", "Supprimer"} <= set(entries)
    distribute = next(action for action in menu.actions() if action.text() == "Distribuer")
    assert not distribute.isEnabled()  # seulement deux objets


# ---------------------------------------------------------------------------
# Copier / Coller et Annuler / Rétablir
# ---------------------------------------------------------------------------
def test_copy_paste_duplicates_the_selected_objects_with_their_characteristics(window):
    rect = _rect(10, 10, 40, 40, color="#ff0000")
    rect.stroke_width = 7
    _add(window, rect)
    window.create_new_loupe()
    loupe = window.canvas.loupes[0]
    loupe.zoom = 3.5
    window.canvas.set_selection([rect, loupe])

    assert window.copy_selection() == 2
    pasted = window.paste_clipboard()

    assert len(window.canvas.annotations) == 2 and len(window.canvas.loupes) == 2
    copy_rect = next(item for item in pasted if isinstance(item, AnnotationItem))
    copy_loupe = next(item for item in pasted if isinstance(item, LoupeOverlay))
    assert copy_rect is not rect and copy_rect.stroke_width == 7 and copy_rect.color.name() == "#ff0000"
    assert copy_rect.start == QPointF(30, 30)
    assert copy_loupe.id == 2 and copy_loupe.zoom == 3.5
    assert window.layer_order[:2] == ["annotation:1", "loupe:2"]
    assert window.canvas.selected_objects() == pasted
    saved = ProcessingRecipe.load(window.current_json_path)
    assert len(saved.annotations) == 2 and len(saved.loupes) == 2


def test_undo_and_redo_restore_the_previous_states(window):
    assert not window.undo_action.isEnabled()
    rect = _rect(10, 10, 40, 40)
    _add(window, rect)
    window.canvas.selected_item = window.canvas.annotations[0]
    window.stroke_width_spin.setValue(9)
    assert window.undo_action.isEnabled()

    assert window.undo()
    assert window.canvas.annotations[0].stroke_width == 3
    assert window.undo()
    assert window.canvas.annotations == []
    assert not window.undo_action.isEnabled()
    assert ProcessingRecipe.load(window.current_json_path).annotations == []

    assert window.redo()
    assert window.redo()
    assert window.canvas.annotations[0].stroke_width == 9
    assert not window.redo_action.isEnabled()

    window.undo()
    window.apply_rotation(90, absolute=False)
    assert not window.redo_action.isEnabled()  # une nouvelle modification vide « Rétablir »


def test_undo_shortcuts_are_ctrl_z_and_ctrl_y(qapp):
    window = ImageEditorWindow()
    assert window.undo_action.shortcut().toString() == "Ctrl+Z"
    assert "Ctrl+Y" in [shortcut.toString() for shortcut in window.redo_action.shortcuts()]
    assert window.copy_action.shortcut().toString() == "Ctrl+C"
    assert window.paste_action.shortcut().toString() == "Ctrl+V"


# ---------------------------------------------------------------------------
# Glisser-déposer et préréglages d'export
# ---------------------------------------------------------------------------
def test_dropping_an_image_file_opens_it(qapp, tmp_path):
    image_path = tmp_path / "depose-raw.png"
    Image.new("RGB", (120, 80), color="red").save(image_path)
    other = tmp_path / "notes.txt"
    other.write_text("x", encoding="utf-8")
    window = ImageEditorWindow()

    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(other)), QUrl.fromLocalFile(str(image_path))])
    assert window._dropped_image_path(mime) == image_path

    text_only = QMimeData()
    text_only.setUrls([QUrl.fromLocalFile(str(other))])
    assert window._dropped_image_path(text_only) is None

    class _Drop:
        def __init__(self, data):
            self.data, self.accepted = data, False

        def mimeData(self):
            return self.data

        def acceptProposedAction(self):
            self.accepted = True

        def ignore(self):
            self.accepted = False

    event = _Drop(mime)
    window.dropEvent(event)
    assert event.accepted
    assert window.source_path == image_path
    assert window.acceptDrops()


def test_export_width_presets(window):
    assert [button.text() for button in window.export_preset_buttons.values()] == ["800 px", "1200 px", "1920 px"]
    window.export_preset_buttons[1920].click()
    assert window.width_spin.value() == 1920
    assert window.height_spin.value() == 1440  # proportions 4:3 conservées
    assert window.export_preset_buttons[1920].isChecked()
    assert not window.export_preset_buttons[800].isChecked()
    window.width_spin.setValue(1000)
    assert not any(button.isChecked() for button in window.export_preset_buttons.values())

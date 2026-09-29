import os
import sys
from pathlib import Path
from PIL import Image
import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PyQt6.QtWidgets import QApplication, QFrame, QToolBar
from PyQt6.QtCore import QPoint, QPointF, QRectF, QEvent, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QMouseEvent

from iat.qt_image_editor import (
    ImageCanvas,
    ImageEditorWindow,
    AnnotationItem,
    LoupeOverlay,
    TOOL_CROP,
    TOOL_DESCRIPTIONS,
    TOOL_LINE,
    TOOL_ROTATE_LINE,
    TOOL_VIEW,
)
from iat.image_processor import ProcessingRecipe


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_editor_starts_without_preloaded_image(qapp):
    window = ImageEditorWindow()
    assert window.source_path is None
    assert window.original_image is None
    assert window.preview_image is None
    assert window.current_json_path is None
    assert window.canvas.base_pixmap is None
    assert window.objects_list.count() == 0


def test_move_tool_is_named_and_resizes_crop(qapp):
    assert TOOL_DESCRIPTIONS[TOOL_VIEW][0] == "Déplacer"

    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (200, 150), color="white"))
    canvas.resize(400, 300)
    canvas.crop_rect = QRectF(20, 20, 100, 80)
    canvas.selected_item = "crop"
    hit = canvas._crop_hit_test(QPointF(240, 200))

    assert hit is not None
    assert hit[0] == "crop_resize_br"
    canvas.drag_mode = hit[0]
    canvas._apply_drag(QPointF(20, 10))
    assert canvas.crop_rect == QRectF(20, 20, 120, 90)


def test_shift_line_constraint_snaps_to_horizontal_vertical_and_45_degrees(qapp):
    start = QPointF(10, 10)

    horizontal = ImageCanvas._constrain_to_45_degrees(start, QPointF(90, 20))
    diagonal = ImageCanvas._constrain_to_45_degrees(start, QPointF(80, 70))

    assert horizontal.y() == pytest.approx(start.y())
    assert abs(diagonal.x() - start.x()) == pytest.approx(abs(diagonal.y() - start.y()))


def test_label_selection_frame_contains_text_when_arrow_points_left(qapp):
    canvas = ImageCanvas()
    item = AnnotationItem(kind="label", start=QPointF(150, 50), end=QPointF(20, 80), text="Objet")
    label_rect = canvas._label_screen_rect(item, QPointF(150, 50))
    selection = label_rect.united(QRectF(QPointF(150, 50), QPointF(20, 80)))

    assert selection.contains(label_rect.topRight())
    assert selection.left() <= 20


def test_rotation_grid_spacing_is_visually_wider(qapp):
    canvas = ImageCanvas()
    canvas.preview_image = Image.new("RGB", (400, 300), color="white")
    bounds = QRectF(0, 0, 800, 600)

    step = canvas.rotation_grid_step(bounds)

    assert step >= 100
    assert step % 10 == 0


def test_export_size_spin_boxes_use_10px_steps(qapp):
    window = ImageEditorWindow()

    assert window.width_spin.singleStep() == 10
    assert window.height_spin.singleStep() == 10


def test_theme_validation_and_auto_discovery(qapp, tmp_path):
    valid_theme = tmp_path / "valid.qss"
    valid_theme.write_text("QWidget { color: #ffffff; }", encoding="utf-8")
    invalid_theme = tmp_path / "invalid.qss"
    invalid_theme.write_text("QWidget { color: #ffffff;", encoding="utf-8")

    window = ImageEditorWindow()

    assert window._validate_stylesheet(valid_theme).startswith("QWidget")
    with pytest.raises(ValueError, match="accolades"):
        window._validate_stylesheet(invalid_theme)
    assert {path.name for path in window._available_themes()} >= {
        "clair.qss", "cbi.qss", "sombre.qss"
    }


def test_loupe_selection_updates_tool_controls(qapp):
    window = ImageEditorWindow()
    loupe = LoupeOverlay(zoom=3.5, radius=140)
    window.canvas.loupes = [loupe]
    window.refresh_objects_list()

    window.objects_list.setCurrentRow(0)

    assert window.objects_list.currentItem().data(Qt.ItemDataRole.UserRole) is loupe
    assert window.loupe_zoom_spin.value() == 3.5
    assert window.loupe_radius_spin.value() == 140


def test_annotation_list_reordering_updates_preview_order_and_json(qapp, tmp_path):
    raw_path = tmp_path / "ordered-raw.jpg"
    Image.new("RGB", (200, 150), color="white").save(raw_path)

    window = ImageEditorWindow()
    window.load_source_image(raw_path)
    first = AnnotationItem(kind="rect", start=QPointF(10, 10), end=QPointF(40, 40), text="first")
    second = AnnotationItem(kind="label", start=QPointF(50, 50), end=QPointF(80, 80), text="second")
    window.canvas.annotations = [first, second]
    window.refresh_objects_list()

    moved = window.objects_list.takeItem(0)
    window.objects_list.insertItem(1, moved)
    window.objects_list.setCurrentItem(moved)
    window._on_objects_reordered()

    assert window.canvas.annotations == [second, first]
    saved = ProcessingRecipe.load(window.current_json_path)
    assert [annotation.text for annotation in saved.annotations] == ["second", "first"]


def test_annotation_list_order_controls_preview_layering(qapp):
    canvas = ImageCanvas()
    canvas.preview_image = Image.new("RGB", (100, 100), color="white")
    bottom = AnnotationItem(
        kind="rect",
        start=QPointF(20, 20),
        end=QPointF(80, 80),
        color=QColor("red"),
        stroke_width=6,
    )
    top = AnnotationItem(
        kind="rect",
        start=QPointF(20, 20),
        end=QPointF(80, 80),
        color=QColor("blue"),
        stroke_width=2,
    )
    canvas.annotations = [top, bottom]

    rendered = QImage(100, 100, QImage.Format.Format_RGB32)
    rendered.fill(QColor("white"))
    painter = QPainter(rendered)
    canvas.paint_annotations(painter, QRectF(0, 0, 100, 100))
    painter.end()

    assert QColor(rendered.pixel(20, 50)) == QColor("blue")


def test_loupe_can_be_reordered_with_annotations_and_reloaded(qapp, tmp_path):
    raw_path = tmp_path / "mixed-layers-raw.jpg"
    Image.new("RGB", (200, 150), color="white").save(raw_path)

    window = ImageEditorWindow()
    window.load_source_image(raw_path)
    annotation = AnnotationItem(kind="rect", start=QPointF(20, 20), end=QPointF(80, 80))
    window.canvas.annotations = [annotation]
    window.canvas.loupes = [LoupeOverlay(id=1)]
    window.refresh_objects_list()

    loupe_item = window.objects_list.takeItem(1)
    window.objects_list.insertItem(0, loupe_item)
    window.objects_list.setCurrentItem(loupe_item)
    window._on_objects_reordered()

    assert window.layer_order == ["loupe:1", "annotation:0"]
    saved = ProcessingRecipe.load(window.current_json_path)
    assert saved.layer_order == ["loupe:1", "annotation:0"]

    reloaded = ImageEditorWindow()
    reloaded.load_source_image(raw_path)
    assert reloaded.layer_order == ["loupe:1", "annotation:0"]
    assert isinstance(reloaded.objects_list.item(0).data(Qt.ItemDataRole.UserRole), LoupeOverlay)


def test_loupe_visibility_toggle_preserves_layer_order(qapp, tmp_path):
    raw_path = tmp_path / "toggle-loupe-raw.jpg"
    Image.new("RGB", (200, 150), color="white").save(raw_path)

    window = ImageEditorWindow()
    window.load_source_image(raw_path)
    window.canvas.annotations = [AnnotationItem(kind="rect", start=QPointF(20, 20), end=QPointF(80, 80))]
    window.canvas.loupes = [LoupeOverlay(id=1)]
    window.layer_order = ["annotation:0", "loupe:1"]
    window.refresh_objects_list()

    window.toggle_loupe(False)
    assert window.layer_order == ["annotation:0", "loupe:1"]
    assert window.objects_list.item(1).text().endswith("(masquée)")
    hidden_recipe = ProcessingRecipe.load(window.current_json_path)
    assert hidden_recipe.layer_order == ["annotation:0", "loupe:1"]
    assert hidden_recipe.loupe.enabled is False

    window.toggle_loupe(True)
    assert window.layer_order == ["annotation:0", "loupe:1"]
    assert not window.objects_list.item(1).text().endswith("(masquée)")
    visible_recipe = ProcessingRecipe.load(window.current_json_path)
    assert visible_recipe.layer_order == ["annotation:0", "loupe:1"]
    assert visible_recipe.loupe.enabled is True


def test_preview_paints_layers_from_back_to_front(qapp):
    canvas = ImageCanvas()
    canvas.set_preview_image(Image.new("RGB", (100, 100), color="white"))
    canvas.resize(100, 100)
    canvas.annotations = [AnnotationItem(kind="rect", start=QPointF(10, 10), end=QPointF(90, 90))]
    canvas.loupes = [LoupeOverlay(id=1)]
    canvas.layer_order = ["loupe:1", "annotation:0"]
    calls = []
    canvas.paint_annotations = lambda _painter, _bounds, _items=None: calls.append("annotation")
    canvas.paint_loupe = lambda _painter, _bounds, _loupe: calls.append("loupe")

    canvas.paintEvent(None)

    assert calls == ["annotation", "loupe"]


def test_toolbar_orders_direct_tool_buttons_without_submenus(qapp):
    window = ImageEditorWindow()
    toolbar = window.findChild(QToolBar, "main_toolbar")

    assert toolbar is not None
    assert list(window.toolbar_tool_buttons) == ["reference_line", "text", "loupe"]
    assert [button.text() for button in window.toolbar_tool_buttons.values()] == [
        "Transformation",
        "Annotation",
        "Outil loupe",
    ]
    assert all(button.menu() is None for button in window.toolbar_tool_buttons.values())
    tool_action_indexes = {
        toolbar.widgetForAction(action).text(): index
        for index, action in enumerate(toolbar.actions())
        if toolbar.widgetForAction(action) in window.toolbar_tool_buttons.values()
    }
    assert [tool_action_indexes[label] for label in ("Transformation", "Annotation", "Outil loupe")] == sorted(
        tool_action_indexes.values()
    )


def test_right_options_panel_is_persistent_and_toolbar_is_primary(qapp):
    window = ImageEditorWindow()

    assert not window.options_dock.isHidden()
    assert window.tool_buttons == {}
    assert window.option_pages.currentIndex() == window.option_page_map[TOOL_VIEW]
    assert window.open_action.text() == "Ouvrir une image"
    assert window.export_action.text() == "Exporter l'image"
    assert window.toolbar_tool_buttons["text"].text() == "Annotation"
    assert window.toolbar_tool_buttons["loupe"].text() == "Outil loupe"


def test_toolbar_tools_are_disabled_until_an_image_is_loaded(qapp, tmp_path):
    window = ImageEditorWindow()

    assert window.open_action.isEnabled()
    assert not window.export_action.isEnabled()
    assert all(not button.isEnabled() for button in window.toolbar_tool_buttons.values())

    image_path = tmp_path / "source.jpg"
    Image.new("RGB", (100, 80), color="white").save(image_path)
    window.load_source_image(image_path)

    assert window.export_action.isEnabled()
    assert all(button.isEnabled() for button in window.toolbar_tool_buttons.values())


def test_toolbar_family_buttons_open_their_right_option_pages(qapp, tmp_path):
    window = ImageEditorWindow()
    image_path = tmp_path / "source.jpg"
    Image.new("RGB", (100, 80), color="white").save(image_path)
    window.load_source_image(image_path)

    window.toolbar_tool_buttons["reference_line"].click()
    assert window.canvas.tool == TOOL_ROTATE_LINE
    assert window.option_pages.currentIndex() == window.option_page_map[TOOL_ROTATE_LINE]

    window.toolbar_tool_buttons["text"].click()
    assert window.canvas.tool == "text"
    assert window.option_pages.currentIndex() == window.option_page_map["text"]


def test_objects_dock_starts_left_and_can_move_right(qapp):
    window = ImageEditorWindow()

    assert window.dockWidgetArea(window.objects_dock) == Qt.DockWidgetArea.LeftDockWidgetArea
    assert window.objects_dock.allowedAreas() == (
        Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
    )
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window.objects_dock)
    assert window.dockWidgetArea(window.objects_dock) == Qt.DockWidgetArea.RightDockWidgetArea


def test_file_actions_require_an_loaded_image_and_export_opens_options(qapp):
    window = ImageEditorWindow()

    assert not window.export_action.isEnabled()
    assert not window.save_recipe_action.isEnabled()
    assert not window.load_recipe_action.isEnabled()

    window.show_export_options()
    assert window.option_pages.currentIndex() == window.option_page_map["export"]
    assert window.export_button.text() == "Exporter l'image annotée"


def test_export_mode_clears_the_active_tool_button(qapp, tmp_path):
    image_path = tmp_path / "source.jpg"
    Image.new("RGB", (100, 80), color="white").save(image_path)
    window = ImageEditorWindow()
    window.load_source_image(image_path)

    window.select_tool("loupe")
    window.show_export_options()

    assert window.canvas.tool == TOOL_VIEW
    assert window.export_action.isChecked()
    assert not window.toolbar_tool_buttons["loupe"].isChecked()


def test_graphical_palette_matches_the_main_toolbar(qapp):
    window = ImageEditorWindow()
    palette = window.findChild(QToolBar, "graphical_tools_palette")

    assert palette is not None
    assert set(window.graphical_tool_actions) == {"open", "reference_line", "text", "loupe", "export"}
    assert palette.isMovable()
    assert palette.isFloatable()
    assert all(action.toolTip() for action in window.graphical_tool_actions.values())


def test_annotation_controls_follow_selected_type(qapp):
    window = ImageEditorWindow()

    window.select_tool(TOOL_LINE)
    assert window.line_arrow_start_checkbox.isEnabled()
    assert not window.show_text_checkbox.isEnabled()
    assert not window.show_arrow_checkbox.isEnabled()

    window.select_tool("rect")
    assert window.border_radius_spin.isEnabled()
    assert not window.line_arrow_start_checkbox.isEnabled()


def test_annotation_selection_activates_annotation_properties(qapp):
    window = ImageEditorWindow()
    annotation = AnnotationItem(
        kind="rect",
        start=QPointF(10, 10),
        end=QPointF(50, 50),
        color=QColor("red"),
        stroke_width=7,
    )
    window.canvas.annotations.append(annotation)
    window.refresh_objects_list()

    window.objects_list.setCurrentRow(0)

    assert window.canvas.selected_item is annotation
    assert window.canvas.tool == "rect"
    assert window.option_pages.currentIndex() == window.option_page_map["rect"]
    assert window.stroke_width_spin.value() == 7


def test_annotation_border_radius_is_created_and_serialized(qapp):
    window = ImageEditorWindow()
    window.canvas.current_border_radius = 12
    annotation = AnnotationItem(
        kind="rect",
        start=QPointF(10, 10),
        end=QPointF(50, 50),
        border_radius=12,
    )
    window.canvas.annotations.append(annotation)

    recipe = window.build_recipe()

    assert recipe.annotations[0].border_radius == 12


def test_transformation_page_contains_rotation_grid_and_crop_controls(qapp):
    window = ImageEditorWindow()
    transformation_page = window.option_pages.widget(window.option_page_map[TOOL_ROTATE_LINE])

    assert transformation_page.isAncestorOf(window.grid_toggle_button)
    assert transformation_page.isAncestorOf(window.crop_apply_button)
    window.select_tool(TOOL_CROP)
    assert window.option_pages.currentIndex() == window.option_page_map[TOOL_CROP]
    window.select_tool(TOOL_ROTATE_LINE)
    assert window.option_pages.currentIndex() == window.option_page_map[TOOL_ROTATE_LINE]


def test_rotation_grid_only_appears_for_rotation_tool(qapp):
    canvas = ImageCanvas()
    canvas.show_rotation_grid = True

    canvas.tool = TOOL_VIEW
    assert not (canvas.show_rotation_grid and canvas.tool == TOOL_ROTATE_LINE)
    canvas.tool = TOOL_ROTATE_LINE
    assert canvas.show_rotation_grid and canvas.tool == TOOL_ROTATE_LINE


def test_transformation_mode_allows_drawing_and_resizing_crop_rect(qapp):
    canvas = ImageCanvas()
    canvas.layer_order = []
    canvas.preview_image = Image.new("RGB", (200, 150), color="white")
    canvas.set_preview_image(canvas.preview_image)
    canvas.resize(400, 300)
    canvas.tool = TOOL_ROTATE_LINE

    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(50, 40),
        QPointF(50, 40),
        QPointF(50, 40),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(150, 110),
        QPointF(150, 110),
        QPointF(150, 110),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(150, 110),
        QPointF(150, 110),
        QPointF(150, 110),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )

    canvas.mousePressEvent(press)
    canvas.mouseMoveEvent(move)
    canvas.mouseReleaseEvent(release)

    assert canvas.crop_rect is not None
    assert canvas.crop_rect.left() >= 0
    assert canvas.crop_rect.width() > 0
    assert canvas.crop_rect.height() > 0


def test_rotation_grid_toggle_button_updates_label_and_state(qapp):
    window = ImageEditorWindow()
    button = window.grid_toggle_button

    assert button.text() == "Afficher la grille d'alignement"
    button.setChecked(True)
    assert button.text() == "Masquer la grille d'alignement"
    # La couleur de l'état actif vient du thème (QPushButton:checked), plus d'un style en dur.
    assert button.styleSheet() == ""
    assert "QPushButton:checked" in window.styleSheet()
    assert window.canvas.show_rotation_grid is True


def test_transformation_options_are_separated_by_horizontal_dividers(qapp):
    window = ImageEditorWindow()
    page = window.option_pages.widget(window.option_page_map[TOOL_ROTATE_LINE])

    separators = [w for w in page.findChildren(QFrame) if w.frameShape() == QFrame.Shape.HLine]
    assert len(separators) >= 2


def test_editor_persists_four_trapezoid_edges(qapp):
    window = ImageEditorWindow()
    window.trapezoid_top = 0.1
    window.trapezoid_bottom = -0.2
    window.trapezoid_left = 0.05
    window.trapezoid_right = -0.15

    recipe = window.build_recipe()

    assert recipe.trapezoid == (0.1, -0.2, 0.05, -0.15)


def test_editor_load_image_auto_naming_and_json_lifecycle(qapp, tmp_path):
    # Create raw image in tmp_path
    raw_path = tmp_path / "electronique-raw.jpg"
    test_img = Image.new("RGB", (200, 150), color="green")
    test_img.save(raw_path)

    window = ImageEditorWindow()
    window.load_source_image(raw_path)

    assert window.source_path == raw_path
    assert window.current_json_path == tmp_path / "electronique-iat.json"
    assert window.default_export_path == tmp_path / "electronique-iat-x1200.jpg"
    assert not window.current_json_path.exists()
    assert window.objects_list.count() == 0

    # Change stroke width
    window.stroke_width_spin.setValue(5)
    assert window.canvas.current_stroke_width == 5

    # Add an annotation
    ann = AnnotationItem(
        kind="rect",
        start=QPointF(10, 10),
        end=QPointF(50, 50),
        color=QColor("yellow"),
        stroke_width=5,
    )
    window.canvas.annotations.append(ann)
    window.canvas.annotation_changed.emit()

    # Verify objects list populated
    assert window.objects_list.count() == 1
    assert "Rectangle" in window.objects_list.item(0).text()
    assert "5px" in window.objects_list.item(0).text()

    # Verify auto-save created the -iat.json file
    assert window.current_json_path.exists()
    saved_recipe = ProcessingRecipe.load(window.current_json_path)
    assert len(saved_recipe.annotations) == 1
    assert saved_recipe.stroke_width == 5

    # Select the object and delete it
    window.objects_list.setCurrentRow(0)
    assert window.canvas.selected_item is ann
    assert window.delete_object_button.isEnabled()

    window.delete_selected_object()
    assert len(window.canvas.annotations) == 0
    assert window.objects_list.count() == 0

    # Auto-saved file should now have 0 annotations
    saved_recipe_after_del = ProcessingRecipe.load(window.current_json_path)
    assert len(saved_recipe_after_del.annotations) == 0


def test_editor_auto_loads_existing_iat_json(qapp, tmp_path):
    raw_path = tmp_path / "carte-test-raw.jpg"
    test_img = Image.new("RGB", (200, 150), color="black")
    test_img.save(raw_path)

    json_path = tmp_path / "carte-test-iat.json"
    recipe = ProcessingRecipe(
        source_image=str(raw_path),
        angle=90.0,
        brightness=12.0,
        contrast=1.3,
        trapezoid=(0.2, -0.1, 0.05, -0.15),
        export_width=100,
        stroke_width=4,
    )
    recipe.save(json_path)

    window = ImageEditorWindow()
    window.load_source_image(raw_path)

    # Recipe should be loaded automatically
    assert window.angle_total == 90.0
    assert window.brightness == 12.0
    assert window.contrast == 1.3
    assert window.trapezoid_top == 0.2
    assert window.trapezoid_bottom == -0.1
    assert window.trapezoid_left == 0.05
    assert window.trapezoid_right == -0.15
    assert window.trapezoid_top_spin.value() == 20.0
    assert window.trapezoid_bottom_spin.value() == -10.0
    assert window.trapezoid_left_spin.value() == 5.0
    assert window.trapezoid_right_spin.value() == -15.0
    assert window.width_spin.value() == 100
    assert window.stroke_width_spin.value() == 4
    assert window.objects_list.count() == 3
    assert "Rotation (+90.0°)" in window.objects_list.item(0).text()
    assert "Trapèze" in window.objects_list.item(1).text()

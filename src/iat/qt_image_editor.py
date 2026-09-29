#!/usr/bin/env python3
# File Name: qt_image_editor.py
# Description: A Qt-based image annotation tool.
# Developer: ArnauldDev
# Created Date: 2026-09-08
# Last Modified: 2026-09-26


from __future__ import annotations

import json
import math
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

from PIL import Image
from PyQt6.QtCore import QItemSelectionModel, QPoint, QPointF, QRectF, QSize, QSettings, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QColor,
    QTextDocument,
    QFont,
    QFontMetrics,
    QIcon,
    QImage,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QDesktopServices,
)
from PyQt6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtSvg import QSvgRenderer

from iat.config import AppConfig, config, load_dotenv, update_config_in_place
from iat.image_processor import (
    Annotation,
    LoupeSpec,
    ProcessingRecipe,
    apply_brightness_contrast,
    apply_trapezoid_correction,
    compute_associated_paths,
    load_image,
    make_preview,
    next_annotation_id,
    next_loupe_id,
    process_image_with_recipe,
    rotate_image,
)

#: Packaged application icon (works regardless of the current working
#: directory, including when frozen with PyInstaller).
APP_ICON_PATH = Path(__file__).resolve().parent / "resources" / "icons" / "app_icon.ico"
ICONS_DIRECTORY = APP_ICON_PATH.parent
APP_LOGO_PATH = Path(__file__).resolve().parent / "resources" / "logo_app_iat.svg"
# Valeur pour la taille du logo, à placer au début du fichier ou du composant
APP_LOGO_SIZE = 220  # modifier uniquement cette valeur pour changer la taille dans la fenêtre "À propos"

#: Application metadata surfaced in the "À propos" dialog.
APP_NAME = "Image Annotation Tool (IAT)"
APP_VERSION = "1.0.0"
APP_LICENSE = "Apache License 2.0"
APP_SOURCE = "https://src.koda.cnrs.fr/cbi-plateau-mecatronique/ressources/image-annotation-tool/"
APP_LAB_INFO = (
    "Arnauld BIGANZOLI\n"
    "Plateau Technique Mécatronique\n"
    "Centre de Biologie Intégrative (CBI) — CNRS FR3743"
)

#: Tools selectable in the toolbox. "view" is the default, non-destructive
#: cursor mode used for panning/inspecting the canvas.
TOOL_VIEW = "view"
TOOL_ROTATE_LINE = "reference_line"
TOOL_TEXT = "text"
TOOL_RECT = "rect"
TOOL_CIRCLE = "circle"
TOOL_LINE = "line"
TOOL_LOUPE = "loupe"
TOOL_CROP = "crop"

#: Sub-tools grouped under the single "Annotation" toolbar button: the shape
#: currently drawn is chosen via the shape-selector row in its options panel.
ANNOTATION_FAMILY_TOOLS: frozenset[str] = frozenset({TOOL_TEXT, TOOL_RECT, TOOL_CIRCLE, TOOL_LINE})

#: On-screen pixel tolerance used to grab a handle (label anchor, loupe
#: centre/arrow tip, rectangle corner, ...) when picking items to drag.
HANDLE_HIT_RADIUS = 12.0

#: Curated colour swatches offered in the tools palette.
COLOR_PALETTE = [
    "#FFFF00",
    "#FF3B30",
    "#FF9500",
    "#34C759",
    "#66D9EF",
    "#0A84FF",
    "#FF2D95",
    "#FFFFFF",
    "#000000",
]

#: Matches a filename that already starts with a date (e.g. "20260901-..."
#: or "2026-09-01_..."), used to decide whether to prefix an export name.
_LEADING_DATE_RE = re.compile(r"^\d{4}[-_]?\d{2}[-_]?\d{2}(?:[-_]|$)")


#: Human-readable label and help text for each tool, reused by the tools
#: palette's tooltips and by the "Aide sur les outils" dialog.
TOOL_DESCRIPTIONS: dict[str, tuple[str, str]] = {
    TOOL_VIEW: (
        "Déplacer",
        "Sélectionne et déplace les éléments déjà placés : glissez une étiquette, "
        "une loupe, le rognage ou l'extrémité d'une flèche pour les repositionner. Il ne crée rien de nouveau. "
        "Ce glisser-déposer sur le contour d'un objet fonctionne aussi lorsqu'un autre outil est actif. "
        "Maintenez Ctrl pendant un tracé ou un déplacement pour vous accrocher à la grille.",
    ),
    TOOL_ROTATE_LINE: (
        "Transformation",
        "Grille d'alignement, rotation, correction trapézoïdale et rognage de l'image : "
        "glissez sur l'image pour dessiner la zone de rognage, puis ajustez-la avec ses poignées.",
    ),
    TOOL_TEXT: (
        "Étiquette texte",
        "Glissez depuis l'emplacement du texte vers l'élément à désigner. "
        "Double-cliquez une étiquette existante pour modifier son texte.",
    ),
    TOOL_RECT: (
        "Zone rectangulaire",
        "Glissez pour dessiner un cadre rectangulaire en surbrillance autour d'une zone d'intérêt.",
    ),
    TOOL_CIRCLE: (
        "Zone ronde",
        "Glissez pour dessiner un cadre ovale/circulaire en surbrillance autour d'une zone d'intérêt.",
    ),
    TOOL_LINE: (
        "Ligne",
        "Glissez pour tracer une ligne droite ; les extrémités peuvent afficher une flèche via les cases à cocher dédiées.",
    ),
    TOOL_LOUPE: (
        "Loupe",
        "Glissez de l'emplacement de la loupe vers la zone à agrandir : "
        "un médaillon zoomé et une flèche seront insérés à l'export. "
        "« Nouvelle loupe » ajoute une loupe supplémentaire ; la molette règle le zoom.",
    ),
    TOOL_CROP: (
        "Rogner",
        "Glissez pour définir la zone de l'image à conserver, puis validez avec « Appliquer le rognage ».",
    ),
}


#: Outils exclus de la barre d'outils principale et du dock outils gauche.
#: TOOL_ROTATE_LINE reste disponible via le dock Rotation directement.
_TOOLBAR_EXCLUDED_TOOLS: frozenset[str] = frozenset({TOOL_ROTATE_LINE})

#: Nombre maximum de fichiers récents mémorisés.
_MAX_RECENT_FILES = 10
#: Nombre maximum d'étapes mémorisées pour « Annuler » (Ctrl+Z).
_MAX_HISTORY = 100
#: Décalage (pixels de l'aperçu) appliqué à chaque collage successif.
_PASTE_OFFSET = 20.0
#: Préréglages de largeur d'export proposés dans le panneau « Exporter l'image ».
EXPORT_WIDTH_PRESETS = (800, 1200, 1920)
#: Extensions d'image acceptées à l'ouverture et par glisser-déposer.
IMAGE_FILE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")

#: Chemin du fichier JSON stockant l'historique des fichiers récents.
_RECENT_FILES_PATH = Path.home() / ".config" / "iat" / "recent_files.json"
#: Bundled themes: "<projet>/themes" from the sources, "<_MEIPASS>/themes" once
#: frozen by PyInstaller (see ``image_annotation_tool.spec``).
_THEMES_DIRECTORY = (
    Path(getattr(sys, "_MEIPASS", "")) / "themes"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2] / "themes"
)
_THEME_ICON_NAMES = ("app_icon.ico", "app_icon.png", "icon.ico", "icon.png")
_THEME_DISPLAY_NAMES = {"clair": "Clair", "sombre": "Sombre", "cbi": "CBI"}
#: Directive (placed in a QSS comment) giving the colour used to tint SVG icons.
_THEME_ICON_COLOR_RE = re.compile(r"iat-icon-color\s*:\s*(#[0-9A-Fa-f]{3,8})")
#: Directive giving the icon colour on a checked (accent-filled) tool button.
_THEME_ICON_CHECKED_COLOR_RE = re.compile(r"iat-icon-checked-color\s*:\s*(#[0-9A-Fa-f]{3,8})")
#: Theme icon reference "url(@icons/<file>.svg)", resolved to a tinted copy of the bundled icon.
_THEME_ICON_URL_RE = re.compile(r"url\(\s*['\"]?@icons/([\w.-]+\.svg)['\"]?\s*\)")
#: Placeholder colour used by the bundled SVG icons, replaced when tinting.
_SVG_PLACEHOLDER_COLORS = ("#444444", "#444")

#: SVG icons of the graphical tools palette (in ``resources/icons``).
_PALETTE_ICON_FILES = {
    "open": "open.svg",
    TOOL_ROTATE_LINE: "transformation.svg",
    TOOL_TEXT: "annotation.svg",
    TOOL_LOUPE: "loupe.svg",
    "export": "export.svg",
}

#: Icons shown left of each link of the "À propos" window (in ``resources/icons``).
#: A custom UT logo can be provided as ``logo_ut.svg``/``logo_ut.png`` in the icons folder.
_ABOUT_LINK_ICON_FILES = {
    "source": "gitlab.svg",
    "mail": "mail.svg",
    "web": "web.svg",
    "ut": "university.svg",
}
APP_CONTACT_EMAIL = "arnauld.biganzoli@utoulouse.fr"
APP_LAB_URL = "https://cbi-toulouse.fr/plateau-mecatronique/"
APP_UT_URL = "https://www.utoulouse.fr/"

#: Translation files "translations/<code>.json" (French source text → translated text).
_TRANSLATIONS_DIRECTORY = (
    Path(getattr(sys, "_MEIPASS", "")) / "translations"
    if getattr(sys, "frozen", False)
    else Path(__file__).resolve().parents[2] / "translations"
)
#: Language of the texts written in the code (no translation file needed).
SOURCE_LANGUAGE = "fr"
SOURCE_LANGUAGE_NAME = "Français"
#: Key of a translation file giving the displayed name of its language.
_LANGUAGE_NAME_KEY = "_language_name"

#: Default location of each configurable resource folder ("Chemins des ressources").
DEFAULT_RESOURCE_PATHS: dict[str, Path] = {
    "icons": ICONS_DIRECTORY,
    "themes": _THEMES_DIRECTORY,
    "translations": _TRANSLATIONS_DIRECTORY,
}
RESOURCE_PATH_LABELS = {
    "icons": "Icônes",
    "themes": "Thèmes",
    "translations": "Traductions",
}


class Translator:
    """Minimal translation engine based on JSON catalogues.

    Each ``translations/<code>.json`` file maps a French source text to its
    translation. The reverse lookup lets the interface be re-translated from
    any language to any other one without remembering the original texts.
    """

    def __init__(self) -> None:
        """
        Description: Start in the source language (French), without any catalogue.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 2

        @returns
        """
        self.language = SOURCE_LANGUAGE
        self.catalog: dict[str, str] = {}
        #: Translated text → French source text, for every loaded catalogue.
        self.reverse: dict[str, str] = {}

    @staticmethod
    def available_languages(directory: Path) -> dict[str, str]:
        """
        Description: Return {code: displayed name} for French plus every valid "<code>.json" catalogue of ``directory``.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param directory

        @returns
        """
        languages = {SOURCE_LANGUAGE: SOURCE_LANGUAGE_NAME}
        if directory.is_dir():
            for path in sorted(directory.glob("*.json")):
                catalog = Translator.read_catalog(path)
                if catalog is not None and path.stem != SOURCE_LANGUAGE:
                    languages[path.stem] = catalog.get(_LANGUAGE_NAME_KEY, path.stem)
        return languages

    @staticmethod
    def read_catalog(path: Path) -> dict[str, str] | None:
        """
        Description: Read one JSON catalogue; return None when it is missing or invalid.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param path

        @returns
        """
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError):
            return None
        if not isinstance(data, dict):
            return None
        return {str(key): str(value) for key, value in data.items() if isinstance(value, str)}

    def set_language(self, code: str, directory: Path) -> bool:
        """
        Description: Activate the catalogue ``code`` of ``directory`` (French needs none); return False if it cannot be loaded.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param code
        @param directory

        @returns
        """
        catalog: dict[str, str] = {}
        if code != SOURCE_LANGUAGE:
            loaded = self.read_catalog(directory / f"{code}.json")
            if loaded is None:
                return False
            catalog = loaded
        # La table inverse couvre toutes les langues pour pouvoir repartir de n'importe laquelle.
        for path in directory.glob("*.json") if directory.is_dir() else ():
            for source, translated in (self.read_catalog(path) or {}).items():
                if source != _LANGUAGE_NAME_KEY:
                    self.reverse.setdefault(translated, source)
        self.language = code
        self.catalog = {key: value for key, value in catalog.items() if key != _LANGUAGE_NAME_KEY}
        return True

    def translate(self, text: str) -> str:
        """
        Description: Translate a French source text into the active language (unchanged when unknown).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param text

        @returns
        """
        return self.catalog.get(text, text)

    def retranslate(self, text: str) -> str:
        """
        Description: Translate a text currently displayed in any known language into the active language.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param text

        @returns
        """
        if not text:
            return text
        return self.translate(self.reverse.get(text, text))


#: Shared translator of the application.
translator = Translator()


def tr(text: str) -> str:
    """
    Description: Translate a French interface text into the active language.

    @author ArnauldDev
    @created 2026-09-23
    @modified 2026-09-23
    @version 1

    @param text

    @returns
    """
    return translator.translate(text)


def tinted_svg_icon(
    path: Path, color: QColor | str, size: int = 32, checked_color: QColor | str | None = None
) -> QIcon:
    """
    Description: Render a monochrome SVG icon in ``color`` (its placeholder grey is replaced), crisp at several sizes; ``checked_color`` provides the variant shown when the tool button is checked.

    @author ArnauldDev
    @created 2026-09-23
    @modified 2026-09-23
    @version 3

    @param path
    @param color
    @param size
    @param checked_color

    @returns
    """
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return QIcon()
    icon = QIcon()
    variants = [(color, QIcon.State.Off)]
    if checked_color is not None:
        variants.append((checked_color, QIcon.State.On))
    for variant_color, state in variants:
        svg = source
        for placeholder in _SVG_PLACEHOLDER_COLORS:
            svg = re.sub(re.escape(placeholder) + r"(?![0-9A-Fa-f])", QColor(variant_color).name(), svg, flags=re.IGNORECASE)
        renderer = QSvgRenderer(svg.encode("utf-8"))
        if not renderer.isValid():
            return QIcon()
        for side in {16, 24, size, size * 2}:
            pixmap = QPixmap(side, side)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            icon.addPixmap(pixmap, QIcon.Mode.Normal, state)
    return icon


@dataclass(eq=False)
class AnnotationItem:
    """UI-side representation of an annotation, in *preview* pixel space.

    Compared by identity (``eq=False``) so two identical shapes remain two
    distinct objects in the layer list.
    """

    kind: str
    start: QPointF | None = None
    end: QPointF | None = None
    text: str = ""
    color: QColor = field(default_factory=lambda: QColor("yellow"))
    stroke_width: int = 3
    border_radius: int = 0
    #: Only used by "label" annotations: whether the pointer arrow towards
    #: the annotated target is drawn, and whether the label box is a
    #: rounded rectangle ("rect") or an ellipse ("round").
    show_arrow: bool = True
    shape: str = "rect"
    #: "label" only: arrow thickness, independent of the box's stroke_width.
    arrow_stroke_width: int = 2
    #: "label" only: whether the text is drawn inside the box.
    show_text: bool = True
    #: "label" only: whether the box background is filled (True) or transparent.
    fill_enabled: bool = True
    #: "label" only: render the text in bold.
    bold_text: bool = False
    #: "line" only: draw an arrowhead at the start/end point.
    line_arrow_start: bool = False
    line_arrow_end: bool = False
    #: Unique identifier, assigned when the annotation is committed to the
    #: canvas (see ``ImageCanvas._commit_new_annotation``). ``0`` marks a
    #: draft that hasn't been added to ``ImageCanvas.annotations`` yet.
    id: int = 0

    @property
    def layer_token(self) -> str:
        """Token of this annotation inside the layer order."""
        return f"annotation:{self.id}"


@dataclass(eq=False)
class LoupeOverlay:
    """UI-side representation of one loupe overlay, in *preview* pixel space.

    Several loupes can coexist; each one has a unique ``id`` referenced in the
    layer order as ``"loupe:<id>"``. Compared by identity (``eq=False``).
    """

    enabled: bool = True
    center: QPointF = field(default_factory=lambda: QPointF(200, 200))
    radius: int = 90
    zoom: float = 2.0
    arrow: tuple[QPointF, QPointF] = field(default_factory=lambda: (QPointF(180, 120), QPointF(120, 100)))
    color: QColor = field(default_factory=lambda: QColor("#66D9EF"))
    #: Rotation (degrees, clockwise) applied to the magnified content only.
    rotation: float = 0.0
    #: Thickness of the loupe's outline ring, independent of other tools.
    stroke_width: int = 4
    #: Thickness of the arrow pointing to the magnified target, independent of stroke_width.
    arrow_stroke_width: int = 2
    #: Unique identifier, auto-incremented when a loupe is added.
    id: int = 1

    @property
    def layer_token(self) -> str:
        """Token of this loupe inside the layer order."""
        return f"loupe:{self.id}"


class ImageCanvas(QWidget):
    """Displays the low-resolution preview image and handles all interactive
    editing tools (annotations, loupe, rotation-alignment line).

    Every editing operation performed here works exclusively on the preview
    image so that the interface stays fluid even when the source photograph
    is very large. Coordinates are converted back to full-resolution pixel
    space only when the final :class:`~iat.image_processor.ProcessingRecipe`
    is built for export.
    """

    annotation_changed = pyqtSignal()
    item_selected = pyqtSignal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-26
        @version 11

        @param parent

        @returns
        """
        super().__init__(parent)
        self.preview_image: Image.Image | None = None
        self.base_pixmap: QPixmap | None = None
        self.annotations: list[AnnotationItem] = []
        #: Loupe overlays, each referenced as "loupe:<id>" in ``layer_order``.
        self.loupes: list[LoupeOverlay] = []
        self.layer_order: list[str] = []
        self.tool = TOOL_VIEW
        self.reference_points: list[QPointF] = []
        self.dragging = False
        self.drag_start = QPointF()
        self.last_mouse = QPointF()
        self.draft_annotation: AnnotationItem | None = None
        self.show_rotation_grid = False
        #: When set, describes what an in-progress drag in TOOL_VIEW mode is
        #: moving (e.g. "label_body", "loupe_arrow_end", ...). ``None`` means
        #: no existing item is currently being repositioned.
        self.drag_mode: str | None = None
        self.drag_target: AnnotationItem | LoupeOverlay | None = None
        #: Mouse position (image space, never snapped) where the current drag
        #: started, and a copy of the dragged geometry at that moment: moves are
        #: recomputed from this origin so Ctrl-snapping never accumulates drift.
        self._drag_press_point = QPointF()
        self._drag_origin: tuple | None = None
        #: Crop rectangle currently being drawn/adjusted, in preview-image
        #: pixel space. Cleared once the user applies or resets the crop.
        self.crop_rect: QRectF | None = None
        self.crop_drag_mode: str | None = None
        #: Colour applied to the next label/highlight-zone/loupe created,
        #: chosen from the tools palette.
        self.current_color = QColor("yellow")
        self.current_stroke_width: int = config.default_stroke_width
        self.current_border_radius: int = 0
        #: Defaults applied to the next "label" annotation created.
        self.current_show_arrow: bool = True
        self.current_label_shape: str = "rect"
        self.current_arrow_stroke_width: int = 2
        self.current_show_text: bool = True
        self.current_fill_enabled: bool = True
        self.current_bold_text: bool = False
        #: Defaults applied to the next "line" annotation created.
        self.current_line_arrow_start: bool = False
        self.current_line_arrow_end: bool = False
        #: Primary selection (object driving the options panel, or "crop"), and
        #: every selected visual object when several are selected at once.
        self._selected_item: AnnotationItem | LoupeOverlay | str | None = None
        self._selection: list[AnnotationItem | LoupeOverlay] = []
        #: Geometry, at press time, of the other objects moved with a group drag.
        self._group_origins: list[tuple[AnnotationItem | LoupeOverlay, tuple | None]] = []
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    # ------------------------------------------------------------------
    # Selection (simple et multiple)
    # ------------------------------------------------------------------
    @property
    def selected_item(self) -> AnnotationItem | LoupeOverlay | str | None:
        """
        Description: Primary selected object (the one shown in the options panel), or "crop".

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        return self._selected_item

    @selected_item.setter
    def selected_item(self, value: AnnotationItem | LoupeOverlay | str | None) -> None:
        """
        Description: Select a single object (or "crop", or nothing), replacing any multiple selection.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-26
        @version 9

        @param value

        @returns
        """
        # Une sélection simple remplace toute sélection multiple.
        self._selected_item = value
        self._selection = [value] if isinstance(value, (AnnotationItem, LoupeOverlay)) else []

    def set_selection(
        self,
        items: list[AnnotationItem | LoupeOverlay],
        primary: AnnotationItem | LoupeOverlay | None = None,
    ) -> None:
        """
        Description: Select several objects at once; ``primary`` (default: the last one) drives the options panel.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param items
        @param primary

        @returns
        """
        unique: list[AnnotationItem | LoupeOverlay] = []
        for item in items:
            if isinstance(item, (AnnotationItem, LoupeOverlay)) and not any(item is kept for kept in unique):
                unique.append(item)
        if primary is None or not any(primary is item for item in unique):
            primary = unique[-1] if unique else None
        self._selected_item = primary
        self._selection = unique

    def selected_objects(self) -> list[AnnotationItem | LoupeOverlay]:
        """
        Description: Every selected visual object still present on the canvas, in selection order.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        present = [*self.annotations, *self.loupes]
        return [item for item in self._selection if any(item is candidate for candidate in present)]

    def is_selected(self, item: object) -> bool:
        """
        Description: Whether ``item`` is part of the current (simple or multiple) selection.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item

        @returns
        """
        return item is self._selected_item or any(item is selected for selected in self._selection)

    def toggle_in_selection(self, item: AnnotationItem | LoupeOverlay) -> None:
        """
        Description: Add ``item`` to the selection, or remove it when already selected (Shift + clic).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item

        @returns
        """
        current = self.selected_objects()
        if any(item is selected for selected in current):
            remaining = [selected for selected in current if selected is not item]
            self.set_selection(remaining, remaining[-1] if remaining else None)
        else:
            self.set_selection([*current, item], item)

    # ------------------------------------------------------------------
    # Géométrie des objets (alignement, distribution, copier/coller)
    # ------------------------------------------------------------------
    def _screen_scale(self) -> float:
        """
        Description: On-screen pixels per preview-image pixel.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        bounds = self._display_bounds()
        if bounds is None or self.preview_image is None or self.preview_image.width == 0:
            return 1.0
        return max(1e-6, bounds.width() / self.preview_image.width)

    def item_bounds(self, item: AnnotationItem | LoupeOverlay) -> QRectF | None:
        """
        Description: Bounding box (preview-image space) used to align an object: the text box of a label, the disc of a loupe, the drawn shape otherwise.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item

        @returns
        """
        if isinstance(item, LoupeOverlay):
            return QRectF(item.center.x() - item.radius, item.center.y() - item.radius, item.radius * 2, item.radius * 2)
        if item.start is None:
            return None
        if item.kind == "label":
            scale = self._screen_scale()
            box = self._label_screen_rect(item, QPointF(0, 0))
            return QRectF(item.start.x(), item.start.y(), box.width() / scale, box.height() / scale)
        if item.end is None:
            return QRectF(item.start, item.start)
        return QRectF(item.start, item.end).normalized()

    @staticmethod
    def translate_item(item: AnnotationItem | LoupeOverlay, delta: QPointF, whole: bool = True) -> None:
        """
        Description: Move an object by ``delta``. With ``whole`` False, a label keeps its arrow target and a loupe keeps the magnified area (only the box/disc moves).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item
        @param delta
        @param whole

        @returns
        """
        if isinstance(item, LoupeOverlay):
            item.center = item.center + delta
            item.arrow = (item.arrow[0] + delta, item.arrow[1] + delta if whole else item.arrow[1])
            return
        if item.start is not None:
            item.start = item.start + delta
        if item.end is not None and (whole or item.kind != "label"):
            item.end = item.end + delta

    def align_selection(self, mode: str) -> bool:
        """
        Description: Align the selected objects ("left", "hcenter", "right", "top", "vcenter", "bottom") on their common bounding box, or on the image when a single object is selected; "grid" snaps each object on the grid; "hdistribute"/"vdistribute" spread the centres evenly (3 objects or more).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param mode

        @returns
        """
        items = [item for item in self.selected_objects() if self.item_bounds(item) is not None]
        if not items or self.preview_image is None:
            return False
        bounds = {id(item): self.item_bounds(item) for item in items}
        if mode == "grid":
            for item in items:
                anchor = item.center if isinstance(item, LoupeOverlay) else item.start
                self.translate_item(item, self.snap_to_grid(anchor) - anchor, whole=False)
            self.update()
            return True
        if mode in ("hdistribute", "vdistribute"):
            if len(items) < 3:
                return False
            horizontal = mode == "hdistribute"
            key = (lambda rect: rect.center().x()) if horizontal else (lambda rect: rect.center().y())
            ordered = sorted(items, key=lambda item: key(bounds[id(item)]))
            first, last = key(bounds[id(ordered[0])]), key(bounds[id(ordered[-1])])
            step = (last - first) / (len(ordered) - 1)
            for index, item in enumerate(ordered[1:-1], start=1):
                shift = first + step * index - key(bounds[id(item)])
                self.translate_item(item, QPointF(shift, 0) if horizontal else QPointF(0, shift), whole=False)
            self.update()
            return True
        if len(items) == 1:
            reference = QRectF(0, 0, self.preview_image.width, self.preview_image.height)
        else:
            reference = QRectF(bounds[id(items[0])])
            for item in items[1:]:
                reference = reference.united(bounds[id(item)])
        for item in items:
            rect = bounds[id(item)]
            dx = dy = 0.0
            if mode == "left":
                dx = reference.left() - rect.left()
            elif mode == "hcenter":
                dx = reference.center().x() - rect.center().x()
            elif mode == "right":
                dx = reference.right() - rect.right()
            elif mode == "top":
                dy = reference.top() - rect.top()
            elif mode == "vcenter":
                dy = reference.center().y() - rect.center().y()
            elif mode == "bottom":
                dy = reference.bottom() - rect.bottom()
            else:
                return False
            self.translate_item(item, QPointF(dx, dy), whole=False)
        self.update()
        return True

    def contextMenuEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Right click: alignment/distribution menu for the selected objects (the object under the cursor is selected first), plus copy, paste and delete.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param event

        @returns
        """
        if self.preview_image is None:
            return
        hit = self._hit_test(QPointF(event.pos()))
        if hit is not None and isinstance(hit[1], (AnnotationItem, LoupeOverlay)) and not self.is_selected(hit[1]):
            self.selected_item = hit[1]
            self.item_selected.emit(self.selected_item)
            self.update()
        menu = self.build_context_menu()
        menu.exec(event.globalPos())

    def build_context_menu(self) -> QMenu:
        """
        Description: Build the right-click menu according to the current selection.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        menu = QMenu(self)
        count = len(self.selected_objects())
        reference = tr("par rapport à l'image") if count == 1 else tr("entre eux")
        align_menu = menu.addMenu(f"{tr('Aligner')} ({reference})")
        align_menu.setEnabled(count >= 1)
        for mode, label in (
            ("left", "Aligner à gauche"),
            ("hcenter", "Centrer horizontalement"),
            ("right", "Aligner à droite"),
            (None, None),
            ("top", "Aligner en haut"),
            ("vcenter", "Centrer verticalement"),
            ("bottom", "Aligner en bas"),
        ):
            if mode is None:
                align_menu.addSeparator()
                continue
            action = align_menu.addAction(tr(label))
            action.triggered.connect(lambda _checked, m=mode: self._run_alignment(m))
        distribute_menu = menu.addMenu(tr("Distribuer"))
        distribute_menu.setEnabled(count >= 3)
        distribute_menu.setToolTip(tr("Nécessite au moins trois objets sélectionnés"))
        for mode, label in (("hdistribute", "Distribuer horizontalement"), ("vdistribute", "Distribuer verticalement")):
            action = distribute_menu.addAction(tr(label))
            action.triggered.connect(lambda _checked, m=mode: self._run_alignment(m))
        grid_action = menu.addAction(tr("Accrocher à la grille"))
        grid_action.setEnabled(count >= 1)
        grid_action.triggered.connect(lambda: self._run_alignment("grid"))
        window = self.window()
        if isinstance(window, ImageEditorWindow):
            menu.addSeparator()
            for action in (window.copy_action, window.paste_action, window.delete_action):
                menu.addAction(action)
        return menu

    def _run_alignment(self, mode: str) -> None:
        """
        Description: Apply an alignment from the context menu, then save it (history and JSON).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param mode

        @returns
        """
        if self.align_selection(mode):
            self.annotation_changed.emit()

    # ------------------------------------------------------------------
    # Loupes
    # ------------------------------------------------------------------
    def effective_layer_order(self) -> list[str]:
        """
        Description: Return the front-to-back layer tokens, falling back to annotations then visible loupes.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        return self.layer_order or [
            *[annotation.layer_token for annotation in self.annotations],
            *[loupe.layer_token for loupe in self.loupes if loupe.enabled],
        ]

    def annotation_for_token(self, token: str) -> AnnotationItem | None:
        """
        Description: Return the annotation referenced by an "annotation:<id>" layer token.

        @author ArnauldDev
        @created 2026-09-27
        @modified 2026-09-27
        @version 1

        @param token

        @returns
        """
        return next((item for item in self.annotations if item.layer_token == token), None)

    def loupe_for_token(self, token: str) -> LoupeOverlay | None:
        """
        Description: Return the loupe referenced by a "loupe:<id>" layer token.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param token

        @returns
        """
        return next((loupe for loupe in self.loupes if loupe.layer_token == token), None)

    def active_loupe(self) -> LoupeOverlay | None:
        """
        Description: Return the selected loupe, otherwise the front-most one in the layer order.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if isinstance(self.selected_item, LoupeOverlay) and self.selected_item in self.loupes:
            return self.selected_item
        for token in self.effective_layer_order():
            loupe = self.loupe_for_token(token)
            if loupe is not None:
                return loupe
        return self.loupes[0] if self.loupes else None

    def add_loupe(self, center: QPointF, target: QPointF | None = None) -> LoupeOverlay:
        """
        Description: Create a new visible loupe with the next free identifier and the current tool defaults.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param center
        @param target

        @returns
        """
        template = self.active_loupe()
        loupe = LoupeOverlay(
            id=next_loupe_id(self.loupes),
            center=QPointF(center),
            arrow=(QPointF(center), QPointF(target if target is not None else center)),
            color=QColor(self.current_color),
        )
        if template is not None:
            # La nouvelle loupe reprend le réglage de la loupe courante.
            loupe.radius = template.radius
            loupe.zoom = template.zoom
            loupe.stroke_width = template.stroke_width
            loupe.arrow_stroke_width = template.arrow_stroke_width
        self.loupes.append(loupe)
        # Une nouvelle loupe est placée au premier plan.
        if self.layer_order or self.annotations:
            self.layer_order.insert(0, loupe.layer_token)
        return loupe

    def _commit_new_annotation(self, item: AnnotationItem) -> None:
        """
        Description: Assign a freshly drawn annotation its unique id, add it to the canvas, and place it at the front of the layer stack (mirroring ``add_loupe``).

        @author ArnauldDev
        @created 2026-09-27
        @modified 2026-09-27
        @version 1

        @param item

        @returns
        """
        # Un nouvel objet est placé au premier plan, comme pour les loupes ;
        # évalué avant l'ajout pour ne pas se compter lui-même.
        has_existing_objects = bool(self.layer_order) or bool(self.annotations) or bool(self.loupes)
        item.id = next_annotation_id(self.annotations)
        self.annotations.append(item)
        if has_existing_objects:
            self.layer_order.insert(0, item.layer_token)

    def set_preview_image(self, image: Image.Image | None) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param image

        @returns
        """
        self.preview_image = image
        self.update_pixmap()
        self.update()

    def update_pixmap(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.preview_image is None:
            self.base_pixmap = None
            return

        image = self.preview_image.convert("RGBA")
        qim = QImage(image.tobytes(), image.width, image.height, image.width * 4, QImage.Format.Format_RGBA8888)
        self.base_pixmap = QPixmap.fromImage(qim)
        self.update()

    def _display_bounds(self) -> QRectF | None:
        """
        Description: Return the on-screen rectangle occupied by the scaled preview image.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.base_pixmap is None:
            return None
        target = self.base_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        x = (self.width() - target.width()) // 2
        y = (self.height() - target.height()) // 2
        return QRectF(x, y, target.width(), target.height())

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-26
        @version 3

        @param event

        @returns
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.base_pixmap is not None:
            target = self.base_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = (self.width() - target.width()) // 2
            y = (self.height() - target.height()) // 2
            bounds = QRectF(x, y, target.width(), target.height())
            painter.drawPixmap(x, y, target)
            for token in reversed(self.effective_layer_order()):
                if token.startswith("loupe:"):
                    loupe = self.loupe_for_token(token)
                    if loupe is not None:
                        self.paint_loupe(painter, bounds, loupe)
                elif token.startswith("annotation:"):
                    item = self.annotation_for_token(token)
                    if item is None:
                        continue
                    self.paint_annotations(painter, bounds, [item])
            if self.draft_annotation is not None:
                # Rendre l'objet en cours de tracé (étiquette, rectangle, cercle…)
                # immédiatement, sans attendre la validation du texte.
                self.paint_annotations(painter, bounds, [self.draft_annotation])
            if self.show_rotation_grid and self.tool == TOOL_ROTATE_LINE:
                self.paint_rotation_grid(painter, bounds)
            self.paint_crop_overlay(painter, bounds)
        else:
            painter.fillRect(self.rect(), QColor("#1b1b1b"))
            painter.setPen(QColor("#a0a0a5"))

            # Titre principal
            font = QFont(self.font())
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            title_rect = QRectF(0, self.height() / 2 - 40, self.width(), 30)
            painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, "Aucune image chargée")

            # Sous-titre sans mise en forme HTML (commenté)
            # font.setPointSize(10)
            # font.setBold(False)
            # painter.setFont(font)
            # sub_rect = QRectF(0, self.height() / 2, self.width(), 30)
            # painter.drawText(
            #     sub_rect,
            #     Qt.AlignmentFlag.AlignCenter,
            #     "Glissez-déposez une image ici\nou ouvrez-en une via « Fichier > Ouvrir une image » pour commencer."
            # )

            # Sous-titre avec mise en gras HTML
            doc = QTextDocument()
            doc.setDefaultFont(QFont(self.font().family(), 10))
            html_content = (
                "<div style='color: #a0a0a5; text-align: center;'>"
                "Glissez-déposez une image ici<br>"
                "ou ouvrez-en une via <b>« Fichier &gt; Ouvrir une image »</b> pour commencer."
                "</div>"
            )
            doc.setHtml(html_content)
            doc.setTextWidth(self.width())

            # Positionnement du QTextDocument au centre sous le titre
            painter.save()
            painter.translate(0, self.height() / 2)
            doc.drawContents(painter)
            painter.restore()

    def rotation_grid_step(self, bounds: QRectF) -> float:
        """
        Description: Return the visible spacing of the rotation alignment grid. The grid should remain readable even when the preview is zoomed out, so we keep a minimum of 100 pixels on screen and scale it upward with the preview size.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param bounds

        @returns
        """
        if self.preview_image is None or self.preview_image.width == 0 or self.preview_image.height == 0:
            return 100.0
        scale = min(bounds.width() / self.preview_image.width, bounds.height() / self.preview_image.height)
        step = max(100.0, 100.0 * scale)
        return max(10.0, round(step / 10.0) * 10.0)

    def paint_rotation_grid(self, painter: QPainter, bounds: QRectF) -> None:
        """
        Description: Overlay a two-level grid to help visually align the rotation. Small dotted grid (50 px) is drawn first for fine alignment, then a coarser dashed grid (100 px) overlaid on top for macro alignment. Both grids are centred on the image so the central cross lines up with the image centre — the most useful reference for levelling.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param painter
        @param bounds

        @returns
        """
        step_large = self.rotation_grid_step(bounds)   # ≥100 px dashed
        step_small = step_large / 2.0                   # 50 px dotted

        cx = bounds.left() + bounds.width() / 2.0
        cy = bounds.top() + bounds.height() / 2.0

        def _draw_grid(step: float, style: Qt.PenStyle, width: int, alpha: int) -> None:
            """
            Description:

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-20
            @version 1

            @param step
            @param style
            @param width
            @param alpha

            @returns
            """
            pen = QPen(QColor(255, 255, 255, alpha))
            pen.setStyle(style)
            pen.setWidth(width)
            painter.setPen(pen)
            # Vertical lines centred on cx
            x = cx % step
            while x <= bounds.right():
                if x >= bounds.left():
                    painter.drawLine(QPointF(x, bounds.top()), QPointF(x, bounds.bottom()))
                x += step
            # Also go left from cx for lines that start right of bounds.left()
            x = cx - step * (math.ceil((cx - bounds.left()) / step))
            while x <= bounds.right():
                if x >= bounds.left():
                    painter.drawLine(QPointF(x, bounds.top()), QPointF(x, bounds.bottom()))
                x += step
            # Horizontal lines centred on cy
            y = cy % step
            while y <= bounds.bottom():
                if y >= bounds.top():
                    painter.drawLine(QPointF(bounds.left(), y), QPointF(bounds.right(), y))
                y += step
            y = cy - step * (math.ceil((cy - bounds.top()) / step))
            while y <= bounds.bottom():
                if y >= bounds.top():
                    painter.drawLine(QPointF(bounds.left(), y), QPointF(bounds.right(), y))
                y += step

        # Petite grille 50 px en pointillés (moins visible)
        _draw_grid(step_small, Qt.PenStyle.DotLine, 1, 100)
        # Grande grille 100 px en tirets (plus visible)
        _draw_grid(step_large, Qt.PenStyle.DashLine, 1, 200)

        # Lignes de centre pleines et épaisses — référence principale.
        pen = QPen(QColor(255, 255, 255, 230))
        pen.setStyle(Qt.PenStyle.SolidLine)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(QPointF(cx, bounds.top()), QPointF(cx, bounds.bottom()))
        painter.drawLine(QPointF(bounds.left(), cy), QPointF(bounds.right(), cy))

    def paint_annotations(
        self, painter: QPainter, bounds: QRectF, items: list[AnnotationItem] | None = None
    ) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 3

        @param painter
        @param bounds
        @param items

        @returns
        """
        if self.preview_image is None:
            return

        scale_x = bounds.width() / self.preview_image.width
        scale_y = bounds.height() / self.preview_image.height

        if items is None:
            items = list(reversed(self.annotations))
            if self.draft_annotation:
                items.append(self.draft_annotation)

        for item in items:
            stroke = max(1, item.stroke_width)
            if item.kind == "text":
                if item.start is None:
                    continue
                point = QPointF(item.start.x() * scale_x + bounds.left(), item.start.y() * scale_y + bounds.top())
                painter.setPen(QPen(item.color, stroke))
                painter.drawText(point.toPoint(), item.text)
            elif item.kind == "label":
                if item.start is None or item.end is None:
                    continue
                label_point = QPointF(item.start.x() * scale_x + bounds.left(), item.start.y() * scale_y + bounds.top())
                target = QPointF(item.end.x() * scale_x + bounds.left(), item.end.y() * scale_y + bounds.top())
                font = QFont(painter.font())
                font.setPointSize(12)
                font.setBold(item.bold_text)
                painter.setFont(font)
                text_rect = painter.fontMetrics().boundingRect(item.text)
                rect = QRectF(label_point.x(), label_point.y(), text_rect.width() + 18, text_rect.height() + 14)
                painter.setPen(QPen(item.color, stroke))
                painter.setBrush(QColor(20, 24, 33, 230) if item.fill_enabled else Qt.BrushStyle.NoBrush)
                if item.shape == "round":
                    painter.drawEllipse(rect)
                else:
                    r = max(0, item.border_radius) * min(scale_x, scale_y)
                    painter.drawRoundedRect(rect, r, r)
                if item.show_text:
                    painter.setPen(QPen(QColor("white"), 1))
                    painter.drawText(rect.adjusted(9, 7, -9, -7), Qt.AlignmentFlag.AlignCenter, item.text)
                if item.show_arrow:
                    anchor = self._nearest_point_on_rect(rect, target)
                    arrow_stroke = max(1, item.arrow_stroke_width)
                    painter.setPen(QPen(item.color, arrow_stroke))
                    painter.drawLine(anchor, target)
                    self._paint_arrow_head(painter, anchor, target, item.color, arrow_stroke)
            elif item.kind == "rect":
                if item.start is None or item.end is None:
                    continue
                rect = QRectF(
                    item.start.x() * scale_x + bounds.left(),
                    item.start.y() * scale_y + bounds.top(),
                    (item.end.x() - item.start.x()) * scale_x,
                    (item.end.y() - item.start.y()) * scale_y,
                ).normalized()
                painter.setPen(QPen(item.color, stroke))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                if item.border_radius > 0:
                    r = item.border_radius * min(scale_x, scale_y)
                    painter.drawRoundedRect(rect, r, r)
                else:
                    painter.drawRect(rect)
            elif item.kind == "circle":
                if item.start is None or item.end is None:
                    continue
                rect = QRectF(
                    item.start.x() * scale_x + bounds.left(),
                    item.start.y() * scale_y + bounds.top(),
                    (item.end.x() - item.start.x()) * scale_x,
                    (item.end.y() - item.start.y()) * scale_y,
                )
                painter.setPen(QPen(item.color, stroke))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(rect.normalized())
            elif item.kind == "line":
                if item.start is None or item.end is None:
                    continue
                p1 = QPointF(item.start.x() * scale_x + bounds.left(), item.start.y() * scale_y + bounds.top())
                p2 = QPointF(item.end.x() * scale_x + bounds.left(), item.end.y() * scale_y + bounds.top())
                painter.setPen(QPen(item.color, stroke))
                painter.drawLine(p1, p2)
                if item.line_arrow_start:
                    self._paint_arrow_head(painter, p2, p1, item.color, stroke)
                if item.line_arrow_end:
                    self._paint_arrow_head(painter, p1, p2, item.color, stroke)

            # Identification visuelle si l'élément est sélectionné
            if self.is_selected(item):
                highlight_pen = QPen(QColor("#00E5FF"), 2, Qt.PenStyle.DashLine)
                painter.setPen(highlight_pen)
                painter.setBrush(Qt.BrushStyle.NoBrush)
                margin = 6
                if item.kind == "label" and item.start is not None and item.end is not None:
                    p1 = QPointF(item.start.x() * scale_x + bounds.left(), item.start.y() * scale_y + bounds.top())
                    p2 = QPointF(item.end.x() * scale_x + bounds.left(), item.end.y() * scale_y + bounds.top())
                    label_rect = self._label_screen_rect(item, p1)
                    bbox = label_rect.united(QRectF(p1, p2)).adjusted(-margin, -margin, margin, margin)
                elif item.start is not None and item.end is not None:
                    p1 = QPointF(item.start.x() * scale_x + bounds.left(), item.start.y() * scale_y + bounds.top())
                    p2 = QPointF(item.end.x() * scale_x + bounds.left(), item.end.y() * scale_y + bounds.top())
                    bbox = QRectF(p1, p2).normalized().adjusted(-margin, -margin, margin, margin)
                else:
                    bbox = None

                if bbox is not None:
                    painter.drawRect(bbox)
                    handle_size = 6
                    painter.fillRect(QRectF(bbox.left() - handle_size / 2, bbox.top() - handle_size / 2, handle_size, handle_size), QColor("#00E5FF"))
                    painter.fillRect(QRectF(bbox.right() - handle_size / 2, bbox.top() - handle_size / 2, handle_size, handle_size), QColor("#00E5FF"))
                    painter.fillRect(QRectF(bbox.left() - handle_size / 2, bbox.bottom() - handle_size / 2, handle_size, handle_size), QColor("#00E5FF"))
                    painter.fillRect(QRectF(bbox.right() - handle_size / 2, bbox.bottom() - handle_size / 2, handle_size, handle_size), QColor("#00E5FF"))

    def paint_loupe(self, painter: QPainter, bounds: QRectF, loupe: LoupeOverlay) -> None:
        """
        Description: Paint one loupe (zoomed disc, outline ring and arrow) onto the preview.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 4

        @param painter
        @param bounds
        @param loupe

        @returns
        """
        if self.preview_image is None or not loupe.enabled:
            return

        scale_x = bounds.width() / self.preview_image.width
        scale_y = bounds.height() / self.preview_image.height

        center = QPointF(loupe.center.x() * scale_x + bounds.left(), loupe.center.y() * scale_y + bounds.top())
        radius = max(20, int(loupe.radius * min(scale_x, scale_y)))
        end = QPointF(loupe.arrow[1].x() * scale_x + bounds.left(), loupe.arrow[1].y() * scale_y + bounds.top())
        source_radius = loupe.radius / max(loupe.zoom, 0.01)
        source = QRectF(loupe.arrow[1].x() - source_radius, loupe.arrow[1].y() - source_radius, source_radius * 2, source_radius * 2)
        destination = QRectF(center.x() - radius, center.y() - radius, radius * 2, radius * 2)
        clip = QPainterPath()
        clip.addEllipse(destination)
        painter.save()
        painter.setClipPath(clip)
        painter.translate(center)
        if loupe.rotation:
            painter.rotate(loupe.rotation)
        painter.drawPixmap(QRectF(-radius, -radius, radius * 2, radius * 2), self.base_pixmap, source)
        painter.restore()
        painter.setPen(QPen(loupe.color, max(1, loupe.stroke_width)))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        # Identification visuelle si la loupe est sélectionnée
        if self.is_selected(loupe):
            highlight_pen = QPen(QColor("#00E5FF"), 2, Qt.PenStyle.DashLine)
            painter.setPen(highlight_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius + 6, radius + 6)

        start = self._circle_edge_toward(center, radius, end)
        # Utiliser une épaisseur indépendante pour la flèche de la loupe
        arrow_pen = QPen(loupe.color, max(1, loupe.arrow_stroke_width))
        painter.setPen(arrow_pen)
        painter.drawLine(start, end)
        self._paint_arrow_head(painter, start, end, loupe.color, max(1, loupe.arrow_stroke_width))

    def paint_crop_overlay(self, painter: QPainter, bounds: QRectF) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param painter
        @param bounds

        @returns
        """
        if self.crop_rect is None or self.preview_image is None:
            return

        scale_x = bounds.width() / self.preview_image.width
        scale_y = bounds.height() / self.preview_image.height
        rect = QRectF(
            self.crop_rect.left() * scale_x + bounds.left(),
            self.crop_rect.top() * scale_y + bounds.top(),
            self.crop_rect.width() * scale_x,
            self.crop_rect.height() * scale_y,
        ).normalized()

        painter.save()
        dim = QPainterPath()
        dim.addRect(bounds)
        dim.addRect(rect)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 140))
        painter.drawPath(dim)
        painter.restore()

        painter.setPen(QPen(QColor("#ffffff"), 2, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

    @staticmethod
    def _nearest_point_on_rect(rect: QRectF, point: QPointF) -> QPointF:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param rect
        @param point

        @returns
        """
        return QPointF(min(max(point.x(), rect.left()), rect.right()), min(max(point.y(), rect.top()), rect.bottom()))

    @staticmethod
    def _circle_edge_toward(center: QPointF, radius: float, point: QPointF) -> QPointF:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param center
        @param radius
        @param point

        @returns
        """
        distance = math.hypot(point.x() - center.x(), point.y() - center.y()) or 1.0
        return QPointF(center.x() + (point.x() - center.x()) * radius / distance, center.y() + (point.y() - center.y()) * radius / distance)

    @staticmethod
    def _paint_arrow_head(painter: QPainter, start: QPointF, end: QPointF, color: QColor, width: int = 2) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param painter
        @param start
        @param end
        @param color
        @param width

        @returns
        """
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        length = max(10, width * 4)
        for offset in (math.radians(150), math.radians(-150)):
            painter.setPen(QPen(color, width))
            painter.drawLine(end, QPointF(end.x() + length * math.cos(angle + offset), end.y() + length * math.sin(angle + offset)))

    @staticmethod
    def _distance(a: QPointF, b: QPointF) -> float:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param a
        @param b

        @returns
        """
        return math.hypot(a.x() - b.x(), a.y() - b.y())

    @staticmethod
    def _distance_to_segment(point: QPointF, start: QPointF, end: QPointF) -> float:
        """
        Description: Shortest distance between ``point`` and the segment ``start``-``end``.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param point
        @param start
        @param end

        @returns
        """
        dx, dy = end.x() - start.x(), end.y() - start.y()
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return math.hypot(point.x() - start.x(), point.y() - start.y())
        t = max(0.0, min(1.0, ((point.x() - start.x()) * dx + (point.y() - start.y()) * dy) / length_sq))
        return math.hypot(point.x() - (start.x() + t * dx), point.y() - (start.y() + t * dy))

    def _label_screen_rect(self, item: AnnotationItem, label_point: QPointF) -> QRectF:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param item
        @param label_point

        @returns
        """
        font = QFont(self.font())
        font.setPointSize(12)
        text_rect = QFontMetrics(font).boundingRect(item.text)
        return QRectF(label_point.x(), label_point.y(), text_rect.width() + 18, text_rect.height() + 14)

    def _crop_hit_test(self, screen_point: QPointF) -> tuple[str, None] | None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param screen_point

        @returns
        """
        bounds = self._display_bounds()
        screen_rect = self._crop_screen_rect(bounds) if bounds is not None else None
        if screen_rect is None:
            return None

        handles = {
            "crop_resize_tl": screen_rect.topLeft(),
            "crop_resize_tr": screen_rect.topRight(),
            "crop_resize_bl": screen_rect.bottomLeft(),
            "crop_resize_br": screen_rect.bottomRight(),
        }
        for mode, handle in handles.items():
            if self._distance(screen_point, handle) <= HANDLE_HIT_RADIUS:
                return (mode, None)
        if self.selected_item == "crop" and screen_rect.contains(screen_point):
            return ("crop_move", None)
        return None

    def _hit_test(self, screen_point: QPointF) -> tuple[str, AnnotationItem | None] | None:
        """
        Description: Identify which existing item/handle (if any) sits under ``screen_point``. Tests items front-to-back following ``self.layer_order`` (the same stacking order used by ``paintEvent``), so an item drawn on top of another (e.g. a label sitting above the loupe) is grabbed first.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param screen_point

        @returns
        """
        bounds = self._display_bounds()
        if bounds is None or self.preview_image is None:
            return None

        scale_x = bounds.width() / self.preview_image.width
        scale_y = bounds.height() / self.preview_image.height

        def to_screen(point: QPointF) -> QPointF:
            """
            Description:

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-20
            @version 2

            @param point

            @returns
            """
            return QPointF(point.x() * scale_x + bounds.left(), point.y() * scale_y + bounds.top())

        # Le rognage est toujours dessiné au premier plan par paintEvent.
        crop_hit = self._crop_hit_test(screen_point)
        if crop_hit is not None:
            return crop_hit

        def hit_loupe(loupe: LoupeOverlay) -> tuple[str, LoupeOverlay] | None:
            """
            Description: Hit-test one loupe: its arrow tip first, then its disc.

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-23
            @version 3

            @param loupe

            @returns
            """
            if not loupe.enabled:
                return None
            arrow_end_screen = to_screen(loupe.arrow[1])
            if self._distance(screen_point, arrow_end_screen) <= HANDLE_HIT_RADIUS:
                return ("loupe_arrow_end", loupe)
            center_screen = to_screen(loupe.center)
            radius_screen = loupe.radius * min(scale_x, scale_y)
            if self._distance(screen_point, center_screen) <= max(radius_screen, HANDLE_HIT_RADIUS):
                return ("loupe_body", loupe)
            return None

        def hit_annotation(item: AnnotationItem) -> tuple[str, AnnotationItem] | None:
            """
            Description:

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-20
            @version 3

            @param item

            @returns
            """
            if item.kind == "label" and item.start is not None and item.end is not None:
                anchor_screen = to_screen(item.end)
                if self._distance(screen_point, anchor_screen) <= HANDLE_HIT_RADIUS:
                    return ("label_anchor", item)
                label_point = to_screen(item.start)
                if self._label_screen_rect(item, label_point).contains(screen_point):
                    return ("label_body", item)
            elif item.kind in ("rect", "circle") and item.start is not None and item.end is not None:
                start_screen = to_screen(item.start)
                end_screen = to_screen(item.end)
                if self._distance(screen_point, start_screen) <= HANDLE_HIT_RADIUS:
                    return ("shape_start", item)
                if self._distance(screen_point, end_screen) <= HANDLE_HIT_RADIUS:
                    return ("shape_end", item)
                if QRectF(start_screen, end_screen).normalized().contains(screen_point):
                    return ("shape_body", item)
            elif item.kind == "line" and item.start is not None and item.end is not None:
                start_screen = to_screen(item.start)
                end_screen = to_screen(item.end)
                if self._distance(screen_point, start_screen) <= HANDLE_HIT_RADIUS:
                    return ("line_start", item)
                if self._distance(screen_point, end_screen) <= HANDLE_HIT_RADIUS:
                    return ("line_end", item)
                # Tout le long du trait (et pas seulement ses extrémités) : la
                # ligne est saisie pour être déplacée au lieu d'en créer une nouvelle.
                tolerance = max(HANDLE_HIT_RADIUS / 2, item.stroke_width * min(scale_x, scale_y) / 2 + 4)
                if self._distance_to_segment(screen_point, start_screen, end_screen) <= tolerance:
                    return ("line_body", item)
            return None

        for token in self.effective_layer_order():
            hit: tuple[str, AnnotationItem | LoupeOverlay | None] | None = None
            if token.startswith("loupe:"):
                loupe = self.loupe_for_token(token)
                hit = hit_loupe(loupe) if loupe is not None else None
            elif token.startswith("annotation:"):
                item = self.annotation_for_token(token)
                if item is None:
                    continue
                hit = hit_annotation(item)
            if hit is not None:
                return hit

        crop_rect = self._crop_screen_rect(bounds)
        if crop_rect is not None and crop_rect.contains(screen_point):
            return ("crop_move", None)
        return None

    def _apply_drag(self, delta: QPointF) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 3

        @param delta

        @returns
        """
        mode = self.drag_mode
        item = self.drag_target
        if mode == "crop_move" and self.crop_rect is not None:
            self.crop_rect.translate(delta)
        elif mode and mode.startswith("crop_resize_") and self.crop_rect is not None and self.preview_image is not None:
            rect = self.crop_rect.normalized()
            left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
            if mode.endswith("tl") or mode.endswith("bl"):
                left = min(max(0.0, left + delta.x()), right - 1.0)
            else:
                right = max(min(float(self.preview_image.width), right + delta.x()), left + 1.0)
            if mode.endswith("tl") or mode.endswith("tr"):
                top = min(max(0.0, top + delta.y()), bottom - 1.0)
            else:
                bottom = max(min(float(self.preview_image.height), bottom + delta.y()), top + 1.0)
            self.crop_rect = QRectF(QPointF(left, top), QPointF(right, bottom))
        elif mode == "loupe_arrow_end" and isinstance(item, LoupeOverlay):
            item.arrow = (item.arrow[0], item.arrow[1] + delta)
        elif mode == "loupe_body" and isinstance(item, LoupeOverlay):
            item.center = item.center + delta
            item.arrow = (item.center, item.arrow[1])
        elif mode == "label_anchor" and item is not None and item.end is not None:
            item.end = item.end + delta
        elif mode == "label_body" and item is not None and item.start is not None:
            item.start = item.start + delta
        elif mode == "shape_start" and item is not None and item.start is not None:
            item.start = item.start + delta
        elif mode == "shape_end" and item is not None and item.end is not None:
            item.end = item.end + delta
        elif mode == "shape_body" and item is not None and item.start is not None and item.end is not None:
            item.start = item.start + delta
            item.end = item.end + delta
        elif mode == "line_start" and item is not None and item.start is not None:
            item.start = item.start + delta
        elif mode == "line_end" and item is not None and item.end is not None:
            item.end = item.end + delta
        elif mode == "line_body" and item is not None and item.start is not None and item.end is not None:
            item.start = item.start + delta
            item.end = item.end + delta

    def _crop_screen_rect(self, bounds: QRectF) -> QRectF | None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param bounds

        @returns
        """
        if self.crop_rect is None or self.preview_image is None:
            return None
        scale_x = bounds.width() / self.preview_image.width
        scale_y = bounds.height() / self.preview_image.height
        return QRectF(
            self.crop_rect.left() * scale_x + bounds.left(),
            self.crop_rect.top() * scale_y + bounds.top(),
            self.crop_rect.width() * scale_x,
            self.crop_rect.height() * scale_y,
        ).normalized()

    def _snapshot_drag_target(self) -> tuple | None:
        """
        Description: Copy the geometry of the item about to be dragged, so each mouse move can be recomputed from this origin.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 2

        @returns
        """
        mode = self.drag_mode or ""
        if mode.startswith("crop") and self.crop_rect is not None:
            return ("crop", QRectF(self.crop_rect))
        return self._snapshot_item(self.drag_target)

    @staticmethod
    def _snapshot_item(item: object) -> tuple | None:
        """
        Description: Copy the geometry of an annotation or a loupe.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item

        @returns
        """
        if isinstance(item, LoupeOverlay):
            return ("loupe", QPointF(item.center), (QPointF(item.arrow[0]), QPointF(item.arrow[1])))
        if isinstance(item, AnnotationItem):
            return (
                "annotation",
                QPointF(item.start) if item.start is not None else None,
                QPointF(item.end) if item.end is not None else None,
            )
        return None

    def _restore_drag_origin(self) -> None:
        """
        Description: Put the dragged item back to the geometry captured by ``_snapshot_drag_target``.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 2

        @returns
        """
        origin = self._drag_origin
        if origin is None:
            return
        if origin[0] == "crop":
            self.crop_rect = QRectF(origin[1])
        else:
            self._restore_item_origin(self.drag_target, origin)

    @staticmethod
    def _restore_item_origin(item: object, origin: tuple | None) -> None:
        """
        Description: Put an annotation or a loupe back to a geometry captured by ``_snapshot_item``.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item
        @param origin

        @returns
        """
        if origin is None:
            return
        if origin[0] == "loupe" and isinstance(item, LoupeOverlay):
            item.center = QPointF(origin[1])
            item.arrow = (QPointF(origin[2][0]), QPointF(origin[2][1]))
        elif origin[0] == "annotation" and isinstance(item, AnnotationItem):
            item.start = QPointF(origin[1]) if origin[1] is not None else None
            item.end = QPointF(origin[2]) if origin[2] is not None else None

    def _drag_reference_point(self) -> QPointF | None:
        """
        Description: Return the point that must land on the grid when the current drag is snapped (moved handle, or the object's anchor for a whole-object move).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        origin = self._drag_origin
        mode = self.drag_mode or ""
        if origin is None:
            return None
        if origin[0] == "crop":
            rect = origin[1].normalized()
            return {
                "crop_resize_tr": rect.topRight(),
                "crop_resize_bl": rect.bottomLeft(),
                "crop_resize_br": rect.bottomRight(),
            }.get(mode, rect.topLeft())
        if origin[0] == "loupe":
            return origin[2][1] if mode == "loupe_arrow_end" else origin[1]
        if mode in ("label_anchor", "shape_end", "line_end"):
            return origin[2]
        return origin[1]

    def _drag_to(self, current: QPointF, snap: bool) -> None:
        """
        Description: Move the dragged item so it follows the mouse from the press point; with ``snap`` the reference point is aligned on the grid.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 2

        @param current
        @param snap

        @returns
        """
        delta = current - self._drag_press_point
        if self._drag_origin is None:
            # Pas d'état d'origine (appel direct) : déplacement incrémental.
            self._apply_drag(current - self.last_mouse)
            self.last_mouse = current
            return
        reference = self._drag_reference_point()
        if snap and reference is not None:
            delta = self.snap_to_grid(reference + delta) - reference
        self._restore_drag_origin()
        self._apply_drag(delta)
        # Sélection multiple : les autres objets suivent le même déplacement.
        for other, origin in self._group_origins:
            self._restore_item_origin(other, origin)
            self.translate_item(other, delta)
        self.last_mouse = current

    def _begin_item_drag(self, hit: tuple[str, AnnotationItem | LoupeOverlay | None], img_point: QPointF) -> None:
        """
        Description: Start dragging an existing item/handle returned by ``_hit_test`` and select it.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 2

        @param hit
        @param img_point

        @returns
        """
        self.dragging = True
        self.drag_mode, self.drag_target = hit
        self.last_mouse = img_point
        self._drag_press_point = QPointF(img_point)
        self._drag_origin = self._snapshot_drag_target()
        self._group_origins = []
        group = self.selected_objects()
        if hit[1] is not None and len(group) > 1 and any(hit[1] is item for item in group) and hit[0].endswith("_body"):
            # Glisser le corps d'un objet d'une sélection multiple déplace tout le groupe.
            self._group_origins = [(item, self._snapshot_item(item)) for item in group if item is not hit[1]]
            self.set_selection(group, hit[1])
        elif hit[1] is not None:
            self.selected_item = hit[1]
        elif hit[0].startswith("crop"):
            self.selected_item = "crop"
        self.item_selected.emit(self.selected_item)
        self.update()

    @staticmethod
    def _snap_requested(event) -> bool:
        """
        Description: Grid snapping is only active while the Ctrl key is held down.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param event

        @returns
        """
        return bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Start dragging an existing item (the "Déplacer" behaviour, always active) or start drawing with the active tool. Holding Ctrl snaps the pressed point to the grid.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 4

        @param event

        @returns
        """
        if self.preview_image is None:
            return

        raw_point = self.to_image_coordinates(event.position().toPoint())
        img_point = self.snap_to_grid(raw_point) if self._snap_requested(event) else raw_point

        # "Déplacer" est toujours actif : cliquer sur le contour d'un objet
        # existant le fait glisser, quel que soit l'outil courant.
        hit = self._hit_test(event.position())
        if hit is not None and isinstance(hit[1], (AnnotationItem, LoupeOverlay)) and (
            event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            # Maj + clic : ajoute l'objet à la sélection ou l'en retire.
            self.toggle_in_selection(hit[1])
            self.item_selected.emit(self.selected_item)
            self.update()
            return
        if hit is not None:
            self._begin_item_drag(hit, raw_point)
            return

        if self.tool in (TOOL_ROTATE_LINE, TOOL_CROP):
            # Le mode Transformation permet de dessiner un rectangle de rognage
            # directement dans la prévisualisation, puis de le redimensionner
            # avec les poignées avant validation.
            self.dragging = True
            self.crop_drag_mode = "crop_new"
            self.drag_start = img_point
            self.crop_rect = QRectF(img_point, img_point)
            self.selected_item = "crop"
            self.item_selected.emit(self.selected_item)
            self.update()
            return
        elif self.tool == TOOL_TEXT:
            self.dragging = True
            self.drag_start = img_point
            self.draft_annotation = AnnotationItem(
                kind="label",
                start=img_point,
                end=img_point,
                text="Étiquette",
                color=QColor(self.current_color),
                stroke_width=self.current_stroke_width,
                border_radius=self.current_border_radius,
                show_arrow=self.current_show_arrow,
                shape=self.current_label_shape,
                arrow_stroke_width=self.current_arrow_stroke_width,
                show_text=self.current_show_text,
                fill_enabled=self.current_fill_enabled,
                bold_text=self.current_bold_text,
            )
        elif self.tool in (TOOL_RECT, TOOL_CIRCLE, TOOL_LINE):
            self.dragging = True
            self.drag_start = img_point
            self.last_mouse = img_point
        elif self.tool == TOOL_LOUPE:
            # Glisser dans le vide repositionne la loupe sélectionnée ; sans
            # loupe sélectionnée, une nouvelle loupe est créée.
            loupe = self.selected_item if isinstance(self.selected_item, LoupeOverlay) else None
            if loupe is None:
                loupe = self.add_loupe(img_point)
            loupe.enabled = True
            loupe.center = QPointF(img_point)
            loupe.arrow = (QPointF(img_point), QPointF(img_point))
            loupe.color = QColor(self.current_color)
            self.dragging = True
            self.drag_target = loupe
            self.drag_start = QPointF(img_point)
            self.last_mouse = QPointF(img_point)
            self.selected_item = loupe
            self.item_selected.emit(self.selected_item)
            self.annotation_changed.emit()
        elif self.tool == TOOL_VIEW:
            if self.selected_item is not None:
                self.selected_item = None
                self.item_selected.emit(None)
                self.update()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Update the item being moved or the shape being drawn. Holding Ctrl snaps to the grid; without it the pointer is followed freely.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param event

        @returns
        """
        if self.preview_image is None:
            return

        raw_current = self.to_image_coordinates(event.position().toPoint())
        snap = self._snap_requested(event)
        current = self.snap_to_grid(raw_current) if snap else raw_current
        if self.dragging and self.drag_mode is not None:
            # Un objet existant est en cours de déplacement : cela prime sur
            # le comportement habituel de l'outil actif.
            self._drag_to(raw_current, snap)
            self.update()
        elif self.tool == TOOL_RECT and self.dragging:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                current = self._constrain_to_square(self.drag_start, current)
            self.draft_annotation = AnnotationItem(
                kind="rect",
                start=self.drag_start,
                end=current,
                color=QColor(self.current_color),
                stroke_width=self.current_stroke_width,
                border_radius=self.current_border_radius,
            )
            self.update()
        elif self.tool == TOOL_CIRCLE and self.dragging:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                current = self._constrain_to_square(self.drag_start, current)
            self.draft_annotation = AnnotationItem(
                kind="circle",
                start=self.drag_start,
                end=current,
                color=QColor(self.current_color),
                stroke_width=self.current_stroke_width,
                border_radius=self.current_border_radius,
            )
            self.update()
        elif self.tool == TOOL_TEXT and self.dragging and self.draft_annotation is not None:
            self.draft_annotation.end = current
            self.update()
        elif self.tool == TOOL_LINE and self.dragging:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                current = self._constrain_to_45_degrees(self.drag_start, current)
            self.draft_annotation = AnnotationItem(
                kind="line",
                start=self.drag_start,
                end=current,
                color=QColor(self.current_color),
                stroke_width=self.current_stroke_width,
                line_arrow_start=self.current_line_arrow_start,
                line_arrow_end=self.current_line_arrow_end,
            )
            self.update()
        elif self.tool == TOOL_LOUPE and self.dragging and isinstance(self.drag_target, LoupeOverlay):
            loupe = self.drag_target
            loupe.arrow = (QPointF(loupe.center), current)
            self.update()
        elif self.tool in (TOOL_ROTATE_LINE, TOOL_CROP) and self.dragging:
            if self.crop_drag_mode == "crop_new":
                self.crop_rect = QRectF(self.drag_start, current)
            self.update()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Commit the shape being drawn or the item being moved.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 4

        @param event

        @returns
        """
        has_changed = False
        if self.dragging and self.draft_annotation is not None:
            if self.draft_annotation.kind == "label":
                text, accepted = QInputDialog.getText(self, "Étiquette", "Texte de l'étiquette :", text=self.draft_annotation.text)
                if accepted and text.strip():
                    self.draft_annotation.text = text.strip()
                    if self.draft_annotation.start == self.draft_annotation.end:
                        self.draft_annotation.end = QPointF(self.draft_annotation.start.x() + 80, self.draft_annotation.start.y() + 80)
                    self._commit_new_annotation(self.draft_annotation)
                    self.selected_item = self.draft_annotation
                    has_changed = True
            elif self.draft_annotation.kind in ("rect", "circle", "line") and self.draft_annotation.start != self.draft_annotation.end:
                self._commit_new_annotation(self.draft_annotation)
                self.selected_item = self.draft_annotation
                has_changed = True
            self.draft_annotation = None
            self.update()
        elif self.dragging and (
            self.drag_mode is not None or self.crop_drag_mode is not None or isinstance(self.drag_target, LoupeOverlay)
        ):
            has_changed = True

        self.dragging = False
        self.drag_mode = None
        self.drag_target = None
        self._drag_origin = None
        self._group_origins = []
        self.crop_drag_mode = None

        if has_changed:
            self.annotation_changed.emit()
            self.item_selected.emit(self.selected_item)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param event

        @returns
        """
        point = self.to_image_coordinates(event.position().toPoint())
        for item in reversed(self.annotations):
            if item.kind != "label" or item.start is None:
                continue
            if abs(point.x() - item.start.x()) < 250 and abs(point.y() - item.start.y()) < 100:
                text, accepted = QInputDialog.getText(self, "Modifier l'étiquette", "Texte de l'étiquette :", text=item.text)
                if accepted and text.strip():
                    item.text = text.strip()
                    self.selected_item = item
                    self.update()
                    self.annotation_changed.emit()
                    self.item_selected.emit(self.selected_item)
                return

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Zoom a loupe in/out with the mouse wheel while the loupe tool is active: the loupe under the cursor, otherwise the selected/front-most one.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param event

        @returns
        """
        loupe = None
        if self.tool == TOOL_LOUPE:
            hit = self._hit_test(event.position())
            loupe = hit[1] if hit is not None and isinstance(hit[1], LoupeOverlay) else self.active_loupe()
        if loupe is not None and loupe.enabled:
            step = 0.1 if event.angleDelta().y() > 0 else -0.1
            loupe.zoom = round(min(8.0, max(1.0, loupe.zoom + step)), 1)
            window = self.window()
            if isinstance(window, ImageEditorWindow) and window.current_loupe() is loupe:
                window.loupe_zoom_spin.blockSignals(True)
                window.loupe_zoom_spin.setValue(loupe.zoom)
                window.loupe_zoom_spin.blockSignals(False)
            self.update()
            self.annotation_changed.emit()
            event.accept()
        else:
            super().wheelEvent(event)

    def grid_step_image(self) -> float:
        """
        Description: Spacing, in preview-image pixels, of the fine (dotted) grid drawn by ``paint_rotation_grid``.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        bounds = self._display_bounds()
        if bounds is None or self.preview_image is None or self.preview_image.width == 0:
            return 50.0
        scale = bounds.width() / self.preview_image.width
        return max(1.0, self.rotation_grid_step(bounds) / 2.0 / max(scale, 1e-6))

    def snap_to_grid(self, point: QPointF) -> QPointF:
        """
        Description: Snap an image-space point to the nearest intersection of the visible alignment grid (fine grid, centred on the image centre).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param point

        @returns
        """
        step = self.grid_step_image()
        if self.preview_image is None:
            return QPointF(round(point.x() / step) * step, round(point.y() / step) * step)
        cx = self.preview_image.width / 2.0
        cy = self.preview_image.height / 2.0
        return QPointF(
            cx + round((point.x() - cx) / step) * step,
            cy + round((point.y() - cy) / step) * step,
        )

    @staticmethod
    def _constrain_to_square(start: QPointF, end: QPointF) -> QPointF:
        """
        Description: Force ``end`` so that ``start``→``end`` spans a perfect square (used to draw a perfect circle or square while Shift is held).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param start
        @param end

        @returns
        """
        dx = end.x() - start.x()
        dy = end.y() - start.y()
        size = max(abs(dx), abs(dy))
        signed_dx = size if dx >= 0 else -size
        signed_dy = size if dy >= 0 else -size
        return QPointF(start.x() + signed_dx, start.y() + signed_dy)

    @staticmethod
    def _constrain_to_45_degrees(start: QPointF, end: QPointF) -> QPointF:
        """Snap a line to the nearest horizontal, vertical or 45° direction."""
        dx, dy = end.x() - start.x(), end.y() - start.y()
        angle = math.atan2(dy, dx)
        snapped_angle = round(angle / (math.pi / 4)) * (math.pi / 4)
        length = math.hypot(dx, dy)
        return QPointF(start.x() + length * math.cos(snapped_angle), start.y() + length * math.sin(snapped_angle))

    def to_image_coordinates(self, point: QPoint) -> QPointF:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param point

        @returns
        """
        if self.base_pixmap is None or self.preview_image is None:
            return QPointF()

        target = self.base_pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        offset_x = (self.width() - target.width()) // 2
        offset_y = (self.height() - target.height()) // 2
        local = QPoint(point.x() - offset_x, point.y() - offset_y)
        if local.x() < 0 or local.y() < 0 or local.x() > target.width() or local.y() > target.height():
            return QPointF()

        scale_x = self.preview_image.width / target.width()
        scale_y = self.preview_image.height / target.height()
        return QPointF(local.x() * scale_x, local.y() * scale_y)

    def request_rotation_from_line(self, theta_deg: float) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param theta_deg

        @returns
        """
        window = self.window()
        if isinstance(window, ImageEditorWindow):
            window.apply_rotation(-theta_deg, absolute=False)


class ImageEditorWindow(QMainWindow):
    """Main application window: a professional-leaning image annotation and
    documentation tool built around a JSON-scriptable processing recipe.

    Workflow:
      1. Load a source image (kept untouched, full resolution, on disk).
      2. Build/refresh a small preview via :func:`make_preview` and edit
         only that preview for fluid interaction.
      3. Every user decision (rotation, brightness/contrast, annotations,
         loupe, export size) accumulates into a :class:`ProcessingRecipe`.
      4. Exporting replays the recipe against the *original* full
         resolution image, guaranteeing a crisp, faithful result.
      5. The recipe can be saved/loaded as JSON to script batch processing
         outside of the interactive UI.
    """

    def __init__(self) -> None:
        """
        Description: Build the main window, restore the user's preferences and apply the theme.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-26
        @version 23

        @returns
        """
        super().__init__()
        self.setWindowTitle("Studio de traitement d'image – Annotation & Documentation")

        # Icône de l'application (fenêtre + barre des tâches/raccourcis), packagée
        # dans iat/resources/icons/ pour rester disponible quel que soit le
        # répertoire de travail courant (y compris une fois figée avec PyInstaller).
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))

        self.source_path: Path | None = None
        self.current_json_path: Path | None = None
        self.default_export_path: Path | None = None
        self.original_image: Image.Image | None = None
        self.preview_image: Image.Image | None = None
        self.preview_scale: float = 1.0  # full_res = preview * preview_scale

        self.angle_total = 0.0
        self.trapezoid_top = 0.0
        self.trapezoid_bottom = 0.0
        self.trapezoid_left = 0.0
        self.trapezoid_right = 0.0
        self.brightness = 0
        self.contrast = 1.0
        #: Crop rectangle in full-resolution coordinates of the *rotated*
        #: source image (matches ``ProcessingRecipe.crop`` semantics). ``None``
        #: means the export uses the full rotated image.
        self.crop_box: tuple[float, float, float, float] | None = None
        #: Guards against feedback loops while width/height export spin boxes
        #: resync each other to preserve the image's aspect ratio.
        self._sync_export_size_guard = False
        #: Colour used to tint the SVG icons, provided by the active theme.
        self._icon_color = QColor("#444444")
        self._icon_checked_color: QColor | None = None
        self.current_theme_path: Path | None = None

        #: Historique des fichiers récents.
        self._recent_files: list[str] = self._load_recent_files()
        self._settings = QSettings("CBI", "ImageAnnotationTool")
        #: Dossiers des ressources (menu « Configuration > Chemins des ressources »).
        self.resource_paths: dict[str, Path] = self._load_resource_paths()
        #: Variables chargées depuis le fichier .env mémorisé (retirées à la réinitialisation).
        self._env_loaded_keys: list[str] = []
        #: Historique « Annuler / Rétablir » : états sérialisés de la recette.
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        self._history_state: str | None = None
        self._restoring_history = False
        #: Objets copiés (Ctrl+C) et nombre de collages successifs (décalage).
        self._clipboard: list[AnnotationItem | LoupeOverlay] = []
        self._paste_count = 0
        #: Grilles de pastilles des palettes de couleurs, reconstruites après un changement.
        self._palette_grids: list[QGridLayout] = []
        # Ouvrir une image en la glissant depuis l'explorateur de fichiers.
        self.setAcceptDrops(True)

        self.canvas = ImageCanvas(self)
        self.canvas.setMinimumSize(760, 560)
        self.canvas.annotation_changed.connect(self._on_canvas_content_changed)
        self.canvas.item_selected.connect(self._on_canvas_item_selected)

        self.setStatusBar(QStatusBar())
        self._build_actions()
        self._build_toolbar()
        self._build_tools_dock()
        self._build_objects_dock()
        self._build_option_docks()
        self._build_central_layout()
        self._build_configuration_menu()
        # Disposition d'origine, rétablie par « Réinitialiser les paramètres ».
        self._default_window_state = self.saveState()
        self._restore_window_preferences()
        self._apply_saved_language()
        self._update_action_states()

        self.statusBar().showMessage(tr("Prêt. Ouvrez une image pour commencer."))

        # ① Plein écran par défaut
        self.showMaximized()

    @property
    def layer_order(self) -> list[str]:
        """
        Description: Front-to-back layer tokens ("annotation:<id>", "loupe:<id>"), shared with the canvas.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        return self.canvas.layer_order

    @layer_order.setter
    def layer_order(self, value: list[str]) -> None:
        self.canvas.layer_order = list(value)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_actions(self) -> None:
        """
        Description: Create the shared actions and the "Fichier" and "Aide" menus ("Configuration" is inserted between them by ``_build_configuration_menu``).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        self.open_action = QAction("Ouvrir une image", self)
        self.open_action.setToolTip("Ouvrir une image brute à annoter (le fichier JSON associé est rechargé s'il existe)")
        self.open_action.triggered.connect(self.open_image)

        self.export_action = QAction("Exporter l'image", self)
        self.export_action.setToolTip("Afficher les options d'export de l'image annotée")
        self.export_action.setCheckable(True)
        self.export_action.triggered.connect(self.show_export_options)

        self.save_recipe_action = QAction("Exporter les annotations au format JSON", self)
        self.save_recipe_action.triggered.connect(self.save_recipe)

        self.load_recipe_action = QAction("Importer les annotations depuis un fichier JSON", self)
        self.load_recipe_action.triggered.connect(self.load_recipe)

        self.tools_help_action = QAction("Aide sur les outils", self)
        self.tools_help_action.triggered.connect(self.show_tools_help)

        self.about_action = QAction("À propos", self)
        self.about_action.triggered.connect(self.show_about_dialog)

        self.load_env_action = QAction("Charger une configuration .env", self)
        self.load_env_action.triggered.connect(self.load_environment_file)
        self.load_env_action.setToolTip(
            "Charge un fichier .env pour modifier les paramètres applicatifs :\n"
            "thème par défaut, épaisseur de trait par défaut, qualité d'export, drapeaux de fonctionnalités.\n"
            "Le chemin du fichier est mémorisé et rechargé automatiquement au prochain démarrage."
        )
        self.load_theme_action = QAction("Charger un thème personnalisé", self)
        self.load_theme_action.triggered.connect(self.load_theme_file)
        self.env_help_action = QAction("À propos des fichiers .env", self)
        self.env_help_action.triggered.connect(self.show_environment_help)

        # Menu Édition : annuler/rétablir, copier/coller et suppression.
        self.undo_action = QAction("Annuler", self)
        self.undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self.undo_action.setToolTip("Annule la dernière modification (Ctrl+Z)")
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = QAction("Rétablir", self)
        self.redo_action.setShortcuts([QKeySequence("Ctrl+Y"), QKeySequence("Ctrl+Shift+Z")])
        self.redo_action.setToolTip("Rétablit la dernière modification annulée (Ctrl+Y)")
        self.redo_action.triggered.connect(self.redo)
        self.copy_action = QAction("Copier", self)
        self.copy_action.setShortcut(QKeySequence("Ctrl+C"))
        self.copy_action.setToolTip("Copie les objets sélectionnés (Ctrl+C)")
        self.copy_action.triggered.connect(self.copy_selection)
        self.paste_action = QAction("Coller", self)
        self.paste_action.setShortcut(QKeySequence("Ctrl+V"))
        self.paste_action.setToolTip("Colle une copie décalée des objets copiés (Ctrl+V)")
        self.paste_action.triggered.connect(self.paste_clipboard)
        self.delete_action = QAction("Supprimer", self)
        self.delete_action.setToolTip("Supprime les éléments sélectionnés (touche Suppr)")
        self.delete_action.triggered.connect(self.delete_selected_object)

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("Fichier")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_recipe_action)
        file_menu.addAction(self.load_recipe_action)
        file_menu.addSeparator()

        # ③ Sous-menu fichiers récents
        self.recent_menu = file_menu.addMenu("Fichiers récents")
        self._update_recent_files_menu()

        self.edit_menu = menu_bar.addMenu("Édition")
        self.edit_menu.addAction(self.undo_action)
        self.edit_menu.addAction(self.redo_action)
        self.edit_menu.addSeparator()
        self.edit_menu.addAction(self.copy_action)
        self.edit_menu.addAction(self.paste_action)
        self.edit_menu.addAction(self.delete_action)

        self.help_menu = menu_bar.addMenu("Aide")
        self.help_menu.addAction(self.tools_help_action)
        self.help_menu.addSeparator()
        self.help_menu.addAction(self.about_action)

    def _build_configuration_menu(self) -> None:
        """
        Description: Build the "Configuration" menu, between "Fichier" and "Aide": .env configuration, themes and visibility of the tool bars.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        self.configuration_menu = QMenu("Configuration", self)
        self.menuBar().insertMenu(self.help_menu.menuAction(), self.configuration_menu)
        self.configuration_menu.addAction(self.load_env_action)
        self.configuration_menu.addAction(self.env_help_action)
        self.configuration_menu.addSeparator()
        self.themes_menu = self.configuration_menu.addMenu("Thèmes disponibles")
        self._update_themes_menu()
        self.configuration_menu.addAction(self.load_theme_action)
        self.language_menu = self.configuration_menu.addMenu("Langue")
        self._update_language_menu()
        self.resource_paths_action = QAction("Chemins des ressources…", self)
        self.resource_paths_action.setToolTip("Dossiers des icônes, des thèmes et des traductions")
        self.resource_paths_action.triggered.connect(self.show_resource_paths_dialog)
        self.configuration_menu.addAction(self.resource_paths_action)
        self.configuration_menu.addSeparator()

        self.export_notification_action = QAction("Notification après l'export", self)
        self.export_notification_action.setCheckable(True)
        self.export_notification_action.setChecked(self.export_notification_enabled())
        self.export_notification_action.setToolTip(
            "Affiche une fenêtre de confirmation après chaque export (le message de la barre d'état reste affiché)"
        )
        self.export_notification_action.toggled.connect(self.set_export_notification_enabled)
        self.configuration_menu.addAction(self.export_notification_action)

        # Actions de visibilité fournies par Qt : cochées/décochées automatiquement
        # lorsque la barre est masquée par un autre moyen (clic droit, restauration).
        self.toggle_toolbar_action = self.main_toolbar.toggleViewAction()
        self.toggle_toolbar_action.setText("Afficher/Masquer la barre horizontale des outils")
        self.toggle_toolbar_action.setToolTip("Affiche ou masque la barre horizontale des outils (Ctrl+T)")
        self.toggle_toolbar_action.setShortcut("Ctrl+T")
        self.configuration_menu.addAction(self.toggle_toolbar_action)
        self.toggle_palette_action = self.graphical_tools_palette.toggleViewAction()
        self.toggle_palette_action.setText("Afficher/Masquer la palette graphique des outils")
        self.configuration_menu.addAction(self.toggle_palette_action)
        self.configuration_menu.addSeparator()
        self.reset_settings_action = QAction("Réinitialiser les paramètres…", self)
        self.reset_settings_action.setToolTip(
            "Rétablit les valeurs par défaut : thème, langue, chemins des ressources, préférences et disposition"
        )
        self.reset_settings_action.triggered.connect(lambda: self.reset_settings())
        self.configuration_menu.addAction(self.reset_settings_action)

    def _update_action_states(self) -> None:
        """
        Description: Enable the actions and tool buttons that need a loaded image.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        has_image = self.original_image is not None
        for action in (
            self.export_action,
            self.save_recipe_action,
            self.load_recipe_action,
            self.copy_action,
            self.paste_action,
            self.delete_action,
        ):
            action.setEnabled(has_image)
        self._update_history_actions()
        for button in self.toolbar_tool_buttons.values():
            button.setEnabled(has_image)
        # Le bouton d'export du panneau et le bouton de suppression de liste
        # doivent aussi être désactivés tant qu'aucune image n'est chargée.
        if hasattr(self, "export_button"):
            self.export_button.setEnabled(has_image)
        if hasattr(self, "new_loupe_button"):
            self.new_loupe_button.setEnabled(has_image)
        if hasattr(self, "delete_object_button") and not has_image:
            self.delete_object_button.setEnabled(False)
        self._sync_tool_action_states("export" if self.export_action.isChecked() else self.canvas.tool)

    def _restore_window_preferences(self) -> None:
        """
        Description: Reload the remembered .env file, window layout and theme (user choice first, then APP_THEME).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        env_path = self._settings.value("env_path", "")
        if env_path and Path(env_path).is_file():
            self._env_loaded_keys = list(load_dotenv(env_path, override=True))
            update_config_in_place(AppConfig())
        geometry = self._settings.value("geometry")
        state = self._settings.value("window_state")
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)
        theme_path = self._settings.value("theme_path", "")
        if not (theme_path and Path(theme_path).is_file() and self._load_theme_path(Path(theme_path), persist=False, quiet=True)):
            self._apply_default_theme()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Remember the window layout (docks, tool bars visibility) for the next session.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param event

        @returns
        """
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("window_state", self.saveState())
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Chemins des ressources (icônes, thèmes, traductions)
    # ------------------------------------------------------------------
    def _load_resource_paths(self) -> dict[str, Path]:
        """
        Description: Read the resource folders chosen by the user; a missing or invalid folder falls back to the bundled one.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        paths: dict[str, Path] = {}
        for key, default in DEFAULT_RESOURCE_PATHS.items():
            value = str(self._settings.value(f"resource_path_{key}", "") or "")
            paths[key] = Path(value) if value and Path(value).is_dir() else default
        return paths

    def _icon_path(self, file_name: str) -> Path:
        """
        Description: Path of an icon in the configured icons folder, or the bundled icon when the folder does not provide it.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param file_name

        @returns
        """
        custom = self.resource_paths["icons"] / file_name
        return custom if custom.is_file() else ICONS_DIRECTORY / file_name

    def show_resource_paths_dialog(self) -> None:
        """
        Description: Let the user choose the icons, themes and translations folders (defaults: bundled folders).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        dialog, edits = self._build_resource_paths_dialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.apply_resource_paths({key: edit.text().strip() for key, edit in edits.items()})

    def _build_resource_paths_dialog(self) -> tuple[QDialog, dict[str, QLineEdit]]:
        """
        Description: Build the "Chemins des ressources" dialog: one folder field + "Parcourir…" per resource, and a button restoring the defaults.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        dialog = QDialog(self)
        dialog.setObjectName("resource_paths_dialog")
        dialog.setWindowTitle(tr("Chemins des ressources"))
        layout = QVBoxLayout(dialog)
        hint = QLabel(tr("Par défaut, les ressources sont lues dans les dossiers livrés avec l'application."))
        hint.setWordWrap(True)
        layout.addWidget(hint)
        form = QFormLayout()
        edits: dict[str, QLineEdit] = {}
        for key, label in RESOURCE_PATH_LABELS.items():
            row = QHBoxLayout()
            edit = QLineEdit(str(self.resource_paths[key]))
            edit.setObjectName(f"resource_path_{key}")
            edit.setMinimumWidth(420)
            edit.setToolTip(f"{tr('Par défaut :')} {DEFAULT_RESOURCE_PATHS[key]}")
            browse = QPushButton(tr("Parcourir…"))
            browse.clicked.connect(
                lambda _checked, target=edit: target.setText(
                    QFileDialog.getExistingDirectory(dialog, tr("Choisir un dossier"), target.text()) or target.text()
                )
            )
            row.addWidget(edit, 1)
            row.addWidget(browse)
            form.addRow(tr(label), row)
            edits[key] = edit
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        defaults_button = buttons.addButton(tr("Valeurs par défaut"), QDialogButtonBox.ButtonRole.ResetRole)
        defaults_button.clicked.connect(
            lambda: [edit.setText(str(DEFAULT_RESOURCE_PATHS[key])) for key, edit in edits.items()]
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        return dialog, edits

    def apply_resource_paths(self, paths: dict[str, str | Path]) -> bool:
        """
        Description: Validate, remember and apply new resource folders (an empty value restores the default); the theme, icons and languages are reloaded.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param paths

        @returns
        """
        resolved: dict[str, Path] = {}
        for key, default in DEFAULT_RESOURCE_PATHS.items():
            value = str(paths.get(key, "") or "").strip()
            path = Path(value) if value else default
            if not path.is_dir():
                QMessageBox.warning(
                    self,
                    tr("Chemin invalide"),
                    f"{tr(RESOURCE_PATH_LABELS[key])} : {tr('le dossier est introuvable')} ({path}).",
                )
                return False
            resolved[key] = path
        for key, path in resolved.items():
            if path.resolve() == DEFAULT_RESOURCE_PATHS[key].resolve():
                self._settings.remove(f"resource_path_{key}")
            else:
                self._settings.setValue(f"resource_path_{key}", str(path.resolve()))
        self.resource_paths = resolved
        # Le thème courant est rechargé depuis le nouveau dossier s'il y existe.
        theme = self.current_theme_path
        candidate = resolved["themes"] / theme.name if theme is not None else None
        if candidate is not None and candidate.is_file():
            self._load_theme_path(candidate, persist=False, quiet=True)
        elif theme is not None and theme.is_file():
            self._load_theme_path(theme, persist=False, quiet=True)
        else:
            self._apply_default_theme()
        self._update_themes_menu()
        if not self.set_language(translator.language, persist=False, quiet=True):
            self.set_language(SOURCE_LANGUAGE, persist=False, quiet=True)
        self.statusBar().showMessage(tr("Chemins des ressources mis à jour."))
        return True

    # ------------------------------------------------------------------
    # Langue de l'interface
    # ------------------------------------------------------------------
    def _apply_saved_language(self) -> None:
        """
        Description: Apply the language chosen by the user, otherwise APP_LANGUAGE (French when unavailable).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        code = str(self._settings.value("language", "") or config.app_language or SOURCE_LANGUAGE)
        if not self.set_language(code, persist=False, quiet=True):
            self.set_language(SOURCE_LANGUAGE, persist=False, quiet=True)

    def set_language(self, code: str, persist: bool = True, quiet: bool = False) -> bool:
        """
        Description: Load the translation file of ``code`` from the translations folder and re-translate the whole interface.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-26
        @version 9

        @param code
        @param persist  remember the choice for the next sessions
        @param quiet    do not show an error dialog

        @returns
        """
        if not translator.set_language(code, self.resource_paths["translations"]):
            if not quiet:
                QMessageBox.warning(
                    self,
                    tr("Langue indisponible"),
                    f"{tr('Impossible de charger le fichier de traduction')} « {code}.json ».",
                )
            self._update_language_menu()
            return False
        if persist:
            self._settings.setValue("language", code)
        self.retranslate_ui()
        self._update_language_menu()
        return True

    def _update_language_menu(self) -> None:
        """
        Description: Rebuild the "Langue" sub-menu from the translation files found; the active language is checked.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if not hasattr(self, "language_menu"):
            return
        self.language_menu.clear()
        group = QActionGroup(self.language_menu)
        group.setExclusive(True)
        for code, name in Translator.available_languages(self.resource_paths["translations"]).items():
            action = self.language_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(code == translator.language)
            action.setData(code)
            group.addAction(action)
            action.triggered.connect(lambda _checked, language=code: self.set_language(language))

    def retranslate_ui(self) -> None:
        """
        Description: Translate every text of the interface (menus, actions, buttons, labels, panels, tooltips) into the active language.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        rt = translator.retranslate
        self.setWindowTitle(rt(self.windowTitle()))
        for widget in [self, *self.findChildren(QWidget)]:
            if widget.toolTip():
                widget.setToolTip(rt(widget.toolTip()))
            if isinstance(widget, QMenu):
                widget.setTitle(rt(widget.title()))
            elif isinstance(widget, (QDockWidget, QToolBar)):
                widget.setWindowTitle(rt(widget.windowTitle()))
            elif isinstance(widget, QGroupBox):
                widget.setTitle(rt(widget.title()))
            elif isinstance(widget, QAbstractButton):
                # Les boutons d'une barre d'outils reprennent le texte de leur action.
                if widget.text() and not (isinstance(widget, QToolButton) and widget.defaultAction() is not None):
                    widget.setText(rt(widget.text()))
            elif isinstance(widget, QLabel):
                if widget.text():
                    widget.setText(rt(widget.text()))
            elif isinstance(widget, QComboBox):
                for index in range(widget.count()):
                    widget.setItemText(index, rt(widget.itemText(index)))
        for action in self.findChildren(QAction):
            if action.text():
                action.setText(rt(action.text()))
            if action.toolTip():
                action.setToolTip(rt(action.toolTip()))
        self._update_palette_tooltips()
        if hasattr(self, "grid_toggle_button"):
            self.toggle_rotation_grid(self.grid_toggle_button.isChecked())
        if hasattr(self, "loupe_zoom_spin"):
            self._sync_loupe_controls()
        self.refresh_objects_list()

    # ------------------------------------------------------------------
    # Réinitialisation des paramètres
    # ------------------------------------------------------------------
    def reset_settings(self, confirm: bool = True) -> bool:
        """
        Description: Restore the default configuration: theme, resource paths, language, export notification, custom colours, remembered .env file and window layout.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param confirm  ask the user first

        @returns
        """
        if confirm:
            reply = QMessageBox.question(
                self,
                tr("Réinitialiser les paramètres"),
                tr(
                    "Rétablir les valeurs par défaut (thème, langue, chemins des ressources, couleurs "
                    "personnalisées, notification après l'export, configuration .env et disposition des fenêtres) ?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return False
        self._settings.clear()
        # Oublier les variables du fichier .env mémorisé, puis relire la configuration par défaut.
        for key in self._env_loaded_keys:
            os.environ.pop(key, None)
        self._env_loaded_keys = []
        load_dotenv()
        update_config_in_place(AppConfig())
        self.canvas.current_stroke_width = config.default_stroke_width
        self.stroke_width_spin.setValue(config.default_stroke_width)
        self._update_multi_loupe_visibility()
        self.resource_paths = dict(DEFAULT_RESOURCE_PATHS)
        self.restoreState(self._default_window_state)
        self.main_toolbar.show()
        self.graphical_tools_palette.show()
        self._apply_default_theme()
        self._update_themes_menu()
        if not self.set_language(config.app_language, persist=False, quiet=True):
            self.set_language(SOURCE_LANGUAGE, persist=False, quiet=True)
        self.export_notification_action.blockSignals(True)
        self.export_notification_action.setChecked(True)
        self.export_notification_action.blockSignals(False)
        self._refresh_color_palettes()
        self.statusBar().showMessage(tr("Paramètres réinitialisés aux valeurs par défaut."))
        return True

    # ------------------------------------------------------------------
    # Annuler / Rétablir (Ctrl+Z / Ctrl+Y)
    # ------------------------------------------------------------------
    def _capture_state(self) -> str | None:
        """
        Description: Serialize the current edits (recipe without the user palette) to compare and restore them.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if self.source_path is None or self.original_image is None:
            return None
        data = self.build_recipe().to_dict()
        data["custom_colors"] = []
        return json.dumps(data, sort_keys=True)

    def _record_history(self) -> None:
        """
        Description: Push the previous state on the undo stack when the edits changed (called on every automatic save).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if self._restoring_history:
            return
        state = self._capture_state()
        if state is None or state == self._history_state:
            return
        if self._history_state is not None:
            self._undo_stack.append(self._history_state)
            del self._undo_stack[:-_MAX_HISTORY]
            self._redo_stack.clear()
        self._history_state = state
        self._update_history_actions()

    def _reset_history(self) -> None:
        """
        Description: Start a new history from the current state (after opening an image or importing a recipe).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._history_state = self._capture_state()
        self._update_history_actions()

    def _update_history_actions(self) -> None:
        """
        Description: Enable "Annuler"/"Rétablir" only when there is something to undo/redo.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if hasattr(self, "undo_action"):
            self.undo_action.setEnabled(bool(self._undo_stack))
            self.redo_action.setEnabled(bool(self._redo_stack))

    def undo(self) -> bool:
        """
        Description: Undo the last modification (Ctrl+Z).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if not self._undo_stack or self._history_state is None:
            return False
        self._redo_stack.append(self._history_state)
        self._restore_state(self._undo_stack.pop())
        self.statusBar().showMessage(tr("Modification annulée."))
        return True

    def redo(self) -> bool:
        """
        Description: Redo the last undone modification (Ctrl+Y).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if not self._redo_stack or self._history_state is None:
            return False
        self._undo_stack.append(self._history_state)
        self._restore_state(self._redo_stack.pop())
        self.statusBar().showMessage(tr("Modification rétablie."))
        return True

    def _restore_state(self, state: str) -> None:
        """
        Description: Rebuild the canvas and panels from a serialized state, then save the JSON without recording a new step.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param state

        @returns
        """
        self._restoring_history = True
        try:
            self.canvas.selected_item = None
            self.canvas.crop_rect = None
            self.apply_recipe_to_ui(ProcessingRecipe.from_dict(json.loads(state)))
            self._history_state = self._capture_state()
            self.canvas.update()
            self.auto_save_recipe()
        finally:
            self._restoring_history = False
        self._update_history_actions()

    # ------------------------------------------------------------------
    # Copier / Coller (Ctrl+C / Ctrl+V)
    # ------------------------------------------------------------------
    @staticmethod
    def _clone_object(item: AnnotationItem | LoupeOverlay) -> AnnotationItem | LoupeOverlay:
        """
        Description: Independent copy of an annotation or a loupe (all its characteristics, new geometry objects).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param item

        @returns
        """
        if isinstance(item, LoupeOverlay):
            return replace(
                item,
                center=QPointF(item.center),
                arrow=(QPointF(item.arrow[0]), QPointF(item.arrow[1])),
                color=QColor(item.color),
            )
        return replace(
            item,
            start=QPointF(item.start) if item.start is not None else None,
            end=QPointF(item.end) if item.end is not None else None,
            color=QColor(item.color),
        )

    def copy_selection(self) -> int:
        """
        Description: Copy the selected objects (annotations and loupes); return how many were copied.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        items = self.canvas.selected_objects()
        if not items:
            self.statusBar().showMessage(tr("Aucun objet sélectionné à copier."))
            return 0
        self._clipboard = [self._clone_object(item) for item in items]
        self._paste_count = 0
        self.statusBar().showMessage(f"{len(items)} {tr('objet(s) copié(s).')}")
        return len(items)

    def paste_clipboard(self) -> list[AnnotationItem | LoupeOverlay]:
        """
        Description: Paste a copy of the copied objects, shifted at each paste and placed in front of the other layers; the pasted objects become the selection.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if not self._clipboard or self.preview_image is None:
            return []
        if any(isinstance(item, LoupeOverlay) for item in self._clipboard) and self.canvas.loupes and not config.feature_multi_loupe:
            self.statusBar().showMessage(tr("Plusieurs loupes : fonctionnalité désactivée (FEATURE_MULTI_LOUPE=false)."))
            return []
        # Compléter l'ordre des calques avant d'y insérer les nouveaux objets.
        self.refresh_objects_list()
        self._paste_count += 1
        offset = QPointF(_PASTE_OFFSET * self._paste_count, _PASTE_OFFSET * self._paste_count)
        pasted: list[AnnotationItem | LoupeOverlay] = []
        tokens: list[str] = []
        for source in self._clipboard:
            clone = self._clone_object(source)
            ImageCanvas.translate_item(clone, offset)
            if isinstance(clone, LoupeOverlay):
                clone.id = next_loupe_id(self.canvas.loupes)
                self.canvas.loupes.append(clone)
            else:
                clone.id = next_annotation_id(self.canvas.annotations)
                self.canvas.annotations.append(clone)
            tokens.append(clone.layer_token)
            pasted.append(clone)
        self.layer_order = [*tokens, *(token for token in self.layer_order if token not in tokens)]
        self.canvas.set_selection(pasted)
        self.refresh_objects_list()
        self._on_canvas_item_selected(self.canvas.selected_item)
        self.canvas.update()
        self.auto_save_recipe(force=True)
        self.statusBar().showMessage(f"{len(pasted)} {tr('objet(s) collé(s).')}")
        return pasted

    # ------------------------------------------------------------------
    # Glisser-déposer d'un fichier image sur la fenêtre
    # ------------------------------------------------------------------
    @staticmethod
    def _dropped_image_path(mime_data) -> Path | None:
        """
        Description: First local image file carried by a drag-and-drop, if any.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param mime_data

        @returns
        """
        if mime_data is None or not mime_data.hasUrls():
            return None
        for url in mime_data.urls():
            if url.isLocalFile():
                path = Path(url.toLocalFile())
                if path.suffix.lower() in IMAGE_FILE_SUFFIXES and path.is_file():
                    return path
        return None

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Accept an image file dragged over the window.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param event

        @returns
        """
        if self._dropped_image_path(event.mimeData()) is not None:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Keep accepting the dragged image file while it moves over the window.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param event

        @returns
        """
        self.dragEnterEvent(event)

    def dropEvent(self, event) -> None:  # type: ignore[override]
        """
        Description: Open the image file dropped on the window (its JSON recipe is reloaded if it exists).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param event

        @returns
        """
        path = self._dropped_image_path(event.mimeData())
        if path is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.load_source_image(path)

    def load_environment_file(self, file_name: str | None = None) -> None:
        """
        Description: Load a .env file: application parameters and feature flags, plus APP_THEME if the file defines it.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @param file_name

        @returns
        """
        if not file_name:
            file_name, _ = QFileDialog.getOpenFileName(
                self, "Charger une configuration", str(Path.cwd()), "Fichiers .env (*.env);;Tous les fichiers (*)"
            )
        if not file_name:
            return
        loaded_keys = load_dotenv(file_name, override=True)
        self._env_loaded_keys = list(loaded_keys)
        update_config_in_place(AppConfig())
        self.canvas.current_stroke_width = config.default_stroke_width
        self.stroke_width_spin.setValue(config.default_stroke_width)
        self._update_multi_loupe_visibility()
        self._settings.setValue("env_path", file_name)
        if "APP_THEME" in loaded_keys:
            # Le thème du .env devient le thème par défaut : il remplace le choix précédent.
            self._settings.remove("theme_path")
            self._apply_default_theme()
        self.statusBar().showMessage(f"Configuration chargée : {Path(file_name).name}")

    def load_theme_file(self) -> None:
        """
        Description: Ask for a custom .qss file and apply it.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        file_name, _ = QFileDialog.getOpenFileName(self, "Charger un thème", str(Path.cwd()), "Thèmes Qt (*.qss);;Tous les fichiers (*)")
        if not file_name:
            return
        self._load_theme_path(Path(file_name))

    def show_environment_help(self) -> None:
        """
        Description: Explain the scope and persistence of the optional .env configuration.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        QMessageBox.information(
            self,
            "Configuration .env",
            "Un fichier <b>.env</b> permet d'adapter l'application sans modifier son code : "
            "thème appliqué par défaut (<code>APP_THEME</code>), épaisseur de trait par défaut, "
            "qualité d'export et drapeaux de fonctionnalités (<code>FEATURE_…</code>).<br><br>"
            "Les couleurs ne sont plus définies dans le .env : elles proviennent uniquement des "
            "thèmes (<i>Configuration &gt; Thèmes disponibles</i>). Le thème choisi dans ce menu "
            "reste prioritaire sur <code>APP_THEME</code>.<br><br>"
            "Après son chargement, le chemin du fichier .env est mémorisé dans les préférences "
            "et il est relu au prochain démarrage.",
        )

    @staticmethod
    def _validate_stylesheet(path: Path) -> str:
        """
        Description: Read a QSS file and reject the common invalid inputs before applying it.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param path

        @returns
        """
        try:
            stylesheet = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as err:
            raise ValueError(f"lecture impossible : {err}") from err
        if not stylesheet.strip():
            raise ValueError("le fichier est vide")
        if stylesheet.count("{") != stylesheet.count("}"):
            raise ValueError("les accolades du style ne sont pas équilibrées")
        if "{" not in stylesheet or "}" not in stylesheet:
            raise ValueError("aucune règle QSS n'a été trouvée")
        return stylesheet

    def _load_theme_path(self, path: Path, persist: bool = True, quiet: bool = False) -> bool:
        """
        Description: Validate and apply one stylesheet (plus its optional icon and SVG icon colour); return False after a clear error.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 4

        @param path
        @param persist  remember the theme for the next sessions
        @param quiet    do not show an error dialog (used at start-up)

        @returns
        """
        try:
            stylesheet = self._validate_stylesheet(path)
        except ValueError as err:
            if not quiet:
                QMessageBox.warning(self, "Thème invalide", f"Impossible de charger « {path.name} » : {err}.")
            return False
        match = _THEME_ICON_COLOR_RE.search(stylesheet)
        self._icon_color = QColor(match.group(1)) if match else self.palette().color(self.foregroundRole())
        checked_match = _THEME_ICON_CHECKED_COLOR_RE.search(stylesheet)
        self._icon_checked_color = QColor(checked_match.group(1)) if checked_match else None
        self.setStyleSheet(self._resolve_theme_icons(stylesheet, self._icon_color, self.resource_paths["icons"]))
        self.current_theme_path = path
        for icon_name in _THEME_ICON_NAMES:
            icon_path = path.parent / icon_name
            if icon_path.is_file():
                icon = QIcon(str(icon_path))
                if not icon.isNull():
                    self.setWindowIcon(icon)
                    app = QApplication.instance()
                    if app is not None:
                        app.setWindowIcon(icon)
                break
        self._refresh_themed_icons()
        self._update_themes_menu()
        if persist:
            self._settings.setValue("theme_path", str(path.resolve()))
        self.statusBar().showMessage(f"Thème chargé : {self._theme_display_name(path)}")
        return True

    @staticmethod
    def _resolve_theme_icons(stylesheet: str, color: QColor, icons_directory: Path = ICONS_DIRECTORY) -> str:
        """
        Description: Replace every "url(@icons/<nom>.svg)" of a theme by a copy of that bundled icon tinted with ``color`` (QSS cannot recolour an image itself).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param stylesheet
        @param color
        @param icons_directory  configured icons folder (the bundled icon is used when a file is missing)

        @returns
        """
        cache_dir = Path(tempfile.gettempdir()) / "iat-theme-icons" / color.name().lstrip("#")

        def tinted_copy(match: re.Match[str]) -> str:
            source = icons_directory / match.group(1)
            if not source.is_file():
                source = ICONS_DIRECTORY / match.group(1)
            if not source.is_file():
                return "url()"
            svg = source.read_text(encoding="utf-8")
            for placeholder in _SVG_PLACEHOLDER_COLORS:
                svg = re.sub(re.escape(placeholder) + r"(?![0-9A-Fa-f])", color.name(), svg, flags=re.IGNORECASE)
            target = cache_dir / source.name
            try:
                cache_dir.mkdir(parents=True, exist_ok=True)
                if not target.is_file() or target.read_text(encoding="utf-8") != svg:
                    target.write_text(svg, encoding="utf-8")
            except OSError:
                target = source
            return f"url({target.as_posix()})"

        return _THEME_ICON_URL_RE.sub(tinted_copy, stylesheet)

    def _apply_default_theme(self) -> bool:
        """
        Description: Apply the theme named by APP_THEME (config/.env), falling back to the CBI theme.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        themes = self._available_themes()
        for wanted in (config.app_theme, "cbi"):
            for path in themes:
                if wanted and wanted.casefold() in (path.stem.casefold(), path.parent.name.casefold()):
                    if self._load_theme_path(path, persist=False, quiet=True):
                        return True
        return False

    def _available_themes(self) -> list[Path]:
        """
        Description: Return bundled QSS themes, including optional per-theme folders.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        themes_directory = self.resource_paths["themes"]
        if not themes_directory.is_dir():
            return []
        return sorted((p for p in themes_directory.rglob("*.qss") if p.is_file()), key=lambda p: p.name.casefold())

    @staticmethod
    def _theme_display_name(path: Path) -> str:
        """
        Description: Human-readable theme name; a "themes/<nom>/style.qss" file is named after its folder.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param path

        @returns
        """
        stem = path.parent.name if path.stem.casefold() == "style" else path.stem
        return _THEME_DISPLAY_NAMES.get(stem.casefold(), stem.replace("-", " ").title())

    def _update_themes_menu(self) -> None:
        """
        Description: Rebuild the "Thèmes disponibles" sub-menu; the active theme is checked.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        if not hasattr(self, "themes_menu"):
            return
        self.themes_menu.clear()
        themes = self._available_themes()
        if not themes:
            empty = self.themes_menu.addAction("(aucun thème installé)")
            empty.setEnabled(False)
            return
        group = QActionGroup(self.themes_menu)
        group.setExclusive(True)
        for path in themes:
            action = self.themes_menu.addAction(self._theme_display_name(path))
            action.setCheckable(True)
            action.setChecked(self.current_theme_path is not None and path.resolve() == self.current_theme_path.resolve())
            action.setToolTip(str(path))
            group.addAction(action)
            action.triggered.connect(lambda _checked, theme_path=path: self._load_theme_path(theme_path))

    def _refresh_themed_icons(self) -> None:
        """
        Description: Re-tint the SVG icons (tool bar "outils" icon, graphical palette) with the theme icon colour.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 2

        @returns
        """
        if hasattr(self, "toolbar_tools_icon"):
            icon = tinted_svg_icon(self._icon_path("tools.svg"), self._icon_color)
            self.toolbar_tools_icon.setPixmap(icon.pixmap(QSize(20, 20)))
        for key, action in getattr(self, "graphical_tool_actions", {}).items():
            file_name = _PALETTE_ICON_FILES.get(key)
            if file_name:
                action.setIcon(
                    tinted_svg_icon(self._icon_path(file_name), self._icon_color, checked_color=self._icon_checked_color)
                )

    def _build_toolbar(self) -> None:
        """
        Description: Horizontal tool bar: the "outils" icon on the left, then text-only buttons "Ouvrir une image" | "Transformation", "Annotation", "Outil loupe" | "Exporter l'image".

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        toolbar = self.addToolBar("Barre horizontale des outils")
        toolbar.setObjectName("main_toolbar")
        # Boutons texte uniquement : les icônes sont réservées à la palette graphique.
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.main_toolbar = toolbar

        self.toolbar_tools_icon = QLabel()
        self.toolbar_tools_icon.setObjectName("toolbar_tools_icon")
        self.toolbar_tools_icon.setToolTip("Outils")
        self.toolbar_tools_icon.setContentsMargins(6, 0, 6, 0)
        toolbar.addWidget(self.toolbar_tools_icon)

        toolbar.addAction(self.open_action)
        toolbar.addSeparator()

        # Les familles d'outils ouvrent directement leurs options associées.
        self.toolbar_tool_buttons: dict[str, QToolButton] = {}
        self._add_toolbar_tool_button(toolbar, TOOL_ROTATE_LINE, display_label="Transformation")
        self._add_toolbar_tool_button(toolbar, TOOL_TEXT, display_label="Annotation")
        self._add_toolbar_tool_button(toolbar, TOOL_LOUPE, display_label="Outil loupe")
        toolbar.addSeparator()
        toolbar.addAction(self.export_action)

        # ⑫ Logo CBI : affiché dans la barre d'état pour garder la barre d'outils
        # composée uniquement de boutons texte.
        logo_path = ICONS_DIRECTORY / "logo_cbi.png"
        if logo_path.exists():
            logo_label = QLabel()
            logo_label.setObjectName("status_logo_cbi")
            logo_label.setPixmap(QPixmap(str(logo_path)).scaledToHeight(20, Qt.TransformationMode.SmoothTransformation))
            logo_label.setToolTip("Centre de Biologie Intégrative (CBI)")
            self.statusBar().addPermanentWidget(logo_label)

        self._build_graphical_tools_palette()
        self._refresh_themed_icons()

    def _build_graphical_tools_palette(self) -> None:
        """
        Description: Create a movable/floating icon-only mirror of the main tool bar, sharing its actions (no duplicated logic).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        palette = QToolBar("Palette graphique des outils", self)
        palette.setObjectName("graphical_tools_palette")
        palette.setMovable(True)
        palette.setFloatable(True)
        palette.setIconSize(QSize(28, 28))
        palette.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, palette)
        self.graphical_tools_palette = palette
        self.graphical_tool_actions: dict[str, QAction] = {}

        self._palette_entries = entries = (
            ("open", self.open_action, "Ouvrir une image", "Ouvrir une image brute à annoter."),
            (TOOL_ROTATE_LINE, None, "Transformation", TOOL_DESCRIPTIONS[TOOL_ROTATE_LINE][1]),
            (TOOL_TEXT, None, "Annotation", "Étiquettes, rectangles, cercles et lignes fléchées."),
            (TOOL_LOUPE, None, "Outil loupe", TOOL_DESCRIPTIONS[TOOL_LOUPE][1]),
            ("export", self.export_action, "Exporter l'image", "Régler la taille puis exporter l'image annotée en JPEG."),
        )
        for key, shared_action, label, help_text in entries:
            if shared_action is not None:
                action = shared_action
            else:
                action = QAction(label, self)
                action.setCheckable(True)
                action.triggered.connect(lambda _checked, tool=key: self._on_toolbar_tool_clicked(tool))
            palette.addAction(action)
            self.graphical_tool_actions[key] = action
        self._update_palette_tooltips()

    def _update_palette_tooltips(self) -> None:
        """
        Description: Explicit tooltips of the graphical palette (tool name in bold + description), in the active language.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        for key, _shared_action, label, help_text in getattr(self, "_palette_entries", ()):
            action = self.graphical_tool_actions.get(key)
            if action is not None:
                action.setToolTip(f"<b>{tr(label)}</b><br>{tr(help_text)}")

    def _sync_tool_action_states(self, active_tool: str | None = None) -> None:
        """
        Description: Keep the text tool bar and the icon-only palette visually in sync.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @param active_tool

        @returns
        """
        if not hasattr(self, "graphical_tool_actions"):
            return
        family = TOOL_TEXT if active_tool in ANNOTATION_FAMILY_TOOLS else active_tool
        family = TOOL_ROTATE_LINE if family == TOOL_CROP else family
        for tool, action in self.graphical_tool_actions.items():
            if tool not in {"open", "export"}:
                action.setEnabled(self.original_image is not None)
                action.setChecked(tool == family)
        self.graphical_tool_actions["export"].setChecked(active_tool == "export")

    def _add_toolbar_tool_button(self, toolbar, tool: str, display_label: str | None = None) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param toolbar
        @param tool
        @param display_label

        @returns
        """
        label, tooltip = TOOL_DESCRIPTIONS[tool]
        label = display_label or label
        button = QToolButton()
        button.setText(label)
        button.setToolTip(tooltip)
        button.setCheckable(True)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        button.clicked.connect(lambda _checked, t=tool: self._on_toolbar_tool_clicked(t))
        toolbar.addWidget(button)
        self.toolbar_tool_buttons[tool] = button

    def _build_tools_dock(self) -> None:
        """
        Description: Retained as a compatibility hook; tool selection now lives in the toolbar.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        self.tool_buttons: dict[str, QToolButton] = {}

    def _build_objects_dock(self) -> None:
        """
        Description: Left-docked panel: list of applied objects and treatments, with selection highlighting on the canvas and a button to remove elements.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        dock = QDockWidget("Liste des annotations", self)
        dock.setObjectName("objects_dock")
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        dock.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        content = QWidget()
        layout = QVBoxLayout(content)

        info_label = QLabel("Objets ajoutés à l'image :")
        layout.addWidget(info_label)

        self.objects_list = QListWidget()
        # Maj + clic : sélection d'une plage ; Ctrl + clic : ajout/retrait d'un objet.
        self.objects_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.objects_list.setDragEnabled(True)
        self.objects_list.setAcceptDrops(True)
        self.objects_list.setDropIndicatorShown(True)
        self.objects_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.objects_list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.objects_list.itemSelectionChanged.connect(self._on_object_selection_changed)
        self.objects_list.model().rowsMoved.connect(self._on_objects_reordered)
        layout.addWidget(self.objects_list)

        btn_layout = QHBoxLayout()
        self.delete_object_button = QPushButton("Supprimer l'élément")
        self.delete_object_button.setToolTip(
            "Supprimer les éléments sélectionnés du preview et du fichier JSON (Touche Suppr). "
            "Maj + clic sélectionne une plage, Ctrl + clic ajoute ou retire un élément."
        )
        self.delete_object_button.setEnabled(False)
        self.delete_object_button.clicked.connect(self.delete_selected_object)
        btn_layout.addWidget(self.delete_object_button)
        layout.addLayout(btn_layout)

        dock.setWidget(content)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.objects_dock = dock

    def _on_stroke_width_changed(self, value: int) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param value

        @returns
        """
        self.canvas.current_stroke_width = value
        if isinstance(self.canvas.selected_item, AnnotationItem):
            self.canvas.selected_item.stroke_width = value
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_border_radius_changed(self, value: int) -> None:
        """
        Description: ⑨ Mise à jour du rayon de coin de l'item sélectionné et du prochain tracé.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param value

        @returns
        """
        self.canvas.current_border_radius = value
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind in ("rect", "label"):
            self.canvas.selected_item.border_radius = value
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_label_shape_changed(self, _index: int) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param _index

        @returns
        """
        shape = self.label_shape_combo.currentData()
        self.canvas.current_label_shape = shape
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "label":
            self.canvas.selected_item.shape = shape
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_show_arrow_changed(self, checked: bool) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param checked

        @returns
        """
        self.canvas.current_show_arrow = checked
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "label":
            self.canvas.selected_item.show_arrow = checked
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_arrow_stroke_width_changed(self, value: int) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param value

        @returns
        """
        self.canvas.current_arrow_stroke_width = value
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "label":
            self.canvas.selected_item.arrow_stroke_width = value
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_show_text_changed(self, checked: bool) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param checked

        @returns
        """
        self.canvas.current_show_text = checked
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "label":
            self.canvas.selected_item.show_text = checked
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_fill_enabled_changed(self, checked: bool) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param checked

        @returns
        """
        self.canvas.current_fill_enabled = checked
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "label":
            self.canvas.selected_item.fill_enabled = checked
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_bold_text_changed(self, checked: bool) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param checked

        @returns
        """
        self.canvas.current_bold_text = checked
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "label":
            self.canvas.selected_item.bold_text = checked
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _select_annotation_shape(self, tool: str) -> None:
        """Switch which shape the "Annotation" tool currently draws (étiquette/rectangle/cercle/ligne)."""
        self.select_tool(tool)

    def _update_annotation_options_for_kind(self, kind: str) -> None:
        """Disable controls that do not apply to the selected annotation type."""
        if not hasattr(self, "label_shape_combo"):
            return
        is_label = kind == "label"
        is_line = kind == "line"
        supports_radius = kind in {"rect", "label"}
        for widget in (
            self.label_shape_combo,
            self.fill_enabled_checkbox,
            self.show_text_checkbox,
            self.bold_text_checkbox,
            self.show_arrow_checkbox,
            self.arrow_stroke_width_spin,
        ):
            widget.setEnabled(is_label)
        self.border_radius_spin.setEnabled(supports_radius)
        self.line_arrow_start_checkbox.setEnabled(is_line)
        self.line_arrow_end_checkbox.setEnabled(is_line)

    def _on_line_arrow_start_changed(self, checked: bool) -> None:
        self.canvas.current_line_arrow_start = checked
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "line":
            self.canvas.selected_item.line_arrow_start = checked
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_line_arrow_end_changed(self, checked: bool) -> None:
        self.canvas.current_line_arrow_end = checked
        if isinstance(self.canvas.selected_item, AnnotationItem) and self.canvas.selected_item.kind == "line":
            self.canvas.selected_item.line_arrow_end = checked
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()

    def _on_object_selection_changed(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        selected_items = self.objects_list.selectedItems()
        if selected_items:
            current = self.objects_list.currentItem()
            primary_item = current if current is not None and current.isSelected() else selected_items[0]
            payload = primary_item.data(Qt.ItemDataRole.UserRole)
            visual = [
                item.data(Qt.ItemDataRole.UserRole)
                for item in selected_items
                if isinstance(item.data(Qt.ItemDataRole.UserRole), (AnnotationItem, LoupeOverlay))
            ]
            self.canvas.selected_item = payload
            self._show_object_options(payload)
            self.delete_object_button.setEnabled(True)
            self._sync_panel_to_payload(payload)
            if len(visual) > 1:
                # Sélection multiple (Maj/Ctrl + clic) : l'élément courant pilote le panneau.
                self.canvas.set_selection(visual, payload if isinstance(payload, (AnnotationItem, LoupeOverlay)) else None)
        else:
            self.canvas.selected_item = None
            self.delete_object_button.setEnabled(False)
        self.canvas.update()

    def _sync_panel_to_payload(self, payload: object) -> None:
        """
        Description: Reflect a selected object's stroke width, corner radius and color in the right-hand panel.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param payload

        @returns
        """
        if isinstance(payload, AnnotationItem):
            self._update_annotation_options_for_kind(payload.kind)
            self.stroke_width_spin.blockSignals(True)
            self.stroke_width_spin.setValue(payload.stroke_width)
            self.stroke_width_spin.blockSignals(False)
            self.border_radius_spin.blockSignals(True)
            self.border_radius_spin.setValue(payload.border_radius)
            self.border_radius_spin.blockSignals(False)
            self._set_current_color(payload.color, apply_to_selection=False)
            if payload.kind == "label":
                self.label_shape_combo.blockSignals(True)
                shape_index = self.label_shape_combo.findData(payload.shape)
                self.label_shape_combo.setCurrentIndex(max(0, shape_index))
                self.label_shape_combo.blockSignals(False)
                self.show_arrow_checkbox.blockSignals(True)
                self.show_arrow_checkbox.setChecked(payload.show_arrow)
                self.show_arrow_checkbox.blockSignals(False)
                self.arrow_stroke_width_spin.blockSignals(True)
                self.arrow_stroke_width_spin.setValue(payload.arrow_stroke_width)
                self.arrow_stroke_width_spin.blockSignals(False)
                self.show_text_checkbox.blockSignals(True)
                self.show_text_checkbox.setChecked(payload.show_text)
                self.show_text_checkbox.blockSignals(False)
                self.fill_enabled_checkbox.blockSignals(True)
                self.fill_enabled_checkbox.setChecked(payload.fill_enabled)
                self.fill_enabled_checkbox.blockSignals(False)
                self.bold_text_checkbox.blockSignals(True)
                self.bold_text_checkbox.setChecked(payload.bold_text)
                self.bold_text_checkbox.blockSignals(False)
            elif payload.kind == "line":
                self.line_arrow_start_checkbox.blockSignals(True)
                self.line_arrow_start_checkbox.setChecked(payload.line_arrow_start)
                self.line_arrow_start_checkbox.blockSignals(False)
                self.line_arrow_end_checkbox.blockSignals(True)
                self.line_arrow_end_checkbox.setChecked(payload.line_arrow_end)
                self.line_arrow_end_checkbox.blockSignals(False)
        elif isinstance(payload, LoupeOverlay):
            self._sync_loupe_controls(payload)
            self._set_current_color(payload.color, apply_to_selection=False)

    def _show_object_options(self, payload: object) -> None:
        """
        Description: Select the tool page matching an object selected in the UI.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param payload

        @returns
        """
        if isinstance(payload, AnnotationItem):
            tool = {
                "rect": TOOL_RECT,
                "circle": TOOL_CIRCLE,
                "label": TOOL_TEXT,
                "line": TOOL_LINE,
            }.get(payload.kind, TOOL_TEXT)
            self.select_tool(tool)
            return
        if isinstance(payload, LoupeOverlay):
            self.select_tool(TOOL_LOUPE, select_default_loupe=False)
            return

        tool = {
            "crop": TOOL_CROP,
            "rotation": TOOL_ROTATE_LINE,
            "trapezoid": TOOL_ROTATE_LINE,
            "adjustments": "adjustments",
        }.get(payload, TOOL_VIEW)
        self.select_tool(tool if tool in self.option_page_map else TOOL_VIEW)
        if tool == "adjustments":
            self.option_pages.setCurrentIndex(self.option_page_map[tool])

    def _on_canvas_item_selected(self, item: object) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param item

        @returns
        """
        if not hasattr(self, "objects_list"):
            return
        if isinstance(item, (AnnotationItem, LoupeOverlay)) and not self.canvas.is_selected(item):
            # Le panneau d'options agit sur l'objet sélectionné (loupe courante…).
            self.canvas.selected_item = item
        wanted = self.canvas.selected_objects()
        self.objects_list.blockSignals(True)
        found = False
        for i in range(self.objects_list.count()):
            list_item = self.objects_list.item(i)
            data = list_item.data(Qt.ItemDataRole.UserRole)
            is_primary = data is item or (isinstance(data, str) and data == item)
            if is_primary:
                self.objects_list.setCurrentItem(list_item, QItemSelectionModel.SelectionFlag.NoUpdate)
            if is_primary or any(data is selected for selected in wanted):
                list_item.setSelected(True)
                found = True
                self.delete_object_button.setEnabled(True)
            else:
                list_item.setSelected(False)
        if not found:
            self.objects_list.clearSelection()
            self.delete_object_button.setEnabled(False)
        else:
            self._show_object_options(item)
            self._sync_panel_to_payload(item)
        self.objects_list.blockSignals(False)

    def delete_selected_object(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        selected = self.objects_list.selectedItems()
        if not selected and self.objects_list.currentItem() is not None:
            selected = [self.objects_list.currentItem()]
        payloads: list[object] = [list_item.data(Qt.ItemDataRole.UserRole) for list_item in selected]
        if not payloads:
            # Sélection faite sur l'image (Maj + clic) sans passer par la liste.
            payloads = list(self.canvas.selected_objects())
        if not payloads:
            return
        if len(payloads) > 1:
            for payload in payloads:
                self._delete_payload(payload)
            self.statusBar().showMessage(f"{len(payloads)} {tr('éléments supprimés.')}")
        else:
            self._delete_payload(payloads[0])

        self.canvas.selected_item = None
        self.canvas.update()
        self.refresh_objects_list()
        self.auto_save_recipe()

    def _delete_payload(self, payload: object) -> None:
        """
        Description: Remove one element of the objects list (annotation, loupe or treatment) from the preview and the recipe.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param payload

        @returns
        """
        if isinstance(payload, AnnotationItem):
            if payload in self.canvas.annotations:
                self.canvas.annotations.remove(payload)
                self.layer_order = [token for token in self.layer_order if token != payload.layer_token]
                self.statusBar().showMessage(tr("Annotation supprimée."))
        elif isinstance(payload, LoupeOverlay):
            if payload in self.canvas.loupes:
                self.canvas.loupes.remove(payload)
                self.layer_order = [token for token in self.layer_order if token != payload.layer_token]
                self.statusBar().showMessage(f"{tr('Loupe')} #{payload.id} {tr('supprimée.')}")
        elif payload == "crop":
            self.crop_box = None
            self.canvas.crop_rect = None
            self._rebuild_preview_from_original()
            self.statusBar().showMessage("Rognage réinitialisé.")
        elif payload == "rotation":
            self.apply_rotation(-self.angle_total, absolute=False)
            self.statusBar().showMessage("Rotation réinitialisée.")
        elif payload == "trapezoid":
            self.apply_trapezoid(0.0, 0.0, absolute=True)
            self.statusBar().showMessage("Correction trapézoïdale réinitialisée.")
        elif payload == "adjustments":
            self.brightness_slider.setValue(0)
            self.contrast_slider.setValue(100)
            self.statusBar().showMessage("Luminosité et contraste réinitialisés.")

    def _on_objects_reordered(self, *_args: object) -> None:
        """
        Description: Persist the heterogeneous visual stacking order after an internal move.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param _args

        @returns
        """
        visual_payloads = []
        for index in range(self.objects_list.count()):
            payload = self.objects_list.item(index).data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, (AnnotationItem, LoupeOverlay)):
                visual_payloads.append(payload)

        self.canvas.annotations = [payload for payload in visual_payloads if isinstance(payload, AnnotationItem)]
        self.layer_order = [payload.layer_token for payload in visual_payloads]
        current = self.objects_list.currentItem().data(Qt.ItemDataRole.UserRole) \
            if self.objects_list.currentItem() else None
        selected_visual = [
            item.data(Qt.ItemDataRole.UserRole)
            for item in self.objects_list.selectedItems()
            if isinstance(item.data(Qt.ItemDataRole.UserRole), (AnnotationItem, LoupeOverlay))
        ]
        self.canvas.selected_item = current
        if len(selected_visual) > 1:
            self.canvas.set_selection(selected_visual, current if isinstance(current, (AnnotationItem, LoupeOverlay)) else None)
        self.canvas.update()
        self.auto_save_recipe()

    def refresh_objects_list(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        if not hasattr(self, "objects_list"):
            return
        current_selected = self.canvas.selected_item
        annotation_tokens = [item.layer_token for item in self.canvas.annotations]
        loupe_tokens = [loupe.layer_token for loupe in self.canvas.loupes]
        valid_tokens = set(annotation_tokens) | set(loupe_tokens)
        # Toutes les loupes restent listées, même masquées, pour pouvoir les réafficher.
        order = [token for token in self.layer_order if token in valid_tokens]
        order.extend(token for token in [*annotation_tokens, *loupe_tokens] if token not in order)
        self.layer_order = order
        self.objects_list.blockSignals(True)
        self.objects_list.clear()

        def add_annotation_item(ann: AnnotationItem) -> None:
            """
            Description:

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-27
            @version 3

            @param ann

            @returns
            """
            if ann.kind == "rect":
                label = f"{tr('Rectangle')} #{ann.id} ({tr('Ép.')} {ann.stroke_width}px)"
            elif ann.kind == "circle":
                label = f"{tr('Cercle')} #{ann.id} ({tr('Ép.')} {ann.stroke_width}px)"
            elif ann.kind == "label":
                label = f"{tr('Étiquette')} : \"{ann.text}\" ({tr('Ép.')} {ann.stroke_width}px)"
            elif ann.kind == "line":
                label = f"{tr('Ligne')} #{ann.id} ({tr('Ép.')} {ann.stroke_width}px)"
            else:
                label = f"{ann.kind.capitalize()} #{ann.id}"

            list_item = QListWidgetItem(label)
            list_item.setData(Qt.ItemDataRole.UserRole, ann)
            pixmap = QPixmap(14, 14)
            pixmap.fill(ann.color)
            list_item.setIcon(QIcon(pixmap))
            self.objects_list.addItem(list_item)
            if self.canvas.is_selected(ann):
                list_item.setSelected(True)
                self.objects_list.setCurrentItem(list_item, QItemSelectionModel.SelectionFlag.NoUpdate)

        # Visual layers are shown front-to-back, matching layer_order.
        for token in self.layer_order:
            if token.startswith("loupe:"):
                loupe = self.canvas.loupe_for_token(token)
                if loupe is None:
                    continue
                visibility = "" if loupe.enabled else f" ({tr('masquée')})"
                loupe_item = QListWidgetItem(
                    f"{tr('Loupe')} #{loupe.id} (Zoom ×{loupe.zoom:.1f}, {tr('Ép.')} {loupe.stroke_width}px){visibility}"
                )
                loupe_item.setData(Qt.ItemDataRole.UserRole, loupe)
                pixmap = QPixmap(14, 14)
                pixmap.fill(loupe.color)
                loupe_item.setIcon(QIcon(pixmap))
                self.objects_list.addItem(loupe_item)
                if self.canvas.is_selected(loupe):
                    loupe_item.setSelected(True)
                    self.objects_list.setCurrentItem(loupe_item, QItemSelectionModel.SelectionFlag.NoUpdate)
            elif token.startswith("annotation:"):
                item = self.canvas.annotation_for_token(token)
                if item is None:
                    continue
                add_annotation_item(item)

        # Non-visual treatments remain listed after the visual layers.
        # 3. Crop
        if self.crop_box is not None:
            crop_w = int(abs(self.crop_box[2] - self.crop_box[0]))
            crop_h = int(abs(self.crop_box[3] - self.crop_box[1]))
            crop_item = QListWidgetItem(f"Rognage ({crop_w}×{crop_h} px)")
            crop_item.setData(Qt.ItemDataRole.UserRole, "crop")
            self.objects_list.addItem(crop_item)
            if current_selected == "crop":
                crop_item.setSelected(True)
                self.objects_list.setCurrentItem(crop_item, QItemSelectionModel.SelectionFlag.NoUpdate)

        # 4. Rotation
        if abs(self.angle_total) > 0.01:
            rot_item = QListWidgetItem(f"Rotation ({self.angle_total:+.1f}°)")
            rot_item.setData(Qt.ItemDataRole.UserRole, "rotation")
            self.objects_list.addItem(rot_item)
            if current_selected == "rotation":
                rot_item.setSelected(True)
                self.objects_list.setCurrentItem(rot_item, QItemSelectionModel.SelectionFlag.NoUpdate)

        if abs(self.trapezoid_top) > 0.0001 or abs(self.trapezoid_bottom) > 0.0001:
            trapezoid_item = QListWidgetItem(
                f"Trapèze (haut {self.trapezoid_top * 100:+.1f}% / bas {self.trapezoid_bottom * 100:+.1f}%)"
            )
            trapezoid_item.setData(Qt.ItemDataRole.UserRole, "trapezoid")
            self.objects_list.addItem(trapezoid_item)
            if current_selected == "trapezoid":
                trapezoid_item.setSelected(True)
                self.objects_list.setCurrentItem(trapezoid_item, QItemSelectionModel.SelectionFlag.NoUpdate)

        # 5. Brightness / Contrast
        if self.brightness != 0 or abs(self.contrast - 1.0) > 0.01:
            adj_item = QListWidgetItem(f"Luminosité ({self.brightness:+.1f}) / Contraste ({self.contrast:.2f}×)")
            adj_item.setData(Qt.ItemDataRole.UserRole, "adjustments")
            self.objects_list.addItem(adj_item)
            if current_selected == "adjustments":
                adj_item.setSelected(True)
                self.objects_list.setCurrentItem(adj_item, QItemSelectionModel.SelectionFlag.NoUpdate)

        self.objects_list.blockSignals(False)
        self.delete_object_button.setEnabled(len(self.objects_list.selectedItems()) > 0)

    def auto_save_recipe(self, force: bool = False) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        if self.source_path is None or self.current_json_path is None:
            return
        self._record_history()
        has_treatments = bool(
            self.canvas.annotations
            or self.canvas.loupes
            or self.crop_box is not None
            or abs(self.angle_total) > 0.01
            or abs(self.trapezoid_top) > 0.0001
            or abs(self.trapezoid_bottom) > 0.0001
            or self.brightness != 0
            or abs(self.contrast - 1.0) > 0.01
        )
        if force or has_treatments or self.current_json_path.exists():
            try:
                recipe = self.build_recipe()
                recipe.save(self.current_json_path)
                self.statusBar().showMessage(
                    f"Recette JSON synchronisée : {self.current_json_path.name}", 3000
                )
            except Exception as err:
                print(f"Erreur sauvegarde auto JSON: {err}")

    def _on_canvas_content_changed(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        self.refresh_objects_list()
        self.auto_save_recipe()

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param event

        @returns
        """
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_object()
        elif event.key() == Qt.Key.Key_Escape:
            # Tâche 4 : Échap → désactiver l'outil courant et revenir à l'état initial
            self._reset_to_initial_state()
        else:
            super().keyPressEvent(event)

    def _set_current_color(self, color: QColor, apply_to_selection: bool = True) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param color
        @param apply_to_selection

        @returns
        """
        self.canvas.current_color = color
        self.current_color_swatch.setStyleSheet(
            f"background-color: {color.name()}; border: 2px solid #444; border-radius: 4px;"
        )
        if apply_to_selection and isinstance(self.canvas.selected_item, AnnotationItem):
            self.canvas.selected_item.color = QColor(color)
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()
        elif apply_to_selection and isinstance(self.canvas.selected_item, LoupeOverlay):
            self.canvas.selected_item.color = QColor(color)
            self.canvas.update()
            self.refresh_objects_list()
            self.auto_save_recipe()
        self.statusBar().showMessage(f"Couleur sélectionnée : {color.name()}")

    def _pick_custom_color(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        color = QColorDialog.getColor(self.canvas.current_color, self, "Choisir une couleur")
        if color.isValid():
            self._remember_custom_color(color)
            self._set_current_color(color)

    def _custom_colors(self) -> list[str]:
        """Return the user palette persisted in Qt settings."""
        raw = self._settings.value("custom_colors", [])
        if isinstance(raw, str):
            raw = [raw]
        if not isinstance(raw, (list, tuple)):
            raw = []
        return [str(value) for value in raw if QColor(str(value)).isValid()]

    def _remember_custom_color(self, color: QColor) -> None:
        """
        Description: Add a custom colour at the head of the user palette and show it in every palette.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @param color

        @returns
        """
        self._persist_custom_colors([color.name(), *self._custom_colors()])
        self._refresh_color_palettes()

    def _persist_custom_colors(self, colors: list[str]) -> None:
        """Store normalized custom swatches in settings and the next JSON save."""
        normalized: list[str] = []
        for value in colors:
            color = QColor(value)
            if color.isValid() and color.name().casefold() not in {item.casefold() for item in normalized}:
                normalized.append(color.name())
        self._settings.setValue("custom_colors", normalized[:12])

    def _build_color_palette_widget(self) -> QWidget:
        """
        Description: Build a colour-palette widget (swatches + custom picker). Shared between the annotation and loupe option panels so both tools offer the exact same set of colours without duplicating the swatch-grid construction logic.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        swatch_grid = QGridLayout()
        swatch_grid.setSpacing(4)
        self._palette_grids.append(swatch_grid)
        self._populate_swatch_grid(swatch_grid)
        layout.addLayout(swatch_grid)

        custom_color_button = QPushButton("Couleur personnalisée…")
        custom_color_button.clicked.connect(self._pick_custom_color)
        layout.addWidget(custom_color_button)
        return container

    def _populate_swatch_grid(self, swatch_grid: QGridLayout) -> None:
        """
        Description: (Re)fill a palette grid with the user's custom colours followed by the standard swatches.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param swatch_grid

        @returns
        """
        while swatch_grid.count():
            widget = swatch_grid.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        colors = list(dict.fromkeys([*self._custom_colors(), *COLOR_PALETTE]))
        for index, hex_color in enumerate(colors):
            swatch = QToolButton()
            swatch.setFixedSize(QSize(32, 32))
            swatch.setToolTip(hex_color)
            swatch.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #444;")
            swatch.clicked.connect(lambda _checked, c=hex_color: self._set_current_color(QColor(c)))
            swatch_grid.addWidget(swatch, index // 3, index % 3)

    def _refresh_color_palettes(self) -> None:
        """
        Description: Rebuild every colour palette (annotation and loupe panels) after the custom colours changed.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        for swatch_grid in self._palette_grids:
            self._populate_swatch_grid(swatch_grid)

    def show_tools_help(self) -> None:
        """
        Description: Summarise every tool of the tool bar, the Ctrl grid snapping and the colour palette.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        lines = [f"<b>{tr(label)}</b> — {tr(tooltip)}" for label, tooltip in TOOL_DESCRIPTIONS.values()]
        for label, text in (
            (
                "Grille",
                "Maintenez Ctrl pendant la création ou le déplacement d'un objet pour l'accrocher à la grille ; "
                "sans Ctrl, l'objet suit librement la souris.",
            ),
            (
                "Sélection multiple",
                "Maj + clic sur l'image ajoute ou retire un objet de la sélection ; dans la liste des annotations, "
                "Maj + clic sélectionne une plage et Ctrl + clic ajoute ou retire un élément. "
                "Glisser un objet sélectionné déplace tout le groupe.",
            ),
            (
                "Alignement",
                "Clic droit sur la sélection : aligner (entre eux, ou par rapport à l'image pour un seul objet), "
                "distribuer (trois objets ou plus) ou accrocher à la grille.",
            ),
            (
                "Édition",
                "Ctrl+Z annule, Ctrl+Y rétablit, Ctrl+C copie et Ctrl+V colle une copie décalée des objets sélectionnés.",
            ),
            ("Ouverture", "Glissez un fichier image sur la fenêtre pour l'ouvrir."),
            (
                "Palette de couleurs",
                "Choisissez une couleur avant de dessiner une étiquette, une loupe ou une zone en surbrillance : "
                "elle sera appliquée au prochain élément créé.",
            ),
        ):
            lines.append(f"<b>{tr(label)}</b> — {tr(text)}")
        QMessageBox.information(self, tr("Aide sur les outils"), "<br><br>".join(lines))

    def _build_about_dialog(self) -> QDialog:
        """
        Description: Build the "À propos" dialog in two columns: the application logo on the left; on the right the information, then one row per link (icon + text, the address shown as a tooltip) and the "Copier l'adresse e-mail" / "Fermer" buttons.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-26
        @version 4

        @returns
        """
        dialog = QDialog(self)
        dialog.setObjectName("about_dialog")
        dialog.setWindowTitle(tr("À propos"))
        dialog.setModal(True)
        columns = QHBoxLayout(dialog)
        columns.setSpacing(24)
        columns.setContentsMargins(24, 24, 24, 24)

        # Colonne gauche : zone réservée au logo de l'application.
        logo_label = QLabel()
        logo_label.setObjectName("about_logo")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedSize(200, 200)
        logo_label.setToolTip(APP_NAME)

        if APP_LOGO_PATH.is_file():
            renderer = QSvgRenderer(str(APP_LOGO_PATH))
            if renderer.isValid():
                # Utilisation de la constante pour la surface du Pixmap
                target_size = QSize(APP_LOGO_SIZE, APP_LOGO_SIZE)
                
                logo = QPixmap(target_size * self.devicePixelRatioF())
                logo.setDevicePixelRatio(self.devicePixelRatioF())
                logo.fill(Qt.GlobalColor.transparent)
                
                painter = QPainter(logo)
                
                # Calcul du ratio d'aspect
                size = renderer.defaultSize().scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio)
                
                # Centrage du rendu dans le carré de taille APP_LOGO_SIZE
                x_offset = (APP_LOGO_SIZE - size.width()) / 2
                y_offset = (APP_LOGO_SIZE - size.height()) / 2
                
                renderer.render(painter, QRectF(x_offset, y_offset, size.width(), size.height()))
                painter.end()
                
                logo_label.setPixmap(logo)

        columns.addWidget(logo_label, 0, Qt.AlignmentFlag.AlignCenter)

        # Colonne droite : informations, liens avec icône, puis boutons en bas à droite.
        right_column = QVBoxLayout()
        information = QLabel(
            f"<h3 style='margin:0'>{APP_NAME}</h3>"
            f"{tr('Version')} {APP_VERSION}<br>"
            f"{tr('Licence :')} {APP_LICENSE}"
        )
        information.setObjectName("about_information")
        information.setTextFormat(Qt.TextFormat.RichText)
        information.setWordWrap(True)
        information.setMinimumWidth(340)
        right_column.addWidget(information)

        # Les liens prennent la couleur d'accent du thème pour rester lisibles sur fond sombre.
        link_style = f"style=\"color:{self._icon_color.name()}\""
        links = QGridLayout()
        links.setHorizontalSpacing(8)
        links.setVerticalSpacing(6)
        entries = (
            ("source", tr("Accéder au dépôt du code source"), APP_SOURCE, APP_SOURCE),
            ("mail", "Arnauld BIGANZOLI", f"mailto:{APP_CONTACT_EMAIL}", APP_CONTACT_EMAIL),
            ("web", tr("Plateau Technique Mécatronique"), APP_LAB_URL, APP_LAB_URL),
            ("ut", tr("Université de Toulouse"), APP_UT_URL, APP_UT_URL),
        )
        for row, (key, text, url, tooltip) in enumerate(entries):
            # L'icône et le texte sont cliquables et affichent l'adresse au survol.
            icon_button = QToolButton()
            icon_button.setObjectName(f"about_icon_{key}")
            icon_button.setAutoRaise(True)
            icon_button.setIcon(self._about_link_icon(key))
            icon_button.setIconSize(QSize(20, 20))
            icon_button.setToolTip(tooltip)
            icon_button.setCursor(Qt.CursorShape.PointingHandCursor)
            icon_button.clicked.connect(lambda _checked, target=url: self._open_about_link(target))
            link_label = QLabel(f"<a {link_style} href=\"{url}\">{text}</a>")
            link_label.setObjectName(f"about_link_{key}")
            link_label.setTextFormat(Qt.TextFormat.RichText)
            link_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            link_label.setOpenExternalLinks(False)
            link_label.setToolTip(tooltip)
            link_label.linkActivated.connect(self._open_about_link)
            links.addWidget(icon_button, row, 0)
            links.addWidget(link_label, row, 1)
        links.setColumnStretch(1, 1)
        right_column.addLayout(links)
        organisation = QLabel("Centre de Biologie Intégrative (CBI) — CNRS FR3743")
        organisation.setObjectName("about_organisation")
        organisation.setWordWrap(True)
        right_column.addWidget(organisation)
        right_column.addStretch(1)

        close_row = QHBoxLayout()
        close_row.addStretch(1)
        copy_button = QPushButton(tr("Copier l'adresse e-mail"))
        copy_button.setObjectName("about_copy_email")
        copy_button.setToolTip(APP_CONTACT_EMAIL)
        copy_button.clicked.connect(self.copy_contact_email)
        close_row.addWidget(copy_button)
        close_button = QPushButton(tr("Fermer"))
        close_button.clicked.connect(dialog.accept)
        close_row.addWidget(close_button)
        right_column.addLayout(close_row)
        columns.addLayout(right_column, 1)
        return dialog

    def _about_link_icon(self, key: str) -> QIcon:
        """
        Description: Icon of one "À propos" link, tinted with the theme colour; a custom "logo_ut.svg/png" in the icons folder replaces the generic UT icon.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param key

        @returns
        """
        if key == "ut":
            for name in ("logo_ut.svg", "logo_ut.png"):
                custom = self.resource_paths["icons"] / name
                if custom.is_file():
                    return QIcon(str(custom))
        return tinted_svg_icon(self._icon_path(_ABOUT_LINK_ICON_FILES[key]), self._icon_color, size=20)

    def _open_about_link(self, url: str) -> bool:
        """
        Description: Open a link of the "À propos" window; when no mail program can open a "mailto:" link, explain it and offer to copy the address.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param url

        @returns
        """
        if QDesktopServices.openUrl(QUrl(url)):
            return True
        if url.startswith("mailto:"):
            self._build_mail_unavailable_box().exec()
        else:
            self.statusBar().showMessage(f"{tr('Impossible d’ouvrir le lien :')} {url}")
        return False

    def _build_mail_unavailable_box(self) -> QMessageBox:
        """
        Description: Message shown when no mail program is installed: the address cannot be opened directly, with a "Copier l'adresse" button left of "Fermer".

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        box = QMessageBox(self)
        box.setObjectName("mail_unavailable_box")
        box.setIcon(QMessageBox.Icon.Information)
        box.setWindowTitle(tr("Messagerie indisponible"))
        box.setText(
            f"{tr('Aucun programme de messagerie n’est installé sur cet ordinateur.')}<br><br>"
            f"{tr('L’adresse')} <b>{APP_CONTACT_EMAIL}</b> "
            f"{tr('ne peut pas être ouverte directement par l’application : copiez-la dans votre messagerie.')}"
        )
        copy_button = box.addButton(tr("Copier l'adresse"), QMessageBox.ButtonRole.ActionRole)
        copy_button.setObjectName("mail_copy_button")
        copy_button.clicked.connect(self.copy_contact_email)
        box.addButton(tr("Fermer"), QMessageBox.ButtonRole.RejectRole)
        return box

    def copy_contact_email(self) -> None:
        """
        Description: Copy the developer's e-mail address to the clipboard.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        QApplication.clipboard().setText(APP_CONTACT_EMAIL)
        self.statusBar().showMessage(f"{tr('Adresse e-mail copiée :')} {APP_CONTACT_EMAIL}")

    def show_about_dialog(self) -> None:
        """
        Description: Show the "À propos" dialog.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @returns
        """
        self._build_about_dialog().exec()

    def _build_option_docks(self) -> None:
        """
        Description: Build one independently dockable panel per option group (rotation, rognage, luminosité/contraste, loupe, export) so the user can freely float, resize, tabify or restack them however they like, instead of being stuck with a fixed right-hand column.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        # --- Rotation ---
        rotation_box = QGroupBox("Rotation")
        rotation_layout = QVBoxLayout(rotation_box)

        quick_row = QHBoxLayout()
        self.rotate_left_button = QPushButton("⟲ 90°")
        self.rotate_left_button.clicked.connect(lambda: self.apply_rotation(-90, absolute=False))
        self.rotate_right_button = QPushButton("⟳ 90°")
        self.rotate_right_button.clicked.connect(lambda: self.apply_rotation(90, absolute=False))
        quick_row.addWidget(self.rotate_left_button)
        quick_row.addWidget(self.rotate_right_button)
        rotation_layout.addLayout(quick_row)

        fine_row = QHBoxLayout()
        fine_row.addWidget(QLabel("Angle fin (°)"))
        self.angle_spin = QDoubleSpinBox()
        self.angle_spin.setRange(-45.0, 45.0)
        self.angle_spin.setSingleStep(0.1)
        self.angle_spin.setValue(0.0)
        self.angle_spin.valueChanged.connect(self.apply_fine_angle)
        fine_row.addWidget(self.angle_spin)
        rotation_layout.addLayout(fine_row)

        self.reset_rotation_button = QPushButton("Réinitialiser la rotation")
        self.reset_rotation_button.clicked.connect(lambda: self.apply_rotation(-self.angle_total, absolute=False))
        rotation_layout.addWidget(self.reset_rotation_button)

        self.grid_toggle_button = QPushButton("Afficher la grille d'alignement")
        self.grid_toggle_button.setCheckable(True)
        self.grid_toggle_button.toggled.connect(self.toggle_rotation_grid)
        self.toggle_rotation_grid(False)

        trapezoid_box = QGroupBox("Correction trapézoïdale")
        trapezoid_layout = QFormLayout(trapezoid_box)
        self.trapezoid_top_spin = QDoubleSpinBox()
        self.trapezoid_top_spin.setRange(-49.0, 49.0)
        self.trapezoid_top_spin.setSingleStep(1.0)
        self.trapezoid_top_spin.setSuffix(" %")
        self.trapezoid_top_spin.valueChanged.connect(self.apply_trapezoid_from_controls)
        trapezoid_layout.addRow("Bord supérieur", self.trapezoid_top_spin)

        self.trapezoid_bottom_spin = QDoubleSpinBox()
        self.trapezoid_bottom_spin.setRange(-49.0, 49.0)
        self.trapezoid_bottom_spin.setSingleStep(1.0)
        self.trapezoid_bottom_spin.setSuffix(" %")
        self.trapezoid_bottom_spin.valueChanged.connect(self.apply_trapezoid_from_controls)
        trapezoid_layout.addRow("Bord inférieur", self.trapezoid_bottom_spin)

        self.trapezoid_left_spin = QDoubleSpinBox()
        self.trapezoid_left_spin.setRange(-49.0, 49.0)
        self.trapezoid_left_spin.setSingleStep(1.0)
        self.trapezoid_left_spin.setSuffix(" %")
        self.trapezoid_left_spin.setToolTip("Rétrécit/élargit le bord gauche de l'image")
        self.trapezoid_left_spin.valueChanged.connect(self.apply_trapezoid_from_controls)
        trapezoid_layout.addRow("Bord gauche", self.trapezoid_left_spin)

        self.trapezoid_right_spin = QDoubleSpinBox()
        self.trapezoid_right_spin.setRange(-49.0, 49.0)
        self.trapezoid_right_spin.setSingleStep(1.0)
        self.trapezoid_right_spin.setSuffix(" %")
        self.trapezoid_right_spin.setToolTip("Rétrécit/élargit le bord droit de l'image")
        self.trapezoid_right_spin.valueChanged.connect(self.apply_trapezoid_from_controls)
        trapezoid_layout.addRow("Bord droit", self.trapezoid_right_spin)

        reset_trapezoid_button = QPushButton("Réinitialiser la correction")
        reset_trapezoid_button.clicked.connect(lambda: self.apply_trapezoid(0.0, 0.0, 0.0, 0.0, absolute=True))
        trapezoid_layout.addRow(reset_trapezoid_button)

        # --- Crop ---
        crop_box = QGroupBox("Rognage")
        crop_layout = QVBoxLayout(crop_box)
        crop_hint = QLabel("Utilisez « Rogner » pour dessiner une zone, puis « Déplacer » pour l'ajuster avant validation.")
        crop_hint.setWordWrap(True)
        crop_layout.addWidget(crop_hint)
        crop_buttons_row = QHBoxLayout()
        self.crop_apply_button = QPushButton("Appliquer le rognage")
        self.crop_apply_button.clicked.connect(self.apply_crop)
        self.crop_reset_button = QPushButton("Réinitialiser")
        self.crop_reset_button.clicked.connect(self.reset_crop)
        crop_buttons_row.addWidget(self.crop_apply_button)
        crop_buttons_row.addWidget(self.crop_reset_button)
        crop_layout.addLayout(crop_buttons_row)
        crop_layout.addStretch(1)

        # --- Brightness / contrast ---
        adjust_box = QGroupBox("Luminosité / Contraste")
        adjust_layout = QFormLayout(adjust_box)

        self.brightness_slider = QSlider(Qt.Orientation.Horizontal)
        self.brightness_slider.setRange(-100, 100)
        self.brightness_slider.setValue(0)
        self.brightness_slider.valueChanged.connect(self.apply_slider_adjustments)
        adjust_layout.addRow("Luminosité", self.brightness_slider)

        self.contrast_slider = QSlider(Qt.Orientation.Horizontal)
        self.contrast_slider.setRange(1, 300)
        self.contrast_slider.setValue(100)
        self.contrast_slider.valueChanged.connect(self.apply_slider_adjustments)
        adjust_layout.addRow("Contraste", self.contrast_slider)

        # --- Loupe ---
        loupe_box = QGroupBox("Loupe (calque de zoom)")
        loupe_layout = QFormLayout(loupe_box)
        loupe_buttons_row = QHBoxLayout()
        self.new_loupe_button = QPushButton("Nouvelle loupe")
        self.new_loupe_button.setToolTip(
            "Ajoute une loupe supplémentaire sur l'image (identifiant incrémenté automatiquement dans le JSON)"
        )
        self.new_loupe_button.setEnabled(False)
        self.new_loupe_button.clicked.connect(self.create_new_loupe)
        loupe_buttons_row.addWidget(self.new_loupe_button)
        self.loupe_enable_button = QPushButton("Activer la loupe")
        self.loupe_enable_button.setCheckable(True)
        self.loupe_enable_button.toggled.connect(self.toggle_loupe)
        loupe_buttons_row.addWidget(self.loupe_enable_button)
        loupe_layout.addRow(loupe_buttons_row)
        self.current_loupe_label = QLabel("Aucune loupe")
        self.current_loupe_label.setToolTip("Loupe dont les réglages sont affichés ci-dessous")
        loupe_layout.addRow("Loupe active", self.current_loupe_label)

        self.loupe_zoom_spin = QDoubleSpinBox()
        self.loupe_zoom_spin.setRange(1.0, 8.0)
        self.loupe_zoom_spin.setSingleStep(0.1)
        self.loupe_zoom_spin.setValue(2.0)
        self.loupe_zoom_spin.valueChanged.connect(self.update_loupe_zoom)
        loupe_layout.addRow("Zoom", self.loupe_zoom_spin)

        self.loupe_radius_spin = QSpinBox()
        self.loupe_radius_spin.setRange(20, 400)
        self.loupe_radius_spin.setValue(90)
        self.loupe_radius_spin.setSingleStep(10)  # ⑦ Rayon par pas de 10
        self.loupe_radius_spin.valueChanged.connect(self.update_loupe_radius)
        loupe_layout.addRow("Rayon", self.loupe_radius_spin)

        self.loupe_stroke_width_spin = QSpinBox()
        self.loupe_stroke_width_spin.setRange(1, 20)
        self.loupe_stroke_width_spin.setValue(4)
        self.loupe_stroke_width_spin.setSuffix(" px")
        self.loupe_stroke_width_spin.setToolTip("Épaisseur du contour circulaire de la loupe (indépendant de la flèche)")
        self.loupe_stroke_width_spin.valueChanged.connect(self.update_loupe_stroke_width)
        loupe_layout.addRow("Épaisseur du contour", self.loupe_stroke_width_spin)

        self.loupe_arrow_stroke_width_spin = QSpinBox()
        self.loupe_arrow_stroke_width_spin.setRange(1, 20)
        self.loupe_arrow_stroke_width_spin.setValue(2)
        self.loupe_arrow_stroke_width_spin.setSuffix(" px")
        self.loupe_arrow_stroke_width_spin.setToolTip("Épaisseur de la flèche de la loupe (indépendante du contour)")
        self.loupe_arrow_stroke_width_spin.valueChanged.connect(self.update_loupe_arrow_stroke_width)
        loupe_layout.addRow("Épaisseur de la flèche", self.loupe_arrow_stroke_width_spin)

        loupe_rotation_quick_row = QHBoxLayout()
        self.loupe_rotate_left_button = QPushButton("⟲ 90°")
        self.loupe_rotate_left_button.setToolTip("Fait pivoter le contenu agrandi de la loupe de 90° vers la gauche")
        self.loupe_rotate_left_button.clicked.connect(lambda: self.rotate_loupe(-90))
        self.loupe_rotate_right_button = QPushButton("⟳ 90°")
        self.loupe_rotate_right_button.setToolTip("Fait pivoter le contenu agrandi de la loupe de 90° vers la droite")
        self.loupe_rotate_right_button.clicked.connect(lambda: self.rotate_loupe(90))
        loupe_rotation_quick_row.addWidget(self.loupe_rotate_left_button)
        loupe_rotation_quick_row.addWidget(self.loupe_rotate_right_button)
        loupe_layout.addRow(loupe_rotation_quick_row)

        self.loupe_rotation_spin = QDoubleSpinBox()
        self.loupe_rotation_spin.setRange(-180.0, 180.0)
        self.loupe_rotation_spin.setSingleStep(1.0)
        self.loupe_rotation_spin.setSuffix(" °")
        self.loupe_rotation_spin.setToolTip("Rotation libre du contenu agrandi de la loupe")
        self.loupe_rotation_spin.valueChanged.connect(self.update_loupe_rotation)
        loupe_layout.addRow("Rotation", self.loupe_rotation_spin)

        loupe_palette_label = QLabel("Palette de couleur")
        loupe_palette_label.setStyleSheet("font-weight: bold;")
        loupe_layout.addRow(loupe_palette_label)
        loupe_layout.addRow(self._build_color_palette_widget())

        # --- Annotation ---
        annotation_box = QGroupBox("Annotation")
        annotation_layout = QVBoxLayout(annotation_box)
        annotation_layout.setSpacing(4)

        def add_annotation_separator() -> None:
            """
            Description:

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-20
            @version 1

            @returns
            """
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            annotation_layout.addWidget(line)

        shape_selector_row = QHBoxLayout()
        self.annotation_shape_buttons: dict[str, QToolButton] = {}
        for tool, label in (
            (TOOL_TEXT, "Étiquette"),
            (TOOL_RECT, "Rectangle"),
            (TOOL_CIRCLE, "Cercle"),
            (TOOL_LINE, "Ligne"),
        ):
            shape_button = QToolButton()
            shape_button.setText(label)
            shape_button.setCheckable(True)
            shape_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            shape_button.clicked.connect(lambda _checked, t=tool: self._select_annotation_shape(t))
            shape_selector_row.addWidget(shape_button)
            self.annotation_shape_buttons[tool] = shape_button
        annotation_layout.addLayout(shape_selector_row)

        self.line_arrow_start_checkbox = QCheckBox("Flèche au début")
        self.line_arrow_start_checkbox.setToolTip("Ligne uniquement : affiche une flèche au premier point tracé")
        self.line_arrow_start_checkbox.toggled.connect(self._on_line_arrow_start_changed)
        annotation_layout.addWidget(self.line_arrow_start_checkbox)

        self.line_arrow_end_checkbox = QCheckBox("Flèche à la fin")
        self.line_arrow_end_checkbox.setToolTip("Ligne uniquement : affiche une flèche au dernier point tracé")
        self.line_arrow_end_checkbox.toggled.connect(self._on_line_arrow_end_changed)
        annotation_layout.addWidget(self.line_arrow_end_checkbox)

        add_annotation_separator()

        shape_row = QHBoxLayout()
        shape_row.addWidget(QLabel("Forme :"))
        self.label_shape_combo = QComboBox()
        self.label_shape_combo.addItem("Rectangulaire", "rect")
        self.label_shape_combo.addItem("Ronde", "round")
        self.label_shape_combo.currentIndexChanged.connect(self._on_label_shape_changed)
        shape_row.addWidget(self.label_shape_combo)
        annotation_layout.addLayout(shape_row)

        stroke_row = QHBoxLayout()
        stroke_row.addWidget(QLabel("Épaisseur :"))
        self.stroke_width_spin = QSpinBox()
        self.stroke_width_spin.setRange(1, 20)
        self.stroke_width_spin.setValue(config.default_stroke_width)
        self.stroke_width_spin.setSuffix(" px")
        self.stroke_width_spin.valueChanged.connect(self._on_stroke_width_changed)
        stroke_row.addWidget(self.stroke_width_spin)
        annotation_layout.addLayout(stroke_row)

        radius_row = QHBoxLayout()
        radius_row.addWidget(QLabel("Rayon :"))
        self.border_radius_spin = QSpinBox()
        self.border_radius_spin.setRange(0, 200)
        self.border_radius_spin.setValue(0)
        self.border_radius_spin.setSuffix(" px")
        self.border_radius_spin.setToolTip("Arrondi des coins (0 = angles droits)")
        self.border_radius_spin.valueChanged.connect(self._on_border_radius_changed)
        radius_row.addWidget(self.border_radius_spin)
        annotation_layout.addLayout(radius_row)

        self.fill_enabled_checkbox = QCheckBox("Fond")
        self.fill_enabled_checkbox.setToolTip("Activer/désactiver la couleur de remplissage de la forme")
        self.fill_enabled_checkbox.setChecked(True)
        self.fill_enabled_checkbox.toggled.connect(self._on_fill_enabled_changed)
        annotation_layout.addWidget(self.fill_enabled_checkbox)

        add_annotation_separator()

        text_label = QLabel("Texte")
        text_label.setStyleSheet("font-weight: bold;")
        annotation_layout.addWidget(text_label)

        self.show_text_checkbox = QCheckBox("Afficher le texte")
        self.show_text_checkbox.setChecked(True)
        self.show_text_checkbox.toggled.connect(self._on_show_text_changed)
        annotation_layout.addWidget(self.show_text_checkbox)

        self.bold_text_checkbox = QCheckBox("Gras")
        self.bold_text_checkbox.setChecked(False)
        self.bold_text_checkbox.toggled.connect(self._on_bold_text_changed)
        annotation_layout.addWidget(self.bold_text_checkbox)

        add_annotation_separator()

        self.show_arrow_checkbox = QCheckBox("Afficher la flèche")
        self.show_arrow_checkbox.setChecked(True)
        self.show_arrow_checkbox.toggled.connect(self._on_show_arrow_changed)
        annotation_layout.addWidget(self.show_arrow_checkbox)

        arrow_stroke_row = QHBoxLayout()
        arrow_stroke_row.addWidget(QLabel("Épaisseur :"))
        self.arrow_stroke_width_spin = QSpinBox()
        self.arrow_stroke_width_spin.setRange(1, 20)
        self.arrow_stroke_width_spin.setValue(2)
        self.arrow_stroke_width_spin.setSuffix(" px")
        self.arrow_stroke_width_spin.valueChanged.connect(self._on_arrow_stroke_width_changed)
        arrow_stroke_row.addWidget(self.arrow_stroke_width_spin)
        annotation_layout.addLayout(arrow_stroke_row)

        add_annotation_separator()

        palette_label = QLabel("Palette de couleur")
        palette_label.setStyleSheet("font-weight: bold;")
        annotation_layout.addWidget(palette_label)
        annotation_layout.addWidget(self._build_color_palette_widget())

        add_annotation_separator()

        current_label = QLabel("Couleur actuelle :")
        current_label.setStyleSheet("font-weight: bold;")
        annotation_layout.addWidget(current_label)
        self.current_color_swatch = QLabel()
        self.current_color_swatch.setFixedHeight(28)
        self.current_color_swatch.setMinimumWidth(120)
        self.current_color_swatch.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        annotation_layout.addWidget(self.current_color_swatch)
        annotation_layout.addStretch(1)

        # --- Export ---
        export_box = QGroupBox("Export")
        export_layout = QFormLayout(export_box)
        self.width_spin = QSpinBox()
        self.width_spin.setRange(50, 20000)
        self.width_spin.setSingleStep(10)
        self.width_spin.setValue(1200)
        self.width_spin.valueChanged.connect(self._on_export_width_changed)
        self.width_spin.valueChanged.connect(self._sync_export_preset_buttons)
        export_layout.addRow("Largeur (px)", self.width_spin)

        presets_row = QHBoxLayout()
        self.export_preset_buttons: dict[int, QPushButton] = {}
        for preset in EXPORT_WIDTH_PRESETS:
            preset_button = QPushButton(f"{preset} px")
            preset_button.setCheckable(True)
            preset_button.setToolTip("Largeur d'export prédéfinie (la hauteur suit les proportions de l'image)")
            preset_button.clicked.connect(lambda _checked, width=preset: self.apply_export_width_preset(width))
            presets_row.addWidget(preset_button)
            self.export_preset_buttons[preset] = preset_button
        export_layout.addRow("Préréglages", presets_row)

        self.height_spin = QSpinBox()
        self.height_spin.setRange(50, 20000)
        self.height_spin.setSingleStep(10)
        self.height_spin.setValue(800)
        self.height_spin.valueChanged.connect(self._on_export_height_changed)
        export_layout.addRow("Hauteur (px)", self.height_spin)
        self.export_button = QPushButton("Exporter l'image annotée")
        self.export_button.clicked.connect(self.export_image)
        export_layout.addRow(self.export_button)
        self._sync_export_preset_buttons(self.width_spin.value())

        transformation_page = QWidget()
        transformation_layout = QVBoxLayout(transformation_page)

        def add_separator() -> None:
            """
            Description:

            @author ArnauldDev
            @created 2026-09-20
            @modified 2026-09-20
            @version 1

            @returns
            """
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setFrameShadow(QFrame.Shadow.Sunken)
            transformation_layout.addWidget(line)

        transformation_layout.addWidget(self.grid_toggle_button)
        add_separator()
        transformation_layout.addWidget(rotation_box)
        add_separator()
        transformation_layout.addWidget(trapezoid_box)
        add_separator()
        transformation_layout.addWidget(crop_box)
        transformation_layout.addStretch(1)

        self.option_pages = QStackedWidget()
        self.option_pages.addWidget(self._make_option_page("Déplacer", QLabel("Sélectionnez un outil dans la barre principale.")))
        self.option_pages.addWidget(self._make_option_page("Transformation", transformation_page))
        self.option_pages.addWidget(adjust_box)
        self.option_pages.addWidget(loupe_box)
        self.option_pages.addWidget(annotation_box)
        self.option_pages.addWidget(export_box)
        self.option_page_map = {
            TOOL_VIEW: 0,
            TOOL_ROTATE_LINE: 1,
            TOOL_CROP: 1,
            TOOL_LOUPE: 3,
            TOOL_TEXT: 4,
            TOOL_RECT: 4,
            TOOL_CIRCLE: 4,
            TOOL_LINE: 4,
            "adjustments": 2,
            "export": 5,
        }
        self.options_dock = QDockWidget("Options", self)
        self.options_dock.setObjectName("options_dock")
        self.options_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.options_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        self.options_dock.setWidget(self.option_pages)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.options_dock)
        self._set_current_color(QColor("yellow"))
        self._update_multi_loupe_visibility()
        # Boutons « + » / « − » explicites sur tous les champs numériques : plus
        # lisibles que de petites flèches et identiques quel que soit le thème.
        for spin in self.findChildren(QAbstractSpinBox):
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)

    def _make_option_page(self, title: str, content: QWidget) -> QWidget:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param title
        @param content

        @returns
        """
        page = QWidget()
        layout = QVBoxLayout(page)
        heading = QLabel(title)
        heading.setStyleSheet("font-weight: bold;")
        layout.addWidget(heading)
        layout.addWidget(content)
        layout.addStretch(1)
        return page

    def _make_option_dock(self, title: str, content: QWidget) -> QDockWidget:
        """
        Description: Wrap ``content`` in a movable/floatable/closable dock widget so it can be freely rearranged in any dock area or detached entirely.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param title
        @param content

        @returns
        """
        dock = QDockWidget(title, self)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
            | QDockWidget.DockWidgetFeature.DockWidgetClosable
        )
        dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        dock.setWidget(content)
        return dock

    def _build_central_layout(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        self.setCentralWidget(self.canvas)

    # ------------------------------------------------------------------
    # Historique des fichiers récents (③)
    # ------------------------------------------------------------------
    @staticmethod
    def _load_recent_files() -> list[str]:
        """
        Description: Charge la liste des fichiers récents depuis le fichier de configuration.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        try:
            if _RECENT_FILES_PATH.exists():
                data = json.loads(_RECENT_FILES_PATH.read_text(encoding="utf-8"))
                return [f for f in data if Path(f).exists()][:_MAX_RECENT_FILES]
        except Exception:
            pass
        return []

    def _save_recent_files(self) -> None:
        """
        Description: Persiste la liste des fichiers récents.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        try:
            _RECENT_FILES_PATH.parent.mkdir(parents=True, exist_ok=True)
            _RECENT_FILES_PATH.write_text(
                json.dumps(self._recent_files, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def _add_to_recent_files(self, path: Path) -> None:
        """
        Description: Ajoute un fichier en tête de la liste récente et persiste.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param path

        @returns
        """
        p = str(path.resolve())
        if p in self._recent_files:
            self._recent_files.remove(p)
        self._recent_files.insert(0, p)
        self._recent_files = self._recent_files[:_MAX_RECENT_FILES]
        self._save_recent_files()
        self._update_recent_files_menu()

    def _update_recent_files_menu(self) -> None:
        """
        Description: Reconstruit le sous-menu Fichiers récents.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if not hasattr(self, "recent_menu"):
            return
        self.recent_menu.clear()
        if not self._recent_files:
            no_action = QAction("(aucun fichier récent)", self)
            no_action.setEnabled(False)
            self.recent_menu.addAction(no_action)
        else:
            for path_str in self._recent_files:
                action = QAction(Path(path_str).name, self)
                action.setToolTip(path_str)
                action.triggered.connect(lambda _checked, p=path_str: self.load_source_image(p))
                self.recent_menu.addAction(action)
        self.recent_menu.addSeparator()
        clear_action = QAction("Effacer l'historique", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def _clear_recent_files(self) -> None:
        """
        Description: Vide la liste des fichiers récents.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        self._recent_files.clear()
        self._save_recent_files()
        self._update_recent_files_menu()
        self.statusBar().showMessage("Historique des fichiers récents effacé.")


    # ------------------------------------------------------------------
    # Image loading / preview management
    # ------------------------------------------------------------------
    def load_demo_image(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        image_path = Path("images/photo-carte-electronique-raw.jpg")
        if not image_path.exists():
            image_path = Path("images/raw/IMG_20260720_174638.jpg")
        if image_path.exists():
            self.load_source_image(image_path)

    def load_source_image(self, path: str | Path) -> None:
        """
        Description: Load the full-resolution source image and derive a fluid preview.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param path

        @returns
        """
        self.source_path = Path(path)
        self.current_json_path, self.default_export_path = compute_associated_paths(
            self.source_path, export_width=self.width_spin.value() if hasattr(self, "width_spin") else None
        )
        self.original_image = load_image(self.source_path)
        self.preview_image, self.preview_scale = make_preview(self.original_image)

        self.angle_total = 0.0
        self.trapezoid_top = 0.0
        self.trapezoid_bottom = 0.0
        self.trapezoid_left = 0.0
        self.trapezoid_right = 0.0
        self.brightness = 0
        self.contrast = 1.0
        self.crop_box = None
        self.canvas.crop_rect = None
        self.canvas.selected_item = None
        self.angle_spin.blockSignals(True)
        self.angle_spin.setValue(0.0)
        self.angle_spin.blockSignals(False)
        for spin in (self.trapezoid_top_spin, self.trapezoid_bottom_spin,
                     self.trapezoid_left_spin, self.trapezoid_right_spin):
            spin.blockSignals(True)
            spin.setValue(0.0)
            spin.blockSignals(False)
        self.brightness_slider.blockSignals(True)
        self.brightness_slider.setValue(0)
        self.brightness_slider.blockSignals(False)
        self.contrast_slider.blockSignals(True)
        self.contrast_slider.setValue(100)
        self.contrast_slider.blockSignals(False)

        self.canvas.annotations.clear()
        self.layer_order = []
        self.canvas.loupes = []
        self._sync_loupe_controls(None)

        self.canvas.set_preview_image(self.preview_image)
        self._sync_height_to_width()
        self._update_action_states()
        # A single path also serves file-dialog, recent-menu and programmatic
        # loads; de-duplication keeps the history stable.
        self._add_to_recent_files(self.source_path)

        # Si le fichier JSON associé existe déjà, charger automatiquement les traitements
        if self.current_json_path.exists():
            try:
                recipe = ProcessingRecipe.load(self.current_json_path)
                self.apply_recipe_to_ui(recipe)
                self.refresh_objects_list()
                self._reset_history()
                self.statusBar().showMessage(
                    f"Image chargée : {self.source_path.name} | Recette associée trouvée et appliquée : {self.current_json_path.name}"
                )
            except Exception as err:
                self.statusBar().showMessage(
                    f"Image chargée : {self.source_path.name} | Erreur lors du chargement de {self.current_json_path.name}: {err}"
                )
        else:
            self.refresh_objects_list()
            self._reset_history()
            self.statusBar().showMessage(
                f"Image chargée : {self.source_path.name} "
                f"({self.original_image.width}×{self.original_image.height} px, "
                f"aperçu {self.preview_image.width}×{self.preview_image.height} px) | "
                f"Fichier JSON prévu : {self.current_json_path.name}"
            )

    def refresh_preview(self) -> None:
        """
        Description: Recompute the preview pixmap after brightness/contrast/rotation changes.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        if self.preview_image is None:
            return
        self.canvas.update_pixmap()
        self.canvas.update()

    # ------------------------------------------------------------------
    # Tool selection
    # ------------------------------------------------------------------
    def select_tool(self, tool: str, select_default_loupe: bool = True) -> None:
        """
        Description: Activate ``tool``: update the tool bar, the graphical palette and the options panel. Activating the loupe tool selects the front-most loupe unless ``select_default_loupe`` is False.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 4

        @param tool
        @param select_default_loupe

        @returns
        """
        self.canvas.tool = tool
        self.export_action.setChecked(False)
        self._sync_tool_action_states(tool)
        if tool in ANNOTATION_FAMILY_TOOLS:
            self._update_annotation_options_for_kind(
                {TOOL_TEXT: "label", TOOL_RECT: "rect", TOOL_CIRCLE: "circle", TOOL_LINE: "line"}[tool]
            )
        self.canvas.reference_points.clear()
        # Mise à jour des boutons de la toolbar principale : chaque bouton
        # représente une famille d'outils (Annotation = formes, Transformation = rognage).
        family = TOOL_TEXT if tool in ANNOTATION_FAMILY_TOOLS else tool
        family = TOOL_ROTATE_LINE if family == TOOL_CROP else family
        if hasattr(self, "toolbar_tool_buttons"):
            for name, button in self.toolbar_tool_buttons.items():
                button.setChecked(name == family)
        if hasattr(self, "annotation_shape_buttons") and tool in ANNOTATION_FAMILY_TOOLS:
            for name, button in self.annotation_shape_buttons.items():
                button.setChecked(name == tool)
        if tool == TOOL_LOUPE:
            loupe = self.canvas.active_loupe()
            if select_default_loupe and loupe is not None:
                # La loupe la plus haute de la pile est sélectionnée par défaut
                # à l'activation de l'outil.
                self.canvas.selected_item = loupe
                if hasattr(self, "objects_list"):
                    self._select_payload_in_list(loupe)
                self.canvas.update()
            self._sync_loupe_controls(loupe)
            if loupe is not None:
                self._set_current_color(loupe.color, apply_to_selection=False)
        self._show_tool_options(tool)
        _, hint = TOOL_DESCRIPTIONS.get(tool, ("", ""))
        self.statusBar().showMessage(tr(hint))

    def _on_toolbar_tool_clicked(self, tool: str) -> None:
        """
        Description: Tâche 2 & 3 : clic sur un bouton outil de la toolbar. Active l'outil et affiche le dock d'options correspondant tout en masquant les autres. Si l'outil est déjà actif (re-clic), on revient à l'état initial (TOOL_VIEW).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param tool

        @returns
        """
        if self.canvas.tool == tool and tool != TOOL_VIEW:
            # Re-clic sur l'outil actif → retour à l'état initial
            self._reset_to_initial_state()
            return

        self.select_tool(tool)
        self._show_tool_options(tool)

    def show_export_options(self) -> None:
        """
        Description: Display export controls without opening a file dialog yet.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        # Export is a mode of the panel, not a drawing tool: leaving another
        # tool first prevents its toolbar button from remaining highlighted.
        self.select_tool(TOOL_VIEW)
        self.export_action.setChecked(True)
        self._sync_tool_action_states("export")
        self.option_pages.setCurrentIndex(self.option_page_map["export"])
        self.options_dock.show()
        self.options_dock.raise_()

    def _show_tool_options(self, tool: str) -> None:
        """
        Description: Select the properties page for the active tool.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param tool

        @returns
        """
        page_index = self.option_page_map.get(tool, self.option_page_map[TOOL_VIEW])
        self.option_pages.setCurrentIndex(page_index)
        self.options_dock.show()
        self.options_dock.raise_()

    def _reset_to_initial_state(self) -> None:
        """
        Description: Tâche 1 & 4 : remet l'interface dans son état initial. - Sélectionne l'outil "Déplacer" (TOOL_VIEW). - Masque tous les docks d'options de droite.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        self.select_tool(TOOL_VIEW)
        self._show_tool_options(TOOL_VIEW)
        # Désélectionne également l'objet courant (Échap doit tout réinitialiser).
        self.canvas.selected_item = None
        if hasattr(self, "objects_list"):
            self.objects_list.blockSignals(True)
            self.objects_list.clearSelection()
            self.objects_list.blockSignals(False)
            self.delete_object_button.setEnabled(False)
        self.canvas.update()

    def toggle_rotation_grid(self, checked: bool) -> None:
        """
        Description: Show/hide the alignment grid; the button's active colour comes from the theme (QPushButton:checked).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 2

        @param checked

        @returns
        """
        self.canvas.show_rotation_grid = checked
        if hasattr(self, "grid_toggle_button"):
            self.grid_toggle_button.setText(
                tr("Masquer la grille d'alignement") if checked else tr("Afficher la grille d'alignement")
            )
            self.grid_toggle_button.setToolTip(tr("Maintenez Ctrl pendant un tracé ou un déplacement pour vous accrocher à la grille."))
        self.canvas.update()

    # ------------------------------------------------------------------
    # Rotation / brightness / contrast (operate on the preview only)
    # ------------------------------------------------------------------
    def apply_rotation(self, angle: float, *, absolute: bool) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param angle
        @param absolute

        @returns
        """
        if self.preview_image is None:
            return
        self.angle_total = angle if absolute else self.angle_total + angle
        self._clear_crop_after_rotation_change()
        self.angle_spin.blockSignals(True)
        self.angle_spin.setValue(self.angle_total)
        self.angle_spin.blockSignals(False)
        self._rebuild_preview_from_original()
        self.refresh_objects_list()
        self.auto_save_recipe()

    def apply_fine_angle(self, value: float) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param value

        @returns
        """
        if self.preview_image is None:
            return
        self.angle_total = value
        self._clear_crop_after_rotation_change()
        self._rebuild_preview_from_original()
        self.refresh_objects_list()
        self.auto_save_recipe()

    def apply_trapezoid_from_controls(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        self.apply_trapezoid(
            self.trapezoid_top_spin.value() / 100.0,
            self.trapezoid_bottom_spin.value() / 100.0,
            self.trapezoid_left_spin.value() / 100.0,
            self.trapezoid_right_spin.value() / 100.0,
            absolute=True,
        )

    def apply_trapezoid(
        self,
        top_inset: float,
        bottom_inset: float,
        left_inset: float = 0.0,
        right_inset: float = 0.0,
        *,
        absolute: bool,
    ) -> None:
        """
        Description: ⑤ Correction trapézoïdale 4 côtés.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param top_inset
        @param bottom_inset
        @param left_inset
        @param right_inset
        @param absolute

        @returns
        """
        if self.preview_image is None:
            return
        if absolute:
            self.trapezoid_top = top_inset
            self.trapezoid_bottom = bottom_inset
            self.trapezoid_left = left_inset
            self.trapezoid_right = right_inset
        else:
            self.trapezoid_top += top_inset
            self.trapezoid_bottom += bottom_inset
            self.trapezoid_left += left_inset
            self.trapezoid_right += right_inset
        for spin, value in [
            (self.trapezoid_top_spin, self.trapezoid_top),
            (self.trapezoid_bottom_spin, self.trapezoid_bottom),
            (self.trapezoid_left_spin, self.trapezoid_left),
            (self.trapezoid_right_spin, self.trapezoid_right),
        ]:
            spin.blockSignals(True)
            spin.setValue(value * 100.0)
            spin.blockSignals(False)
        self._rebuild_preview_from_original()
        self.refresh_objects_list()
        self.auto_save_recipe()

    def _clear_crop_after_rotation_change(self) -> None:
        """
        Description: Drop any crop when the rotation changes, since it was defined against the previous rotated image bounds and would no longer line up correctly.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.crop_box is not None:
            self.crop_box = None
            self.canvas.crop_rect = None
            self.statusBar().showMessage("Le rognage a été réinitialisé suite au changement de rotation.")

    def apply_slider_adjustments(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.preview_image is None:
            return
        self.brightness = self.brightness_slider.value()
        self.contrast = self.contrast_slider.value() / 100.0
        self._rebuild_preview_from_original()
        self.refresh_objects_list()
        self.auto_save_recipe()

    def _rebuild_preview_from_original(self) -> None:
        """
        Description: Recompute the preview from the low-res base each time, so rotation/brightness/contrast never compound rounding errors and stay perfectly reversible while the user experiments.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.original_image is None:
            return
        base_preview, _ = make_preview(self.original_image)
        preview = rotate_image(base_preview, self.angle_total) if self.angle_total else base_preview
        if any(
            value
            for value in (
                self.trapezoid_top,
                self.trapezoid_bottom,
                self.trapezoid_left,
                self.trapezoid_right,
            )
        ):
            preview = apply_trapezoid_correction(
                preview,
                self.trapezoid_top,
                self.trapezoid_bottom,
                self.trapezoid_left,
                self.trapezoid_right,
            )
        if self.crop_box is not None and self.preview_scale:
            x1, y1, x2, y2 = (value / self.preview_scale for value in self.crop_box)
            left, top = max(0, int(round(x1))), max(0, int(round(y1)))
            right = min(preview.width, max(left + 1, int(round(x2))))
            bottom = min(preview.height, max(top + 1, int(round(y2))))
            preview = preview.crop((left, top, right, bottom))
        preview = apply_brightness_contrast(preview, brightness=self.brightness, contrast=self.contrast)
        self.preview_image = preview
        self.canvas.set_preview_image(self.preview_image)
        self._sync_height_to_width()

    # ------------------------------------------------------------------
    # Crop controls
    # ------------------------------------------------------------------
    def apply_crop(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        rect = self.canvas.crop_rect
        if rect is None or self.preview_image is None:
            return
        rect = rect.normalized()
        rect = rect.intersected(QRectF(0, 0, self.preview_image.width, self.preview_image.height))
        if rect.width() < 5 or rect.height() < 5:
            self.statusBar().showMessage("Zone de rognage trop petite, ignorée.")
            return

        scale = self.preview_scale or 1.0
        new_x1, new_y1 = rect.left() * scale, rect.top() * scale
        new_x2, new_y2 = rect.right() * scale, rect.bottom() * scale
        if self.crop_box is not None:
            base_x1, base_y1, _, _ = self.crop_box
            new_x1, new_x2 = new_x1 + base_x1, new_x2 + base_x1
            new_y1, new_y2 = new_y1 + base_y1, new_y2 + base_y1
        self.crop_box = (new_x1, new_y1, new_x2, new_y2)

        offset = rect.topLeft()
        kept: list[AnnotationItem] = []
        kept_tokens: set[str] = set()
        for item in self.canvas.annotations:
            if item.start is not None:
                item.start = item.start - offset
            if item.end is not None:
                item.end = item.end - offset
            reference = item.start if item.start is not None else item.end
            if reference is not None and 0 <= reference.x() <= rect.width() and 0 <= reference.y() <= rect.height():
                kept.append(item)
                kept_tokens.add(item.layer_token)
        self.canvas.annotations = kept
        # Les annotations hors cadre disparaissent : leur id ne change jamais,
        # donc il suffit de retirer leur jeton de l'ordre des calques (les
        # ids des annotations restantes restent valides, sans renumérotation).
        self.layer_order = [
            token for token in self.layer_order
            if not token.startswith("annotation:") or token in kept_tokens
        ]

        for loupe in self.canvas.loupes:
            loupe.center = loupe.center - offset
            loupe.arrow = (loupe.arrow[0] - offset, loupe.arrow[1] - offset)

        self.canvas.crop_rect = None
        self._rebuild_preview_from_original()
        self.statusBar().showMessage("Rognage appliqué.")
        self.refresh_objects_list()
        self.auto_save_recipe()

    def reset_crop(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.canvas.crop_rect is None and self.crop_box is None:
            return
        self.canvas.crop_rect = None
        self.crop_box = None
        self._rebuild_preview_from_original()
        self.statusBar().showMessage("Rognage réinitialisé.")
        self.refresh_objects_list()
        self.auto_save_recipe()

    # ------------------------------------------------------------------
    # Export size controls
    # ------------------------------------------------------------------
    def _sync_height_to_width(self) -> None:
        """
        Description: Keep the export height proportional to the export width whenever the working image (rotation/crop) changes, so the export always matches the image's own aspect ratio.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.preview_image is None or self.preview_image.width == 0:
            return
        self._sync_export_size_guard = True
        ratio = self.preview_image.height / self.preview_image.width
        target = round(self.width_spin.value() * ratio)
        target = max(self.height_spin.minimum(), min(self.height_spin.maximum(), target))
        self.height_spin.blockSignals(True)
        self.height_spin.setValue(target)
        self.height_spin.blockSignals(False)
        self._sync_export_size_guard = False

    def apply_export_width_preset(self, width: int) -> None:
        """
        Description: Apply one of the export width presets (800, 1200, 1920 px); the height follows the image ratio.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param width

        @returns
        """
        self.width_spin.setValue(width)
        self._sync_export_preset_buttons(self.width_spin.value())
        self.statusBar().showMessage(tr("Largeur d'export :") + f" {width} px")

    def _sync_export_preset_buttons(self, value: int) -> None:
        """
        Description: Highlight the preset button matching the current export width.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param value

        @returns
        """
        for preset, button in getattr(self, "export_preset_buttons", {}).items():
            button.setChecked(preset == value)

    def _on_export_width_changed(self, value: int) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @param value

        @returns
        """
        if self._sync_export_size_guard or self.preview_image is None or self.preview_image.width == 0:
            return
        self._sync_export_size_guard = True
        ratio = self.preview_image.height / self.preview_image.width
        target = max(self.height_spin.minimum(), min(self.height_spin.maximum(), round(value * ratio)))
        self.height_spin.setValue(target)
        self._sync_export_size_guard = False

        if self.source_path is not None:
            _, self.default_export_path = compute_associated_paths(self.source_path, export_width=value)
            self.auto_save_recipe(force=True)

    def _on_export_height_changed(self, value: int) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param value

        @returns
        """
        if self._sync_export_size_guard or self.preview_image is None or self.preview_image.height == 0:
            return
        self._sync_export_size_guard = True
        ratio = self.preview_image.width / self.preview_image.height
        target = max(self.width_spin.minimum(), min(self.width_spin.maximum(), round(value * ratio)))
        self.width_spin.setValue(target)
        self._sync_export_size_guard = False
        if self.source_path is not None:
            self.auto_save_recipe(force=True)

    # ------------------------------------------------------------------
    # Loupe controls
    # ------------------------------------------------------------------
    def current_loupe(self) -> LoupeOverlay | None:
        """
        Description: Loupe driven by the options panel: the selected loupe, otherwise the front-most one.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        return self.canvas.active_loupe()

    def _sync_loupe_controls(self, loupe: LoupeOverlay | None = None) -> None:
        """
        Description: Show the values of ``loupe`` (preview space) in the loupe panel without triggering the update slots.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param loupe

        @returns
        """
        loupe = loupe if loupe is not None else self.current_loupe()
        if not hasattr(self, "loupe_zoom_spin"):
            return
        self.current_loupe_label.setText(f"{tr('Loupe')} #{loupe.id}" if loupe is not None else tr("Aucune loupe"))
        if loupe is None:
            self.loupe_enable_button.blockSignals(True)
            self.loupe_enable_button.setChecked(False)
            self.loupe_enable_button.setText(tr("Activer la loupe"))
            self.loupe_enable_button.blockSignals(False)
            return
        for spin, value in (
            (self.loupe_zoom_spin, loupe.zoom),
            (self.loupe_radius_spin, loupe.radius),
            (self.loupe_rotation_spin, loupe.rotation),
            (self.loupe_stroke_width_spin, loupe.stroke_width),
            (self.loupe_arrow_stroke_width_spin, loupe.arrow_stroke_width),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)
        self.loupe_enable_button.blockSignals(True)
        self.loupe_enable_button.setChecked(loupe.enabled)
        self.loupe_enable_button.setText(tr("Masquer la loupe") if loupe.enabled else tr("Activer la loupe"))
        self.loupe_enable_button.blockSignals(False)

    def _update_multi_loupe_visibility(self) -> None:
        """
        Description: Show the "Nouvelle loupe" button only when the FEATURE_MULTI_LOUPE flag is enabled.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if hasattr(self, "new_loupe_button"):
            self.new_loupe_button.setVisible(config.feature_multi_loupe)

    def _select_payload_in_list(self, payload: object) -> None:
        """
        Description: Select ``payload`` in the objects list without re-emitting the selection signal.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param payload

        @returns
        """
        self.objects_list.blockSignals(True)
        for index in range(self.objects_list.count()):
            list_item = self.objects_list.item(index)
            matches = list_item.data(Qt.ItemDataRole.UserRole) is payload
            if matches:
                self.objects_list.setCurrentItem(list_item, QItemSelectionModel.SelectionFlag.NoUpdate)
            list_item.setSelected(matches)
        self.objects_list.blockSignals(False)
        self.delete_object_button.setEnabled(bool(self.objects_list.selectedItems()))

    def create_new_loupe(self) -> LoupeOverlay | None:
        """
        Description: Add a new loupe with the next identifier, offset from the existing ones and pointing at the image centre.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        if self.preview_image is None:
            return None
        if self.canvas.loupes and not config.feature_multi_loupe:
            self.statusBar().showMessage("Plusieurs loupes : fonctionnalité désactivée (FEATURE_MULTI_LOUPE=false).")
            return None
        width, height = self.preview_image.width, self.preview_image.height
        slot = len(self.canvas.loupes) % 4
        center = QPointF(width * (0.2 + 0.2 * slot), height * 0.25)
        target = QPointF(width * 0.5, height * 0.6)
        is_first = not self.canvas.loupes
        loupe = self.canvas.add_loupe(center, target)
        if is_first:
            # Sans loupe modèle, adapter le rayon par défaut aux petites images.
            loupe.radius = min(loupe.radius, max(20, int(min(width, height) / 6)))
        self.canvas.selected_item = loupe
        if self.canvas.tool != TOOL_LOUPE:
            self.select_tool(TOOL_LOUPE, select_default_loupe=False)
        self.refresh_objects_list()
        self._select_payload_in_list(loupe)
        self._sync_loupe_controls(loupe)
        self._set_current_color(loupe.color, apply_to_selection=False)
        self.canvas.update()
        self.auto_save_recipe(force=True)
        self.statusBar().showMessage(
            f"Loupe #{loupe.id} ajoutée : glissez son disque pour la placer et son extrémité de flèche vers la zone à agrandir."
        )
        return loupe

    def _after_loupe_change(self, force_save: bool = True) -> None:
        """
        Description: Repaint, refresh the objects list and save the JSON after a loupe setting changed.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param force_save

        @returns
        """
        self.canvas.update()
        self.refresh_objects_list()
        self.auto_save_recipe(force=force_save)

    def toggle_loupe(self, checked: bool) -> None:
        """
        Description: Show/hide the current loupe (its layer position is kept); creates a first loupe when none exists.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param checked

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            if checked:
                self.create_new_loupe()
            self._sync_loupe_controls()
            return
        loupe.enabled = checked
        self.loupe_enable_button.setText(tr("Masquer la loupe") if checked else tr("Activer la loupe"))
        if checked:
            self.canvas.selected_item = loupe
            if self.canvas.tool != TOOL_LOUPE:
                self.select_tool(TOOL_LOUPE, select_default_loupe=False)
        elif self.canvas.selected_item is loupe:
            # Une loupe masquée reste la loupe courante du panneau pour pouvoir
            # la réafficher, mais elle n'est plus mise en évidence sur l'image.
            self.canvas.selected_item = loupe
        self._after_loupe_change()

    def update_loupe_zoom(self, value: float) -> None:
        """
        Description: Magnification factor of the current loupe.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param value

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            return
        loupe.zoom = value
        self._after_loupe_change()

    def update_loupe_radius(self, value: int) -> None:
        """
        Description: Radius (preview pixels) of the current loupe.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param value

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            return
        loupe.radius = value
        self._after_loupe_change()

    def rotate_loupe(self, delta: float) -> None:
        """
        Description: Rotate the magnified content of the current loupe by ``delta`` degrees.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param delta

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            return
        rotation = (loupe.rotation + delta + 180) % 360 - 180
        self.loupe_rotation_spin.setValue(rotation)

    def update_loupe_rotation(self, value: float) -> None:
        """
        Description: Free rotation of the magnified content of the current loupe.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param value

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            return
        loupe.rotation = value
        self._after_loupe_change()

    def update_loupe_stroke_width(self, value: int) -> None:
        """
        Description: Thickness of the current loupe's outline ring (independent of the arrow), saved live in the JSON.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param value

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            return
        loupe.stroke_width = value
        self._after_loupe_change()

    def update_loupe_arrow_stroke_width(self, value: int) -> None:
        """
        Description: Thickness of the current loupe's arrow (independent of the ring outline), saved live in the JSON.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @param value

        @returns
        """
        loupe = self.current_loupe()
        if loupe is None:
            return
        loupe.arrow_stroke_width = value
        self._after_loupe_change()

    # ------------------------------------------------------------------
    # File dialogs
    # ------------------------------------------------------------------
    def open_image(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-21
        @version 2

        @returns
        """
        initial_dir = str(self.source_path.parent) if self.source_path else ("images" if Path("images").exists() else ".")
        file_name, _ = QFileDialog.getOpenFileName(
            self, tr("Ouvrir une image"), initial_dir, "Images (" + " ".join(f"*{suffix}" for suffix in IMAGE_FILE_SUFFIXES) + ")"
        )
        if not file_name:
            return
        self.load_source_image(file_name)
        # ③ Mémoriser dans l'historique des fichiers récents après chargement réussi
        self._add_to_recent_files(Path(file_name))

    def export_image(self) -> None:
        """
        Description: Ask for the destination and export the annotated image. Overwriting an existing file is confirmed only once, by the save dialog itself; the notification window can be disabled from the "Configuration" menu (the status bar message is always shown).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-23
        @version 3

        @returns
        """
        if self.original_image is None or self.source_path is None:
            return

        default_dest = self.default_export_path or (self.source_path.parent / self._suggest_export_name())
        # La boîte de dialogue d'enregistrement (native ou Qt) demande déjà
        # confirmation avant d'écraser un fichier existant : aucun second message.
        file_name, _ = QFileDialog.getSaveFileName(
            self, tr("Exporter l'image"), str(default_dest), "JPEG (*.jpg *.jpeg)"
        )
        if not file_name:
            return

        recipe = self.build_recipe()
        output_path = process_image_with_recipe(recipe, file_name)
        if self.current_json_path is not None:
            # Garde le fichier JSON des traitements synchronisé avec l'export réalisé.
            recipe.save(self.current_json_path)
        if self.export_notification_enabled():
            QMessageBox.information(self, tr("Export terminé"), f"{tr('Image enregistrée dans')} {output_path}")
        self.statusBar().showMessage(f"{tr('Exporté vers')} {output_path}")

    def export_notification_enabled(self) -> bool:
        """
        Description: Whether the notification window is shown after an export (enabled by default).

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @returns
        """
        return str(self._settings.value("export_notification", "true")).lower() in ("true", "1")

    def set_export_notification_enabled(self, enabled: bool) -> None:
        """
        Description: Enable/disable the notification window after an export and remember the choice.

        @author ArnauldDev
        @created 2026-09-23
        @modified 2026-09-23
        @version 1

        @param enabled

        @returns
        """
        self._settings.setValue("export_notification", "true" if enabled else "false")
        if hasattr(self, "export_notification_action") and self.export_notification_action.isChecked() != enabled:
            self.export_notification_action.setChecked(enabled)
        self.statusBar().showMessage(
            tr("Notification après l'export activée.") if enabled else tr("Notification après l'export désactivée.")
        )

    def _suggest_export_name(self) -> str:
        """
        Description: Propose an export name following nom-de-l-image-iat[-xWIDTH].jpg convention.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.default_export_path:
            return self.default_export_path.name
        stem = self.source_path.stem if self.source_path else "export"
        width = self.width_spin.value() if hasattr(self, "width_spin") else None
        suffix = f"-x{int(width)}" if width and int(width) > 0 else ""
        return f"{stem}-iat{suffix}.jpg"

    def save_recipe(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        if self.original_image is None:
            return
        default_dest = self.current_json_path or Path("recipe.json")
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Enregistrer la recette", str(default_dest), "JSON (*.json)"
        )
        if not file_name:
            return
        self.current_json_path = Path(file_name)
        recipe = self.build_recipe()
        path = recipe.save(file_name)
        self.statusBar().showMessage(f"Recette enregistrée : {path}")

    def load_recipe(self) -> None:
        """
        Description:

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 1

        @returns
        """
        default_dir = str(self.source_path.parent) if self.source_path else "images"
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Charger une recette", default_dir, "JSON (*.json)"
        )
        if not file_name:
            return
        recipe = ProcessingRecipe.load(file_name)
        self.current_json_path = Path(file_name)
        if recipe.source_image:
            self.load_source_image(recipe.source_image)
        self.apply_recipe_to_ui(recipe)
        self._reset_history()
        self.statusBar().showMessage(f"Recette chargée : {file_name}")

    # ------------------------------------------------------------------
    # Recipe (JSON) <-> UI state conversion
    # ------------------------------------------------------------------
    def build_recipe(self) -> ProcessingRecipe:
        """
        Description: Translate the current preview-space edits into a full-resolution :class:`ProcessingRecipe`, ready to be replayed or serialized.

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @returns
        """
        scale = self.preview_scale

        annotations = [
            Annotation(
                id=item.id,
                type=item.kind,
                x1=(item.start.x() if item.start else 0.0) * scale,
                y1=(item.start.y() if item.start else 0.0) * scale,
                x2=(item.end.x() if item.end else 0.0) * scale,
                y2=(item.end.y() if item.end else 0.0) * scale,
                text=item.text,
                color=item.color.name(),
                stroke_width=max(1, round(item.stroke_width * scale)),
                font_size=max(6, round(28 * scale)),
                border_radius=max(0, round(item.border_radius * scale)),
                show_arrow=item.show_arrow,
                shape=item.shape,
                arrow_stroke_width=max(1, round(item.arrow_stroke_width * scale)),
                show_text=item.show_text,
                fill_enabled=item.fill_enabled,
                bold_text=item.bold_text,
                line_arrow_start=item.line_arrow_start,
                line_arrow_end=item.line_arrow_end,
            )
            for item in self.canvas.annotations
        ]

        # Les épaisseurs sont converties comme les coordonnées : la valeur
        # affichée dans le panneau (espace aperçu) est retrouvée au rechargement.
        loupe_specs = [
            LoupeSpec(
                id=loupe.id,
                enabled=loupe.enabled,
                center_x=loupe.center.x() * scale,
                center_y=loupe.center.y() * scale,
                radius=loupe.radius * scale,
                zoom=loupe.zoom,
                arrow_start_x=loupe.arrow[0].x() * scale,
                arrow_start_y=loupe.arrow[0].y() * scale,
                arrow_end_x=loupe.arrow[1].x() * scale,
                arrow_end_y=loupe.arrow[1].y() * scale,
                color=loupe.color.name(),
                stroke_width=max(1, round(loupe.stroke_width * scale)),
                rotation=loupe.rotation,
                arrow_stroke_width=max(1, round(loupe.arrow_stroke_width * scale)),
            )
            for loupe in self.canvas.loupes
        ]

        layer_order = list(self.layer_order) or self.canvas.effective_layer_order()

        return ProcessingRecipe(
            source_image=str(self.source_path) if self.source_path else "",
            angle=self.angle_total,
            brightness=self.brightness,
            contrast=self.contrast,
            trapezoid=(
                self.trapezoid_top,
                self.trapezoid_bottom,
                self.trapezoid_left,
                self.trapezoid_right,
            ),
            crop=self.crop_box,
            export_width=self.width_spin.value(),
            export_height=self.height_spin.value(),
            stroke_width=self.canvas.current_stroke_width,
            annotations=annotations,
            loupes=loupe_specs,
            custom_colors=self._custom_colors(),
            layer_order=layer_order,
        )

    def apply_recipe_to_ui(self, recipe: ProcessingRecipe) -> None:
        """
        Description: Populate widgets/canvas state from a loaded recipe (preview space).

        @author ArnauldDev
        @created 2026-09-20
        @modified 2026-09-20
        @version 2

        @param recipe

        @returns
        """
        scale = self.preview_scale or 1.0
        if recipe.custom_colors:
            self._persist_custom_colors(recipe.custom_colors)
            self._refresh_color_palettes()

        self.angle_total = recipe.angle
        self.angle_spin.blockSignals(True)
        self.angle_spin.setValue(recipe.angle)
        self.angle_spin.blockSignals(False)

        self.brightness = recipe.brightness
        self.brightness_slider.blockSignals(True)
        self.brightness_slider.setValue(int(recipe.brightness))
        self.brightness_slider.blockSignals(False)

        self.contrast = recipe.contrast
        self.contrast_slider.blockSignals(True)
        self.contrast_slider.setValue(int(recipe.contrast * 100))
        self.contrast_slider.blockSignals(False)

        self.trapezoid_top = float(recipe.trapezoid[0])
        self.trapezoid_bottom = float(recipe.trapezoid[1])
        self.trapezoid_left = float(recipe.trapezoid[2]) if len(recipe.trapezoid) > 2 else 0.0
        self.trapezoid_right = float(recipe.trapezoid[3]) if len(recipe.trapezoid) > 3 else 0.0
        self.trapezoid_top_spin.blockSignals(True)
        self.trapezoid_top_spin.setValue(self.trapezoid_top * 100.0)
        self.trapezoid_top_spin.blockSignals(False)
        self.trapezoid_bottom_spin.blockSignals(True)
        self.trapezoid_bottom_spin.setValue(self.trapezoid_bottom * 100.0)
        self.trapezoid_bottom_spin.blockSignals(False)
        self.trapezoid_left_spin.blockSignals(True)
        self.trapezoid_left_spin.setValue(self.trapezoid_left * 100.0)
        self.trapezoid_left_spin.blockSignals(False)
        self.trapezoid_right_spin.blockSignals(True)
        self.trapezoid_right_spin.setValue(self.trapezoid_right * 100.0)
        self.trapezoid_right_spin.blockSignals(False)

        self.crop_box = recipe.crop
        self.canvas.crop_rect = None

        # blockSignals est indispensable ici : sans lui, setValue() déclenche
        # _on_export_width_changed/_on_export_height_changed, qui appellent
        # auto_save_recipe(force=True) -> build_recipe() alors que les
        # annotations/loupes/layer_order/stroke_width n'ont pas encore été
        # restaurés plus bas dans cette méthode. Le JSON qu'on vient de
        # charger était alors immédiatement réécrit avec un état partiel
        # (annotations/loupes/layer_order vidés, stroke_width remis au
        # défaut), perdant définitivement le reste de la recette.
        if recipe.export_width:
            self.width_spin.blockSignals(True)
            self.width_spin.setValue(int(recipe.export_width))
            self.width_spin.blockSignals(False)
            self._sync_export_preset_buttons(self.width_spin.value())
        if recipe.export_height:
            self.height_spin.blockSignals(True)
            self.height_spin.setValue(int(recipe.export_height))
            self.height_spin.blockSignals(False)

        # Épaisseur du trait
        self.canvas.current_stroke_width = recipe.stroke_width
        if hasattr(self, "stroke_width_spin"):
            self.stroke_width_spin.blockSignals(True)
            self.stroke_width_spin.setValue(recipe.stroke_width)
            self.stroke_width_spin.blockSignals(False)

        self.canvas.annotations = [
            AnnotationItem(
                id=a.id,
                kind=a.type,
                start=QPointF(a.x1 / scale, a.y1 / scale),
                end=QPointF(a.x2 / scale, a.y2 / scale),
                text=a.text,
                color=QColor(a.color),
                stroke_width=max(1, round(a.stroke_width / scale)) if scale else a.stroke_width,
                border_radius=max(0, round(a.border_radius / scale)) if scale else a.border_radius,
                show_arrow=a.show_arrow,
                shape=a.shape,
                arrow_stroke_width=max(1, round(a.arrow_stroke_width / scale)) if scale else a.arrow_stroke_width,
                show_text=a.show_text,
                fill_enabled=a.fill_enabled,
                bold_text=a.bold_text,
                line_arrow_start=a.line_arrow_start,
                line_arrow_end=a.line_arrow_end,
            )
            for a in recipe.annotations
        ]
        self.layer_order = list(recipe.layer_order)
        self.canvas.layer_order = self.layer_order

        # Les spin boxes du panneau travaillent en espace aperçu : elles sont
        # alimentées depuis les loupes converties, jamais depuis les valeurs
        # pleine résolution du JSON (qui dépassaient leurs bornes et bloquaient
        # les boutons « + » / faussaient l'épaisseur enregistrée).
        self.canvas.loupes = [
            LoupeOverlay(
                id=loupe.id,
                enabled=loupe.enabled,
                center=QPointF(loupe.center_x / scale, loupe.center_y / scale),
                radius=max(20, round(loupe.radius / scale)),
                zoom=loupe.zoom,
                arrow=(
                    QPointF(loupe.arrow_start_x / scale, loupe.arrow_start_y / scale),
                    QPointF(loupe.arrow_end_x / scale, loupe.arrow_end_y / scale),
                ),
                color=QColor(loupe.color),
                rotation=loupe.rotation,
                stroke_width=max(1, round(loupe.stroke_width / scale)),
                arrow_stroke_width=max(1, round(loupe.arrow_stroke_width / scale)),
            )
            for loupe in recipe.loupes
        ]
        self._sync_loupe_controls()

        self._rebuild_preview_from_original()
        self.refresh_objects_list()


# Import main as launch_editor from external scripts if needed
def main() -> None:
    """
    Description:

    @author ArnauldDev
    @created 2026-09-20
    @modified 2026-09-20
    @version 1

    @returns
    """
    load_dotenv()
    update_config_in_place(AppConfig())
    app = QApplication([])
    if config.qt_style:
        # Style de base sous les thèmes QSS (Fusion par défaut, voir APP_QT_STYLE).
        app.setStyle(config.qt_style)
    if APP_ICON_PATH.exists():
        # Nécessaire sur certaines plateformes/gestionnaires de fenêtres pour que
        # l'icône de la barre des tâches/du raccourci corresponde à celle affichée.
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))
    window = ImageEditorWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()

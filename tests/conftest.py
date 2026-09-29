import os

import pytest
from PIL import Image

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(autouse=True)
def isolated_user_settings(tmp_path, monkeypatch):
    """Keep the editor's QSettings and recent-files history inside ``tmp_path``.

    Without this, every test creating an ``ImageEditorWindow`` would read and
    overwrite the developer's real preferences (theme, layout, recent files).
    """
    try:
        import iat.qt_image_editor as editor
        from PyQt6.QtCore import QSettings
    except ImportError:  # pragma: no cover - PyQt6 absent: pure engine tests only
        yield
        return
    ini_path = str(tmp_path / "settings.ini")
    monkeypatch.setattr(editor, "QSettings", lambda *_args: QSettings(ini_path, QSettings.Format.IniFormat))
    monkeypatch.setattr(editor, "_RECENT_FILES_PATH", tmp_path / "recent_files.json")
    yield


@pytest.fixture
def sample_rgb_image():
    """Return a simple synthetic 200x150 RGB image for testing."""
    image = Image.new("RGB", (200, 150), color="blue")
    for x in range(20, 60):
        for y in range(20, 60):
            image.putpixel((x, y), (255, 0, 0))
    return image


@pytest.fixture
def temp_image_file(tmp_path, sample_rgb_image):
    """Save a sample image to disk in a temporary directory and yield its Path."""
    image_file = tmp_path / "test_sample-raw.jpg"
    sample_rgb_image.save(image_file, format="JPEG")
    return image_file

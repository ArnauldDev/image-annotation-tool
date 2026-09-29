#!/usr/bin/env python3
"""
  File Name: test_config.py
  Description: Tests unitaires pour le module de configuration et harness .env.
  Developer: ArnauldDev
  Created Date: 2026-09-12
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from iat.config import AppConfig, load_dotenv, reload_config


def test_default_config_values(monkeypatch):
    """Vérifie les valeurs par défaut de AppConfig."""
    for key in [
        "APP_ENV",
        "APP_DEBUG",
        "APP_THEME",
        "APP_QT_STYLE",
        "DEFAULT_PREVIEW_MAX_DIMENSION",
        "DEFAULT_EXPORT_QUALITY",
        "DEFAULT_STROKE_WIDTH",
        "FEATURE_RECENT_FILES_HISTORY",
        "FEATURE_TRAPEZOID_ROTATION",
        "FEATURE_CORNER_RADIUS",
        "FEATURE_MULTI_LOUPE",
    ]:
        monkeypatch.delenv(key, raising=False)

    cfg = AppConfig.load(env_path=None, override=True)
    assert cfg.app_env == "production"
    assert cfg.debug is False
    assert cfg.app_theme == "cbi"
    assert cfg.qt_style == "Fusion"
    assert not hasattr(cfg, "cbi_primary_color"), "les couleurs ne doivent provenir que des thèmes"
    assert cfg.preview_max_dimension == 1600
    assert cfg.export_quality == 95
    assert cfg.default_stroke_width == 3
    assert cfg.feature_recent_files_history is True
    assert cfg.feature_trapezoid_rotation is False
    assert cfg.feature_multi_loupe is True


def test_load_dotenv_from_file(tmp_path, monkeypatch):
    """Vérifie le chargement des variables depuis un fichier .env sur disque."""
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=development\n"
        "APP_DEBUG=true\n"
        "APP_THEME='sombre'\n"
        "DEFAULT_PREVIEW_MAX_DIMENSION=2000\n"
        "DEFAULT_STROKE_WIDTH=5\n"
        "FEATURE_TRAPEZOID_ROTATION=true\n",
        encoding="utf-8",
    )
    # Déclarer les clés au préalable : monkeypatch les restaure après le test, sinon
    # le .env chargé resterait dans os.environ pour les tests suivants (APP_THEME=sombre…).
    for key in ("APP_ENV", "APP_DEBUG", "APP_THEME", "DEFAULT_PREVIEW_MAX_DIMENSION",
                "DEFAULT_STROKE_WIDTH", "FEATURE_TRAPEZOID_ROTATION"):
        monkeypatch.setenv(key, "")

    cfg = AppConfig.load(env_path=env_file, override=True)
    assert cfg.app_env == "development"
    assert cfg.debug is True
    assert cfg.app_theme == "sombre"
    assert cfg.preview_max_dimension == 2000
    assert cfg.default_stroke_width == 5
    assert cfg.feature_trapezoid_rotation is True


def test_feature_flags_checker(monkeypatch):
    """Vérifie la méthode is_feature_enabled()."""
    for key in os.environ:
        if key.startswith("FEATURE_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("FEATURE_CUSTOM_TEST", "true")
    monkeypatch.setenv("FEATURE_RECENT_FILES_HISTORY", "true")
    monkeypatch.setenv("FEATURE_TRAPEZOID_ROTATION", "false")

    cfg = AppConfig.load(env_path=Path("non_existent_.env"), override=True)
    assert cfg.is_feature_enabled("recent_files_history") is True
    assert cfg.is_feature_enabled("trapezoid_rotation") is False
    assert cfg.is_feature_enabled("custom_test") is True
    assert cfg.is_feature_enabled("non_existent") is False


def test_reload_config_global(tmp_path, monkeypatch):
    """Vérifie que reload_config met à jour l'instance globale."""
    env_file = tmp_path / ".env.test"
    env_file.write_text("DEFAULT_EXPORT_QUALITY=80\n", encoding="utf-8")

    reloaded = reload_config(env_path=env_file, override=True)
    assert reloaded.export_quality == 80

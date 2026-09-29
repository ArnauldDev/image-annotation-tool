#!/usr/bin/env python3
"""
  File Name: config.py
  Description: Module de configuration et harness .env (variables d'environnement et feature flags).
  Developer: ArnauldDev
  Created Date: 2026-09-12
  Last Modified: 2026-09-23
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


def load_dotenv(env_path: Optional[str | Path] = None, override: bool = False) -> dict[str, str]:
    """Charge un fichier .env dans os.environ.

    Utilise `python-dotenv` si le module est installé, sinon bascule sur un analyseur
    natif léger en bibliothèque standard Python.
    """
    try:
        import dotenv  # type: ignore

        if env_path is not None:
            path_obj = Path(env_path)
            if path_obj.exists():
                dotenv.load_dotenv(dotenv_path=path_obj, override=override)
        else:
            dotenv.load_dotenv(override=override)
    except ImportError:
        pass

    # Analyseur natif de secours (fallback standard library)
    if env_path is None:
        candidates = [
            Path.cwd() / ".env",
            Path(__file__).resolve().parents[1] / ".env",
        ]
        target = next((p for p in candidates if p.exists() and p.is_file()), None)
    else:
        target = Path(env_path) if Path(env_path).exists() else None

    loaded: dict[str, str] = {}
    if target and target.is_file():
        try:
            content = target.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                elif " #" in value:
                    value = value.split(" #", 1)[0].strip()

                loaded[key] = value
                if override or key not in os.environ:
                    os.environ[key] = value
        except Exception:
            pass

    return loaded


def _get_str_env(key: str, default: str) -> str:
    val = os.getenv(key)
    return val.strip() if val is not None else default


def _get_bool_env(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on", "y")


def _get_int_env(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def _get_float_env(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val.strip())
    except ValueError:
        return default


@dataclass
class AppConfig:
    """Structure de configuration globale et feature flags pour l'application."""

    # Environnement et débogage
    app_env: str = field(default_factory=lambda: _get_str_env("APP_ENV", "production"))
    debug: bool = field(default_factory=lambda: _get_bool_env("APP_DEBUG", False))

    # Apparence : l'unique source des couleurs est le dossier ``themes/``.
    # APP_THEME désigne le thème appliqué par défaut (nom du fichier .qss, sans
    # extension) tant que l'utilisateur n'en a pas choisi un autre via le menu.
    app_theme: str = field(default_factory=lambda: _get_str_env("APP_THEME", "cbi"))
    #: Style Qt de base sur lequel les thèmes QSS sont appliqués. « Fusion »
    #: respecte intégralement les feuilles de style (menus, champs numériques…),
    #: contrairement au style natif « windows11 ».
    qt_style: str = field(default_factory=lambda: _get_str_env("APP_QT_STYLE", "Fusion"))
    #: Langue de l'interface par défaut (« fr » = textes du code, sinon fichier
    #: ``translations/<code>.json``) tant que l'utilisateur n'en a pas choisi une autre.
    app_language: str = field(default_factory=lambda: _get_str_env("APP_LANGUAGE", "fr"))

    # Paramètres de traitement d'image
    preview_max_dimension: int = field(
        default_factory=lambda: _get_int_env("DEFAULT_PREVIEW_MAX_DIMENSION", 1600)
    )
    export_quality: int = field(default_factory=lambda: _get_int_env("DEFAULT_EXPORT_QUALITY", 95))
    default_stroke_width: int = field(default_factory=lambda: _get_int_env("DEFAULT_STROKE_WIDTH", 3))

    # Feature Flags (Harness pour nouvelles fonctionnalités)
    feature_recent_files_history: bool = field(
        default_factory=lambda: _get_bool_env("FEATURE_RECENT_FILES_HISTORY", True)
    )
    feature_trapezoid_rotation: bool = field(
        default_factory=lambda: _get_bool_env("FEATURE_TRAPEZOID_ROTATION", False)
    )
    feature_corner_radius: bool = field(
        default_factory=lambda: _get_bool_env("FEATURE_CORNER_RADIUS", False)
    )
    feature_multi_loupe: bool = field(
        default_factory=lambda: _get_bool_env("FEATURE_MULTI_LOUPE", True)
    )

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Vérifie si une fonctionnalité spécifique est activée."""
        attr = f"feature_{feature_name}"
        if hasattr(self, attr):
            return getattr(self, attr)
        env_key = f"FEATURE_{feature_name.upper()}"
        return _get_bool_env(env_key, False)

    @classmethod
    def load(cls, env_path: Optional[str | Path] = None, override: bool = False) -> AppConfig:
        """Charge le fichier .env et retourne une nouvelle instance AppConfig."""
        load_dotenv(env_path, override=override)
        return cls()


#: Instance globale de configuration
config = AppConfig.load()


def reload_config(env_path: Optional[str | Path] = None, override: bool = True) -> AppConfig:
    """Recharge la configuration globale en réévaluant l'environnement."""
    refreshed = AppConfig.load(env_path, override=override)
    config.__dict__.update(refreshed.__dict__)
    return config


def update_config_in_place(new_config: AppConfig) -> AppConfig:
    """Update the shared configuration object without invalidating imports."""
    config.__dict__.update(new_config.__dict__)
    return config

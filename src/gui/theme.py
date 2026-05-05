"""QSS 기반 앱 테마 로더."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_THEMES_DIR = Path(__file__).parent.parent.parent / "assets" / "styles"
_SUPPORTED_THEMES = frozenset({"dark", "light"})


def normalize_theme_name(theme_name: str | None) -> str:
    if theme_name in _SUPPORTED_THEMES:
        return str(theme_name)
    return "dark"


def load_theme_stylesheet(theme_name: str | None) -> str:
    normalized = normalize_theme_name(theme_name)
    stylesheet_path = _THEMES_DIR / f"{normalized}.qss"
    if stylesheet_path.exists():
        return stylesheet_path.read_text(encoding="utf-8")
    fallback_path = _THEMES_DIR / "dark.qss"
    return fallback_path.read_text(encoding="utf-8") if fallback_path.exists() else ""


def apply_theme(app: QApplication, theme_name: str | None) -> str:
    normalized = normalize_theme_name(theme_name)
    app.setStyleSheet(load_theme_stylesheet(normalized))
    return normalized

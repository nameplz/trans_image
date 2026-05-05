"""theme 유틸 테스트."""
from __future__ import annotations

from pathlib import Path

from src.gui.theme import apply_theme, load_theme_stylesheet, normalize_theme_name


class TestTheme:
    def test_normalize_theme_name_defaults_to_dark(self):
        assert normalize_theme_name(None) == "dark"
        assert normalize_theme_name("unknown") == "dark"
        assert normalize_theme_name("light") == "light"

    def test_load_theme_stylesheet_uses_requested_file(self, monkeypatch, tmp_path):
        themes_dir = tmp_path / "styles"
        themes_dir.mkdir()
        (themes_dir / "dark.qss").write_text("dark-style", encoding="utf-8")
        (themes_dir / "light.qss").write_text("light-style", encoding="utf-8")
        monkeypatch.setattr("src.gui.theme._THEMES_DIR", themes_dir)

        assert load_theme_stylesheet("light") == "light-style"

    def test_load_theme_stylesheet_falls_back_to_dark(self, monkeypatch, tmp_path):
        themes_dir = tmp_path / "styles"
        themes_dir.mkdir()
        (themes_dir / "dark.qss").write_text("dark-style", encoding="utf-8")
        monkeypatch.setattr("src.gui.theme._THEMES_DIR", themes_dir)

        assert load_theme_stylesheet("missing") == "dark-style"

    def test_apply_theme_sets_stylesheet_and_returns_normalized_name(self, monkeypatch):
        app = type("FakeApp", (), {"setStyleSheet": lambda self, text: setattr(self, "stylesheet", text)})()
        monkeypatch.setattr("src.gui.theme.load_theme_stylesheet", lambda name: f"{name}-sheet")

        result = apply_theme(app, "light")

        assert result == "light"
        assert app.stylesheet == "light-sheet"

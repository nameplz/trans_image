"""SettingsDialog 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QWidget

from src.gui.dialogs.settings_dialog import SettingsDialog


class FakeSettingsPanel(QWidget):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(kwargs.get("parent"))
        self.apply_calls = 0
        self.current_settings = {
            "source_lang": "en",
            "target_lang": "ko",
            "ocr_plugin": "easyocr",
            "translator_plugin": "deepl",
            "agent_plugin": "claude",
            "use_agent": True,
        }

    def _on_apply(self) -> None:
        self.apply_calls += 1

    def get_current_settings(self) -> dict:
        return self.current_settings


class TestSettingsDialog:
    def test_on_ok_applies_settings_and_accepts(self, qtbot):
        config = MagicMock()
        plugin_manager = MagicMock()

        with patch("src.gui.dialogs.settings_dialog.SettingsPanel", FakeSettingsPanel):
            dialog = SettingsDialog(config, plugin_manager)
            qtbot.addWidget(dialog)
            dialog.accept = MagicMock()

            dialog._on_ok()

        assert dialog._panel.apply_calls == 1
        config.save.assert_called_once_with()
        dialog.accept.assert_called_once()

    def test_get_settings_delegates_to_panel(self, qtbot):
        config = MagicMock()
        plugin_manager = MagicMock()

        with patch("src.gui.dialogs.settings_dialog.SettingsPanel", FakeSettingsPanel):
            dialog = SettingsDialog(config, plugin_manager)
            qtbot.addWidget(dialog)

            result = dialog.get_settings()

        assert result == {
            "source_lang": "en",
            "target_lang": "ko",
            "ocr_plugin": "easyocr",
            "translator_plugin": "deepl",
            "agent_plugin": "claude",
            "use_agent": True,
        }

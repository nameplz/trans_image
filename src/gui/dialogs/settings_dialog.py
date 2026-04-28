"""설정 다이얼로그."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QVBoxLayout,
)

from src.core.exceptions import ConfigError
from src.core.config_manager import ConfigManager
from src.core.plugin_manager import PluginManager
from src.gui.widgets.settings_panel import SettingsPanel


class SettingsDialog(QDialog):
    def __init__(
        self,
        config: ConfigManager,
        plugin_manager: PluginManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("설정")
        self.setMinimumWidth(400)
        self._panel = SettingsPanel(config, plugin_manager, self)

        layout = QVBoxLayout(self)
        layout.addWidget(self._panel)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_ok(self) -> None:
        self._panel._on_apply()
        try:
            self._config.save()
        except ConfigError as exc:
            QMessageBox.critical(self, "설정 저장 실패", str(exc))
            return
        self.accept()

    def get_settings(self) -> dict:
        return self._panel.get_current_settings()

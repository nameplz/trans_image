"""플러그인 선택 + API 키 설정 패널."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QCheckBox,
)

from src.core.config_manager import ConfigManager
from src.core.plugin_manager import PluginManager


class SettingsPanel(QWidget):
    """파이프라인 설정 UI."""

    settings_changed = Signal()

    def __init__(
        self,
        config: ConfigManager,
        plugin_manager: PluginManager,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._plugin_manager = plugin_manager
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        processing_settings = self._config.processing_settings

        # 언어 설정
        lang_group = QGroupBox("언어 설정")
        lang_form = QFormLayout(lang_group)

        self._source_lang = QLineEdit()
        self._source_lang.setText(processing_settings.default_source_lang)
        self._source_lang.setPlaceholderText("auto 또는 en, ko, ja ...")
        lang_form.addRow("소스 언어:", self._source_lang)

        self._target_lang = QLineEdit()
        self._target_lang.setText(processing_settings.default_target_lang)
        lang_form.addRow("목표 언어:", self._target_lang)
        layout.addWidget(lang_group)

        # 플러그인 선택
        plugin_group = QGroupBox("플러그인 선택")
        plugin_form = QFormLayout(plugin_group)

        self._ocr_combo = QComboBox()
        for pid in self._plugin_manager.list_available("ocr"):
            self._ocr_combo.addItem(pid)
        self._select_combo_value(self._ocr_combo, processing_settings.default_ocr_plugin)
        plugin_form.addRow("OCR 플러그인:", self._ocr_combo)

        self._easyocr_gpu_check = QCheckBox("EasyOCR GPU 사용")
        self._easyocr_gpu_check.setChecked(self._get_easyocr_gpu_enabled())
        plugin_form.addRow("", self._easyocr_gpu_check)

        self._translator_combo = QComboBox()
        for pid in self._plugin_manager.list_available("translators"):
            self._translator_combo.addItem(pid)
        self._select_combo_value(
            self._translator_combo,
            processing_settings.default_translator_plugin,
        )
        plugin_form.addRow("번역 플러그인:", self._translator_combo)

        self._agent_combo = QComboBox()
        for pid in self._plugin_manager.list_available("agents"):
            self._agent_combo.addItem(pid)
        self._select_combo_value(self._agent_combo, processing_settings.default_agent_plugin)
        plugin_form.addRow("에이전트 플러그인:", self._agent_combo)

        self._use_agent_check = QCheckBox("에이전트 분석/검증 사용")
        self._use_agent_check.setChecked(processing_settings.use_agent)
        plugin_form.addRow("", self._use_agent_check)
        layout.addWidget(plugin_group)

        # 적용 버튼
        apply_btn = QPushButton("설정 적용")
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)
        layout.addStretch()

    def _select_combo_value(self, combo: QComboBox, value: str) -> None:
        if not value:
            return
        index = combo.findText(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    def _get_easyocr_gpu_enabled(self) -> bool:
        entry = self._config.get_plugin_config("ocr", "easyocr")
        if entry is None:
            return False
        config = getattr(entry, "config", {})
        return bool(config.get("gpu", False))

    def _on_apply(self) -> None:
        current_gpu_enabled = self._get_easyocr_gpu_enabled()
        next_gpu_enabled = self._easyocr_gpu_check.isChecked()

        self._config.set("processing", "default_source_lang", value=self._source_lang.text().strip())
        self._config.set("processing", "default_target_lang", value=self._target_lang.text().strip())
        self._config.set("processing", "default_ocr_plugin", value=self._ocr_combo.currentText())
        self._config.set(
            "processing",
            "default_translator_plugin",
            value=self._translator_combo.currentText(),
        )
        self._config.set("processing", "default_agent_plugin", value=self._agent_combo.currentText())
        self._config.set("processing", "use_agent", value=self._use_agent_check.isChecked())
        self._config.set_plugin_config_value("ocr", "easyocr", "gpu", value=next_gpu_enabled)
        if current_gpu_enabled != next_gpu_enabled:
            self._plugin_manager.invalidate_plugin("ocr", "easyocr")
        self.settings_changed.emit()

    def get_current_settings(self) -> dict:
        return {
            "source_lang": self._source_lang.text().strip() or "auto",
            "target_lang": self._target_lang.text().strip() or "ko",
            "ocr_plugin": self._ocr_combo.currentText(),
            "translator_plugin": self._translator_combo.currentText(),
            "agent_plugin": self._agent_combo.currentText(),
            "use_agent": self._use_agent_check.isChecked(),
        }

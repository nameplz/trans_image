"""SettingsPanel 단위 테스트."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.config_manager import ConfigManager
from src.core.plugin_manager import PluginManager
from src.gui.widgets.settings_panel import SettingsPanel


@pytest.fixture
def settings_deps():
    """ConfigManager / PluginManager Mock 반환."""
    config = MagicMock(spec=ConfigManager)
    config.get.side_effect = lambda *args, **kw: {
        ("processing", "default_source_lang"): "en",
        ("processing", "default_target_lang"): "ko",
        ("processing", "default_ocr_plugin"): "easyocr",
        ("processing", "default_translator_plugin"): "gemini",
        ("processing", "default_agent_plugin"): "gemini_agent",
        ("processing", "use_agent"): True,
    }.get(args, kw.get("default"))
    config.set = MagicMock()
    config.processing_settings = SimpleNamespace(
        default_source_lang="en",
        default_target_lang="ko",
        default_ocr_plugin="easyocr",
        default_translator_plugin="gemini",
        default_agent_plugin="gemini_agent",
        use_agent=True,
    )

    pm = MagicMock(spec=PluginManager)
    pm.list_available.side_effect = lambda t: {
        "ocr": ["easyocr"],
        "translators": ["deepl", "gemini"],
        "agents": ["gemini_agent"],
    }.get(t, [])

    return config, pm


@pytest.fixture
def panel(qtbot, settings_deps):
    """SettingsPanel 인스턴스 생성 후 qtbot 등록."""
    config, pm = settings_deps
    widget = SettingsPanel(config=config, plugin_manager=pm)
    qtbot.addWidget(widget)
    return widget


class TestSettingsPanel:
    def test_initial_values_loaded(self, panel):
        """생성 직후 config 값이 소스/목표 언어 필드에 반영되어야 한다."""
        assert panel._source_lang.text() == "en"
        assert panel._target_lang.text() == "ko"

    def test_use_agent_checkbox_initial(self, panel):
        """생성 직후 use_agent 체크박스가 config 값에 따라 체크된 상태여야 한다."""
        assert panel._use_agent_check.isChecked() is True

    def test_get_current_settings_returns_dict(self, panel):
        """get_current_settings()가 필수 키를 모두 포함한 dict를 반환해야 한다."""
        result = panel.get_current_settings()
        required_keys = {
            "source_lang",
            "target_lang",
            "ocr_plugin",
            "translator_plugin",
            "agent_plugin",
            "use_agent",
        }
        assert required_keys.issubset(result.keys())

    def test_get_current_settings_values(self, panel):
        """get_current_settings()가 현재 UI 상태의 값을 정확히 반환해야 한다."""
        result = panel.get_current_settings()
        assert result["source_lang"] == "en"
        assert result["target_lang"] == "ko"
        assert result["ocr_plugin"] == "easyocr"
        assert result["translator_plugin"] == "gemini"
        assert result["agent_plugin"] == "gemini_agent"
        assert result["use_agent"] is True

    def test_apply_saves_to_config(self, qtbot, settings_deps):
        """설정 적용 시 config.set이 각 설정 키에 대해 호출되어야 한다."""
        config, pm = settings_deps
        widget = SettingsPanel(config=config, plugin_manager=pm)
        qtbot.addWidget(widget)

        widget._on_apply()

        calls = {call.args[:2]: call.kwargs.get("value") for call in config.set.call_args_list}
        assert ("processing", "default_source_lang") in calls
        assert ("processing", "default_target_lang") in calls
        assert ("processing", "default_ocr_plugin") in calls
        assert ("processing", "default_translator_plugin") in calls
        assert ("processing", "default_agent_plugin") in calls
        assert ("processing", "use_agent") in calls

    def test_current_plugin_selection_loaded_from_config(self, panel):
        """기본 플러그인 선택은 저장된 config 값을 따라야 한다."""
        assert panel._ocr_combo.currentText() == "easyocr"
        assert panel._translator_combo.currentText() == "gemini"
        assert panel._agent_combo.currentText() == "gemini_agent"

    def test_apply_emits_settings_changed(self, qtbot, settings_deps):
        """설정 적용 시 settings_changed 시그널이 emit 되어야 한다."""
        config, pm = settings_deps
        widget = SettingsPanel(config=config, plugin_manager=pm)
        qtbot.addWidget(widget)

        with qtbot.waitSignal(widget.settings_changed, timeout=1000):
            widget._on_apply()

    def test_plugin_lists_populated(self, panel):
        """OCR·번역·에이전트 콤보박스에 플러그인 목록이 로드되어야 한다."""
        assert panel._ocr_combo.count() == 1
        assert panel._ocr_combo.itemText(0) == "easyocr"

        assert panel._translator_combo.count() == 2
        assert panel._translator_combo.itemText(0) == "deepl"
        assert panel._translator_combo.itemText(1) == "gemini"

        assert panel._agent_combo.count() == 1
        assert panel._agent_combo.itemText(0) == "gemini_agent"

from __future__ import annotations

import pytest

from src.core.exceptions import ConfigError
from src.core.plugin_registry_models import PluginRegistry
from src.core.settings_models import ChatSettings, ProcessingSettings, RenderingSettings


class TestSettingsModels:
    def test_processing_settings_from_dict_reads_values(self):
        settings = ProcessingSettings.from_dict(
            {
                "default_source_lang": "en",
                "default_target_lang": "ko",
                "use_agent": False,
            }
        )

        assert settings.default_source_lang == "en"
        assert settings.use_agent is False

    def test_rendering_settings_rejects_invalid_type(self):
        with pytest.raises(ConfigError):
            RenderingSettings.from_dict({"min_font_size": "small"})

    def test_chat_settings_uses_defaults_for_missing_values(self):
        settings = ChatSettings.from_dict({})
        assert settings.llm_provider == "anthropic"

    def test_plugin_registry_builds_typed_entries(self):
        registry = PluginRegistry.from_dict(
            {
                "ocr": [
                    {
                        "id": "easyocr",
                        "enabled": True,
                        "module": "src.plugins.ocr.easyocr_plugin",
                        "class": "EasyOCRPlugin",
                        "config": {"gpu": False},
                    }
                ]
            }
        )

        entry = registry.get_plugin_config("ocr", "easyocr")
        assert entry is not None
        assert entry.plugin_id == "easyocr"

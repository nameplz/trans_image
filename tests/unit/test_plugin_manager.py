"""PluginManager 단위 테스트."""
from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.exceptions import PluginNotFoundError
from src.core.plugin_manager import PluginManager
from src.plugins.base.plugin_base import PluginBase


def make_mock_plugin_class(name="test_plugin"):
    """MagicMock 플러그인 클래스 팩토리."""
    instance = MagicMock(spec=PluginBase)
    instance.is_loaded = True
    instance.PLUGIN_NAME = name
    instance.unload = AsyncMock()

    cls = MagicMock(return_value=instance)
    return cls, instance


def make_plugin_entry(
    plugin_id: str,
    module: str = "fake.module",
    classname: str = "FakePlugin",
    enabled: bool = True,
    config: dict | None = None,
) -> dict:
    return {
        "id": plugin_id,
        "enabled": enabled,
        "module": module,
        "class": classname,
        "config": config or {},
    }


class TestGetPlugin:
    def test_first_call_creates_instance(self):
        """get_plugin 최초 호출 → 인스턴스 생성."""
        config = MagicMock()
        entry = make_plugin_entry("deepl", config={"api_key": "test"})
        config.get_plugin_config.return_value = entry
        config.get_api_key.return_value = "test-key"

        cls, instance = make_mock_plugin_class()
        manager = PluginManager(config)

        with patch.object(manager, "_load_class", return_value=cls):
            result = manager.get_plugin("translators", "deepl")
        assert result is instance

    def test_second_call_returns_cached_instance(self):
        """동일 ID 두 번 호출 → 캐시된 같은 인스턴스 (is 비교)."""
        config = MagicMock()
        entry = make_plugin_entry("deepl")
        config.get_plugin_config.return_value = entry
        config.get_api_key.return_value = ""

        cls, instance = make_mock_plugin_class()
        manager = PluginManager(config)

        with patch.object(manager, "_load_class", return_value=cls):
            first = manager.get_plugin("translators", "deepl")
            second = manager.get_plugin("translators", "deepl")

        assert first is second
        # 클래스 생성자는 한 번만 호출
        assert cls.call_count == 1

    def test_unregistered_id_raises(self):
        """미등록 ID → PluginNotFoundError 발생."""
        config = MagicMock()
        config.get_plugin_config.return_value = None
        manager = PluginManager(config)

        with pytest.raises(PluginNotFoundError):
            manager.get_plugin("translators", "nonexistent")

    def test_disabled_plugin_raises(self):
        """enabled=False → PluginNotFoundError 발생."""
        config = MagicMock()
        entry = make_plugin_entry("deepl", enabled=False)
        config.get_plugin_config.return_value = entry
        manager = PluginManager(config)

        with pytest.raises(PluginNotFoundError):
            manager.get_plugin("translators", "deepl")


class TestResolveConfig:
    def test_env_suffix_reads_from_environ(self):
        """_env 접미사 키 → os.environ에서 값 읽기."""
        config = MagicMock()
        config.get_api_key.return_value = "my-api-key"
        manager = PluginManager(config)

        raw = {"api_key_env": "DEEPL_API_KEY", "free_api": False}
        resolved = manager._resolve_config(raw)

        config.get_api_key.assert_called_once_with("DEEPL_API_KEY")
        assert "api_key" in resolved
        assert resolved["api_key"] == "my-api-key"
        assert "api_key_env" not in resolved

    def test_non_env_key_kept_as_is(self):
        """_env 아닌 키 → 그대로 유지."""
        config = MagicMock()
        manager = PluginManager(config)

        raw = {"model": "gpt-4o", "max_tokens": 4096}
        resolved = manager._resolve_config(raw)

        assert resolved["model"] == "gpt-4o"
        assert resolved["max_tokens"] == 4096

    def test_non_string_env_value_skipped(self):
        """_env 접미사이지만 값이 str이 아닌 경우 → get_api_key 호출 안 함."""
        config = MagicMock()
        manager = PluginManager(config)

        # 숫자값은 _env 처리 안 됨 (isinstance check)
        raw = {"timeout_env": 30}
        resolved = manager._resolve_config(raw)
        config.get_api_key.assert_not_called()


class TestListAvailable:
    def test_lists_enabled_plugins(self):
        """list_available → 활성 플러그인 ID 목록 반환."""
        config = MagicMock()
        config.get_plugin_configs.return_value = [
            {"id": "deepl", "enabled": True},
            {"id": "gemini", "enabled": True},
            {"id": "ollama", "enabled": False},
        ]
        manager = PluginManager(config)
        ids = manager.list_available("translators")
        assert "deepl" in ids
        assert "gemini" in ids
        assert "ollama" not in ids


class TestUnloadAll:
    async def test_unload_all_calls_unload(self):
        """unload_all() → 로드된 플러그인의 unload() 호출."""
        config = MagicMock()
        manager = PluginManager(config)

        plugin1 = MagicMock(spec=PluginBase)
        plugin1.is_loaded = True
        plugin1.unload = AsyncMock()

        plugin2 = MagicMock(spec=PluginBase)
        plugin2.is_loaded = True
        plugin2.unload = AsyncMock()

        manager._instances = {
            "translators:deepl": plugin1,
            "translators:gemini": plugin2,
        }
        await manager.unload_all()

        plugin1.unload.assert_called_once()
        plugin2.unload.assert_called_once()
        assert len(manager._instances) == 0

    async def test_unload_all_skips_not_loaded(self):
        """is_loaded=False 플러그인은 unload 호출 안 함."""
        config = MagicMock()
        manager = PluginManager(config)

        plugin = MagicMock(spec=PluginBase)
        plugin.is_loaded = False
        plugin.unload = AsyncMock()

        manager._instances = {"ocr:easyocr": plugin}
        await manager.unload_all()
        plugin.unload.assert_not_called()


class TestGetTypedPlugins:
    def test_get_ocr_plugin_returns_ocr_type(self):
        """get_ocr_plugin → AbstractOCRPlugin 인스턴스 반환."""
        from src.plugins.base.ocr_plugin import AbstractOCRPlugin

        config = MagicMock()
        entry = make_plugin_entry("easyocr")
        config.get_plugin_config.return_value = entry

        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin
        manager = PluginManager(config)

        with patch.object(manager, "_load_class", return_value=EasyOCRPlugin):
            result = manager.get_ocr_plugin("easyocr")

        assert isinstance(result, AbstractOCRPlugin)

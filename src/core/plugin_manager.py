"""플러그인 발견·로드·제공 관리자."""
from __future__ import annotations

import importlib
from typing import Any, TypeVar

from src.core.config_manager import ConfigManager
from src.core.exceptions import PluginLoadError, PluginNotFoundError
from src.plugins.base.agent_plugin import AbstractAgentPlugin
from src.plugins.base.ocr_plugin import AbstractOCRPlugin
from src.plugins.base.plugin_base import PluginBase
from src.plugins.base.translator_plugin import AbstractTranslatorPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.plugin_manager")

P = TypeVar("P", bound=PluginBase)

_PLUGIN_TYPE_MAP = {
    "ocr": AbstractOCRPlugin,
    "translators": AbstractTranslatorPlugin,
    "agents": AbstractAgentPlugin,
}


class PluginManager:
    """플러그인 레지스트리 기반 동적 로드 및 인스턴스 캐시."""

    def __init__(self, config_manager: ConfigManager) -> None:
        self._config = config_manager
        self._instances: dict[str, PluginBase] = {}  # "type:id" → instance

    def _cache_key(self, plugin_type: str, plugin_id: str) -> str:
        return f"{plugin_type}:{plugin_id}"

    def _load_class(self, module_path: str, class_name: str) -> type:
        try:
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise PluginLoadError(
                f"플러그인 클래스 로드 실패 ({module_path}.{class_name}): {e}"
            ) from e

    def get_plugin(
        self,
        plugin_type: str,
        plugin_id: str,
    ) -> PluginBase:
        """플러그인 인스턴스 반환 (캐시 미스 시 생성).

        Args:
            plugin_type: 'ocr' | 'translators' | 'agents'
            plugin_id: plugins.yaml에 정의된 id

        Raises:
            PluginNotFoundError: 플러그인 ID 없음 또는 비활성화
            PluginLoadError: 모듈 로드 실패
        """
        key = self._cache_key(plugin_type, plugin_id)
        if key in self._instances:
            return self._instances[key]

        entry = self._config.get_plugin_config(plugin_type, plugin_id)
        if not entry:
            raise PluginNotFoundError(f"플러그인 없음: {plugin_type}/{plugin_id}")
        if not self._is_enabled(entry):
            raise PluginNotFoundError(f"플러그인 비활성화: {plugin_type}/{plugin_id}")

        cls = self._load_class(self._entry_module(entry), self._entry_class(entry))
        plugin_config = self._entry_config(entry)

        # API 키 환경변수 해석
        resolved_config = self._resolve_config(plugin_config)

        instance = cls(config=resolved_config)
        self._instances[key] = instance
        logger.info("플러그인 인스턴스 생성: %s", key)
        return instance

    def _resolve_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """config 딕셔너리 내 *_env 키를 환경변수 값으로 해석."""
        resolved = {}
        for k, v in config.items():
            if k.endswith("_env") and isinstance(v, str):
                api_key = self._config.get_api_key(v)
                # _env 접미사 제거 후 저장
                resolved[k[:-4]] = api_key
            else:
                resolved[k] = v
        return resolved

    def _is_enabled(self, entry: Any) -> bool:
        return bool(entry.enabled if hasattr(entry, "enabled") else entry.get("enabled", False))

    def _entry_module(self, entry: Any) -> str:
        return entry.module if hasattr(entry, "module") else entry["module"]

    def _entry_class(self, entry: Any) -> str:
        return entry.class_name if hasattr(entry, "class_name") else entry["class"]

    def _entry_config(self, entry: Any) -> dict[str, Any]:
        return entry.config if hasattr(entry, "config") else entry.get("config", {})

    def get_ocr_plugin(self, plugin_id: str) -> AbstractOCRPlugin:
        plugin = self.get_plugin("ocr", plugin_id)
        assert isinstance(plugin, AbstractOCRPlugin)
        return plugin

    def get_translator_plugin(self, plugin_id: str) -> AbstractTranslatorPlugin:
        plugin = self.get_plugin("translators", plugin_id)
        assert isinstance(plugin, AbstractTranslatorPlugin)
        return plugin

    def get_agent_plugin(self, plugin_id: str) -> AbstractAgentPlugin:
        plugin = self.get_plugin("agents", plugin_id)
        assert isinstance(plugin, AbstractAgentPlugin)
        return plugin

    def list_available(self, plugin_type: str) -> list[str]:
        """활성화된 플러그인 ID 목록 반환."""
        return [
            e.plugin_id if hasattr(e, "plugin_id") else e["id"]
            for e in self._config.get_plugin_configs(plugin_type)
            if self._is_enabled(e)
        ]

    async def unload_all(self) -> None:
        """모든 로드된 플러그인 해제."""
        for key, plugin in self._instances.items():
            if plugin.is_loaded:
                try:
                    await plugin.unload()
                    logger.info("플러그인 언로드: %s", key)
                except Exception as e:
                    logger.warning("플러그인 언로드 실패 (%s): %s", key, e)
        self._instances.clear()

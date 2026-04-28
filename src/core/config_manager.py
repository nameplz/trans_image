"""YAML 설정 로드/저장 관리자."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from src.core.exceptions import ConfigError
from src.core.plugin_registry_models import PluginEntry, PluginRegistry
from src.core.settings_models import AppSettings, ChatSettings, ProcessingSettings, RenderingSettings
from src.utils.logger import get_logger

logger = get_logger("trans_image.config")

_DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "default_config.yaml"
_PLUGINS_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "plugins.yaml"


class ConfigManager:
    """앱 설정 및 플러그인 레지스트리 로드·조회."""

    def __init__(
        self,
        config_path: Path | None = None,
        plugins_path: Path | None = None,
    ) -> None:
        self._config_path = config_path or _DEFAULT_CONFIG_PATH
        self._plugins_path = plugins_path or _PLUGINS_CONFIG_PATH
        self._config: dict[str, Any] = {}
        self._plugins: dict[str, Any] = {}
        self._app_settings = AppSettings()
        self._processing_settings = ProcessingSettings()
        self._rendering_settings = RenderingSettings()
        self._chat_settings = ChatSettings()
        self._plugin_registry = PluginRegistry()

    def load(self) -> None:
        """설정 파일 로드. 앱 시작 시 한 번 호출."""
        self._config = self._load_yaml(self._config_path)
        self._plugins = self._load_yaml(self._plugins_path)
        self._refresh_all_typed_settings()
        self._plugin_registry = PluginRegistry.from_dict(self._plugins)
        logger.info("설정 로드 완료: %s", self._config_path)

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise ConfigError(f"설정 파일 없음: {path}")
        try:
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"YAML 파싱 오류 ({path}): {e}") from e

    def save(self) -> None:
        """현재 설정을 파일에 저장."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, allow_unicode=True, default_flow_style=False)
        except OSError as e:
            raise ConfigError(f"설정 저장 실패: {e}") from e

    # --- 설정 조회 ---

    def get(self, *keys: str, default: Any = None) -> Any:
        """점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')"""
        node = self._config
        for key in keys:
            if not isinstance(node, dict):
                return default
            node = node.get(key, default)
            if node is default:
                return default
        return node

    def set(self, *keys: str, value: Any) -> None:
        """점 경로로 설정 업데이트."""
        if not keys:
            raise ConfigError("설정 경로가 비어 있습니다.")
        node = self._config
        for key in keys[:-1]:
            child = node.get(key)
            if not isinstance(child, dict):
                child = {}
                node[key] = child
            node = child
        node[keys[-1]] = value
        self._refresh_typed_settings_for_section(keys[0])

    def _refresh_all_typed_settings(self) -> None:
        self._app_settings = AppSettings.from_dict(self._config.get("app"))
        self._processing_settings = ProcessingSettings.from_dict(self._config.get("processing"))
        self._rendering_settings = RenderingSettings.from_dict(self._config.get("rendering"))
        self._chat_settings = ChatSettings.from_dict(self._config.get("chat"))

    def _refresh_typed_settings_for_section(self, section: str) -> None:
        if section == "app":
            self._app_settings = AppSettings.from_dict(self._config.get("app"))
            return
        if section == "processing":
            self._processing_settings = ProcessingSettings.from_dict(self._config.get("processing"))
            return
        if section == "rendering":
            self._rendering_settings = RenderingSettings.from_dict(self._config.get("rendering"))
            return
        if section == "chat":
            self._chat_settings = ChatSettings.from_dict(self._config.get("chat"))

    # --- API 키 조회 ---

    def get_api_key(self, env_var: str, config_path: tuple[str, ...] | None = None) -> str:
        """환경변수 우선, 없으면 config.yaml의 api_keys 섹션 참조.

        YAML 값이 str이 아닌 경우(예: 잘못된 YAML로 dict가 파싱된 경우) 경고를
        로그하고 빈 문자열을 반환한다.
        """
        value = os.environ.get(env_var, "")
        if value:
            return value
        if config_path:
            raw = self.get(*config_path, default="")
        else:
            raw = self.get("api_keys", env_var.lower().replace("_api_key", ""), default="")
        if not isinstance(raw, str):
            logger.warning(
                "api_keys.%s 값이 str이 아닌 %s 타입입니다 (YAML 파싱 오류 가능성). "
                "빈 문자열로 대체합니다. 환경변수 %s 를 설정하거나 "
                "config/default_config.yaml 의 해당 키를 빈 문자열(\"\")로 수정하세요.",
                env_var.lower().replace("_api_key", ""),
                type(raw).__name__,
                env_var,
            )
            return ""
        return raw

    # --- 플러그인 레지스트리 조회 ---

    @property
    def app_settings(self) -> AppSettings:
        return self._app_settings

    @property
    def processing_settings(self) -> ProcessingSettings:
        return self._processing_settings

    @property
    def rendering_settings(self) -> RenderingSettings:
        return self._rendering_settings

    @property
    def chat_settings(self) -> ChatSettings:
        return self._chat_settings

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        for plugin_type in ("ocr", "translators", "agents"):
            if plugin_type not in self._plugin_registry.entries:
                errors.append(f"플러그인 섹션 누락: {plugin_type}")
        return errors

    def get_plugin_configs(self, plugin_type: str) -> list[PluginEntry]:
        """plugin_type: 'ocr' | 'translators' | 'agents'"""
        return self._plugin_registry.get_plugin_configs(plugin_type)

    def get_plugin_config(self, plugin_type: str, plugin_id: str) -> PluginEntry | None:
        return self._plugin_registry.get_plugin_config(plugin_type, plugin_id)

    def is_plugin_enabled(self, plugin_type: str, plugin_id: str) -> bool:
        entry = self.get_plugin_config(plugin_type, plugin_id)
        return bool(entry and entry.enabled)

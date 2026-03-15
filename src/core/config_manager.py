"""YAML 설정 로드/저장 관리자."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from src.core.exceptions import ConfigError
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

    def load(self) -> None:
        """설정 파일 로드. 앱 시작 시 한 번 호출."""
        self._config = self._load_yaml(self._config_path)
        self._plugins = self._load_yaml(self._plugins_path)
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
        node = self._config
        for key in keys[:-1]:
            node = node.setdefault(key, {})
        node[keys[-1]] = value

    # --- API 키 조회 ---

    def get_api_key(self, env_var: str, config_path: tuple[str, ...] | None = None) -> str:
        """환경변수 우선, 없으면 config.yaml의 api_keys 섹션 참조."""
        value = os.environ.get(env_var, "")
        if value:
            return value
        if config_path:
            return self.get(*config_path, default="")
        return self.get("api_keys", env_var.lower().replace("_api_key", ""), default="")

    # --- 플러그인 레지스트리 조회 ---

    def get_plugin_configs(self, plugin_type: str) -> list[dict[str, Any]]:
        """plugin_type: 'ocr' | 'translators' | 'agents'"""
        return self._plugins.get(plugin_type, [])

    def get_plugin_config(self, plugin_type: str, plugin_id: str) -> dict[str, Any] | None:
        for entry in self.get_plugin_configs(plugin_type):
            if entry.get("id") == plugin_id:
                return entry
        return None

    def is_plugin_enabled(self, plugin_type: str, plugin_id: str) -> bool:
        entry = self.get_plugin_config(plugin_type, plugin_id)
        return bool(entry and entry.get("enabled", False))

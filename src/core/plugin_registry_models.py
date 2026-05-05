"""Typed plugin registry models."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.core.exceptions import ConfigError

PluginType = str


@dataclass(frozen=True)
class PluginEntry:
    plugin_type: PluginType
    plugin_id: str
    module: str
    class_name: str
    enabled: bool = True
    config: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, plugin_type: str, data: dict[str, Any]) -> "PluginEntry":
        required = ("id", "module", "class")
        missing = [key for key in required if key not in data]
        if missing:
            raise ConfigError(
                f"플러그인 설정 누락 ({plugin_type}): {', '.join(missing)}"
            )
        plugin_id = data["id"]
        module = data["module"]
        class_name = data["class"]
        enabled = data.get("enabled", True)
        config = data.get("config", {})
        if not isinstance(plugin_id, str) or not isinstance(module, str) or not isinstance(class_name, str):
            raise ConfigError(f"플러그인 설정 타입 오류 ({plugin_type}/{plugin_id})")
        if not isinstance(enabled, bool):
            raise ConfigError(f"플러그인 enabled 타입 오류 ({plugin_type}/{plugin_id})")
        if not isinstance(config, dict):
            raise ConfigError(f"플러그인 config 타입 오류 ({plugin_type}/{plugin_id})")
        return cls(
            plugin_type=plugin_type,
            plugin_id=plugin_id,
            module=module,
            class_name=class_name,
            enabled=enabled,
            config=config,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.plugin_id,
            "enabled": self.enabled,
            "module": self.module,
            "class": self.class_name,
            "config": dict(self.config),
        }


@dataclass(frozen=True)
class PluginRegistry:
    entries: dict[str, list[PluginEntry]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PluginRegistry":
        source = data or {}
        entries: dict[str, list[PluginEntry]] = {}
        for plugin_type, raw_entries in source.items():
            if not isinstance(raw_entries, list):
                raise ConfigError(f"플러그인 목록 타입 오류 ({plugin_type})")
            entries[plugin_type] = [
                PluginEntry.from_dict(plugin_type, entry) for entry in raw_entries
            ]
        return cls(entries=entries)

    def get_plugin_configs(self, plugin_type: str) -> list[PluginEntry]:
        return list(self.entries.get(plugin_type, []))

    def get_plugin_config(self, plugin_type: str, plugin_id: str) -> PluginEntry | None:
        return next(
            (entry for entry in self.get_plugin_configs(plugin_type) if entry.plugin_id == plugin_id),
            None,
        )

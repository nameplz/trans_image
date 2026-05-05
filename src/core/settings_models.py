"""Typed settings models for validated internal config access."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypeVar

from src.core.exceptions import ConfigError

T = TypeVar("T")


def _read_value(
    data: dict[str, Any],
    key: str,
    expected_type: type[T] | tuple[type[Any], ...],
    default: T,
) -> T:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, expected_type):
        expected_name = (
            ", ".join(tp.__name__ for tp in expected_type)
            if isinstance(expected_type, tuple)
            else expected_type.__name__
        )
        raise ConfigError(f"설정 키 '{key}' 타입 오류: expected {expected_name}, got {type(value).__name__}")
    return value


def _read_string_sequence(
    data: dict[str, Any],
    key: str,
    default: tuple[str, ...],
    *,
    max_items: int | None = None,
) -> tuple[str, ...]:
    value = data.get(key, default)
    if value is None:
        return default
    if not isinstance(value, (list, tuple)):
        raise ConfigError(
            f"설정 키 '{key}' 타입 오류: expected list, got {type(value).__name__}"
        )

    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ConfigError(
                f"설정 키 '{key}' 원소 타입 오류: expected non-empty str, got {type(item).__name__}"
            )
        result.append(item)

    if max_items is not None:
        result = result[:max_items]
    return tuple(result)


@dataclass(frozen=True)
class AppSettings:
    name: str = "trans_image"
    version: str = "0.1.0"
    theme: str = "dark"
    language: str = "ko"
    recent_files: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "AppSettings":
        source = data or {}
        return cls(
            name=_read_value(source, "name", str, cls.name),
            version=_read_value(source, "version", str, cls.version),
            theme=_read_value(source, "theme", str, cls.theme),
            language=_read_value(source, "language", str, cls.language),
            recent_files=_read_string_sequence(source, "recent_files", cls.recent_files, max_items=10),
        )


@dataclass(frozen=True)
class ProcessingSettings:
    default_source_lang: str = "auto"
    default_target_lang: str = "ko"
    default_ocr_plugin: str = "easyocr"
    default_translator_plugin: str = "deepl"
    default_agent_plugin: str = "claude"
    use_agent: bool = True
    agent_analyze: bool = True
    agent_validate: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ProcessingSettings":
        source = data or {}
        return cls(
            default_source_lang=_read_value(
                source, "default_source_lang", str, cls.default_source_lang
            ),
            default_target_lang=_read_value(
                source, "default_target_lang", str, cls.default_target_lang
            ),
            default_ocr_plugin=_read_value(
                source, "default_ocr_plugin", str, cls.default_ocr_plugin
            ),
            default_translator_plugin=_read_value(
                source,
                "default_translator_plugin",
                str,
                cls.default_translator_plugin,
            ),
            default_agent_plugin=_read_value(
                source, "default_agent_plugin", str, cls.default_agent_plugin
            ),
            use_agent=_read_value(source, "use_agent", bool, cls.use_agent),
            agent_analyze=_read_value(source, "agent_analyze", bool, cls.agent_analyze),
            agent_validate=_read_value(source, "agent_validate", bool, cls.agent_validate),
        )


@dataclass(frozen=True)
class RenderingSettings:
    auto_font_size: bool = True
    min_font_size: int = 8
    max_font_size: int = 72
    font_fallback: str = "NotoSansCJK"
    line_spacing: float = 1.2

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "RenderingSettings":
        source = data or {}
        return cls(
            auto_font_size=_read_value(source, "auto_font_size", bool, cls.auto_font_size),
            min_font_size=_read_value(source, "min_font_size", int, cls.min_font_size),
            max_font_size=_read_value(source, "max_font_size", int, cls.max_font_size),
            font_fallback=_read_value(source, "font_fallback", str, cls.font_fallback),
            line_spacing=_read_value(
                source, "line_spacing", (int, float), cls.line_spacing
            ),
        )


@dataclass(frozen=True)
class ChatSettings:
    enabled: bool = True
    llm_provider: str = "anthropic"
    llm_model: str = "claude-haiku-4-5-20251001"
    max_history: int = 50
    default_output_suffix: str = "_translated"

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ChatSettings":
        source = data or {}
        return cls(
            enabled=_read_value(source, "enabled", bool, cls.enabled),
            llm_provider=_read_value(source, "llm_provider", str, cls.llm_provider),
            llm_model=_read_value(source, "llm_model", str, cls.llm_model),
            max_history=_read_value(source, "max_history", int, cls.max_history),
            default_output_suffix=_read_value(
                source,
                "default_output_suffix",
                str,
                cls.default_output_suffix,
            ),
        )

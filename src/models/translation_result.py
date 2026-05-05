"""번역 결과 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TranslationResult:
    """단일 텍스트 영역의 번역 결과 (불변)."""

    region_id: str
    source_text: str
    translated_text: str
    source_lang: str
    target_lang: str
    error: str = ""
    confidence: float = 1.0
    plugin_id: str = ""
    latency_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        return not self.error and bool(self.translated_text)

    @property
    def is_empty(self) -> bool:
        return not self.translated_text

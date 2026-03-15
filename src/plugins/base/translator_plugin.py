"""AbstractTranslatorPlugin ABC."""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

from src.models.text_region import TextRegion
from src.models.translation_result import TranslationResult
from src.plugins.base.plugin_base import PluginBase


class AbstractTranslatorPlugin(PluginBase):
    """번역 플러그인 추상 기반 클래스."""

    PLUGIN_TYPE = "translator"

    @abstractmethod
    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str | None = None,
    ) -> TranslationResult:
        """단일 텍스트 번역.

        Args:
            text: 번역할 원문
            source_lang: 원본 언어 코드 (BCP-47). "auto" 이면 자동 감지 요청.
            target_lang: 목표 언어 코드 (BCP-47)
            context: 번역 컨텍스트 힌트 (에이전트가 생성)

        Returns:
            TranslationResult
        """

    @abstractmethod
    async def translate_batch(
        self,
        regions: list[TextRegion],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslationResult]:
        """TextRegion 목록 일괄 번역.

        각 TextRegion의 context_hint를 번역 컨텍스트로 활용.
        반환 목록은 입력과 같은 순서 + 같은 길이여야 함.
        """

    @abstractmethod
    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        """지원하는 (source_lang, target_lang) 쌍 목록.
        source_lang에 "auto" 가 포함되면 자동 감지 지원.
        빈 목록 반환 시 '모든 쌍 지원'으로 간주.
        """

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "translator",
            "plugin_name": self.PLUGIN_NAME,
            "supported_pairs": self.get_supported_language_pairs(),
        }

    def supports_language_pair(self, source: str, target: str) -> bool:
        pairs = self.get_supported_language_pairs()
        if not pairs:
            return True
        return (source, target) in pairs or ("auto", target) in pairs

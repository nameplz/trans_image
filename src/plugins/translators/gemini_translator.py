"""Gemini 번역 플러그인."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.exceptions import PluginConfigError, RateLimitError, TranslationAPIError
from src.models.text_region import TextRegion
from src.models.translation_result import TranslationResult
from src.plugins.base.translator_plugin import AbstractTranslatorPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.translator.gemini")


class GeminiTranslatorPlugin(AbstractTranslatorPlugin):
    PLUGIN_NAME = "gemini"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Google Gemini API 번역 플러그인"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._api_key = self.get_config("api_key", "")
        self._model = self.get_config("model", "gemini-1.5-flash")

    async def load(self) -> None:
        errors = self.validate_config()
        if errors:
            raise PluginConfigError("; ".join(errors))
        try:
            from google import genai
            self._client = genai.Client(api_key=self._api_key)
        except ImportError as e:
            raise PluginConfigError("google-genai 미설치: pip install google-genai") from e
        self._loaded = True
        logger.info("Gemini 플러그인 로드 완료 (모델: %s)", self._model)

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        if not self._api_key:
            return ["Gemini API 키 없음 (GOOGLE_API_KEY 환경변수)"]
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "translator",
            "plugin_name": self.PLUGIN_NAME,
            "context_support": True,
        }

    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        return []  # 다국어 지원

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str | None = None,
    ) -> TranslationResult:
        if not self._loaded:
            await self.load()

        prompt = self._build_prompt(text, source_lang, target_lang, context)
        t0 = time.time()
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model,
                contents=prompt,
            )
            translated = response.text.strip()
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                raise RateLimitError(str(e), 429) from e
            raise TranslationAPIError(str(e)) from e

        return TranslationResult(
            region_id="",
            source_text=text,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_lang,
            plugin_id=self.PLUGIN_NAME,
            latency_ms=(time.time() - t0) * 1000,
        )

    async def translate_batch(
        self,
        regions: list[TextRegion],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslationResult]:
        # 개별 번역을 병렬 처리
        tasks = [
            self.translate(
                r.raw_text, source_lang, target_lang, r.context_hint or None
            )
            for r in regions
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for region, res in zip(regions, raw_results):
            if isinstance(res, Exception):
                results.append(TranslationResult(
                    region_id=region.region_id,
                    source_text=region.raw_text,
                    translated_text="",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    plugin_id=self.PLUGIN_NAME,
                    error=str(res),
                ))
            else:
                import dataclasses
                results.append(dataclasses.replace(res, region_id=region.region_id))
        return results

    def _build_prompt(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str | None,
    ) -> str:
        ctx = f"\n컨텍스트: {context}" if context else ""
        return (
            f"다음 텍스트를 {source_lang}에서 {target_lang}로 번역하세요."
            f"{ctx}\n"
            f"번역문만 출력하고 설명은 생략하세요.\n\n"
            f"원문: {text}\n번역:"
        )

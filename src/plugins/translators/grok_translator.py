"""Grok (xAI) 번역 플러그인 — OpenAI 호환 엔드포인트 사용."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.exceptions import PluginConfigError, RateLimitError, TranslationAPIError
from src.models.text_region import TextRegion
from src.models.translation_result import TranslationResult
from src.plugins.base.translator_plugin import AbstractTranslatorPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.translator.grok")


class GrokTranslatorPlugin(AbstractTranslatorPlugin):
    PLUGIN_NAME = "grok"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "xAI Grok API 번역 플러그인 (OpenAI 호환)"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._api_key = self.get_config("api_key", "")
        self._model = self.get_config("model", "grok-beta")
        self._base_url = self.get_config("base_url", "https://api.x.ai/v1")

    async def load(self) -> None:
        errors = self.validate_config()
        if errors:
            raise PluginConfigError("; ".join(errors))
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
            )
        except ImportError as e:
            raise PluginConfigError("openai 미설치: pip install openai") from e
        self._loaded = True
        logger.info("Grok 플러그인 로드 완료")

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        if not self._api_key:
            return ["Grok API 키 없음 (XAI_API_KEY 환경변수)"]
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {"plugin_type": "translator", "plugin_name": self.PLUGIN_NAME}

    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        return []

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str | None = None,
    ) -> TranslationResult:
        if not self._loaded:
            await self.load()

        ctx = f"\n컨텍스트: {context}" if context else ""
        prompt = (
            f"{source_lang}에서 {target_lang}로 번역하세요.{ctx}\n"
            f"번역문만 출력하세요.\n\n원문: {text}"
        )
        t0 = time.time()
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2048,
            )
            translated = resp.choices[0].message.content.strip()
        except Exception as e:
            if "429" in str(e):
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
        tasks = [
            self.translate(r.raw_text, source_lang, target_lang, r.context_hint or None)
            for r in regions
        ]
        raw = await asyncio.gather(*tasks, return_exceptions=True)
        results = []
        for region, res in zip(regions, raw):
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
                res.region_id = region.region_id
                results.append(res)
        return results

"""Ollama 로컬 LLM 번역 플러그인."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from src.core.exceptions import PluginConfigError, TranslationAPIError
from src.models.text_region import TextRegion
from src.models.translation_result import TranslationResult
from src.plugins.base.translator_plugin import AbstractTranslatorPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.translator.ollama")


class OllamaTranslatorPlugin(AbstractTranslatorPlugin):
    PLUGIN_NAME = "ollama"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Ollama 로컬 LLM 번역 플러그인 (API 키 불필요)"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._base_url = self.get_config("base_url", "http://localhost:11434")
        self._model = self.get_config("model", "llama3.1")

    async def load(self) -> None:
        try:
            import ollama
            self._client = ollama.AsyncClient(host=self._base_url)
        except ImportError as e:
            raise PluginConfigError("ollama 미설치: pip install ollama") from e
        self._loaded = True
        logger.info("Ollama 플러그인 로드 완료 (모델: %s)", self._model)

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        return []  # API 키 불필요

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "translator",
            "plugin_name": self.PLUGIN_NAME,
            "local": True,
        }

    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        return []  # 모델에 따라 다름

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
            f"번역문만 출력하세요.\n\n원문: {text}\n번역:"
        )
        t0 = time.time()
        try:
            response = await self._client.generate(
                model=self._model,
                prompt=prompt,
                stream=False,
            )
            translated = response["response"].strip()
        except Exception as e:
            raise TranslationAPIError(f"Ollama 호출 실패: {e}") from e

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
        # Ollama 로컬이므로 순차 처리 (메모리 부하 방지)
        results = []
        for region in regions:
            try:
                result = await self.translate(
                    region.raw_text, source_lang, target_lang,
                    region.context_hint or None,
                )
                result.region_id = region.region_id
                results.append(result)
            except Exception as e:
                results.append(TranslationResult(
                    region_id=region.region_id,
                    source_text=region.raw_text,
                    translated_text="",
                    source_lang=source_lang,
                    target_lang=target_lang,
                    plugin_id=self.PLUGIN_NAME,
                    error=str(e),
                ))
        return results

"""DeepL 번역 플러그인."""
from __future__ import annotations

import time
from typing import Any

from src.core.exceptions import (
    PluginConfigError,
    RateLimitError,
    TranslationAPIError,
)
from src.models.text_region import TextRegion
from src.models.translation_result import TranslationResult
from src.plugins.base.translator_plugin import AbstractTranslatorPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.translator.deepl")

# DeepL 지원 목표 언어 (일부)
_DEEPL_TARGET_LANGS = [
    "BG", "CS", "DA", "DE", "EL", "EN-GB", "EN-US", "ES", "ET",
    "FI", "FR", "HU", "ID", "IT", "JA", "KO", "LT", "LV", "NB",
    "NL", "PL", "PT-BR", "PT-PT", "RO", "RU", "SK", "SL", "SV",
    "TR", "UK", "ZH",
]

# BCP-47 → DeepL 코드 매핑
_LANG_MAP: dict[str, str] = {
    "ko": "KO",
    "en": "EN-US",
    "ja": "JA",
    "zh": "ZH",
    "fr": "FR",
    "de": "DE",
    "es": "ES",
    "it": "IT",
    "pt": "PT-BR",
    "ru": "RU",
    "nl": "NL",
    "pl": "PL",
    "tr": "TR",
}


class DeepLTranslatorPlugin(AbstractTranslatorPlugin):
    PLUGIN_NAME = "deepl"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "DeepL API 번역 플러그인"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._translator = None
        self._api_key = self.get_config("api_key", "")
        self._free_api = self.get_config("free_api", False)

    async def load(self) -> None:
        errors = self.validate_config()
        if errors:
            raise PluginConfigError("; ".join(errors))
        try:
            import deepl
            server_url = "https://api-free.deepl.com" if self._free_api else None
            self._translator = deepl.Translator(
                self._api_key,
                server_url=server_url,
            )
        except ImportError as e:
            raise PluginConfigError("deepl 패키지 미설치: pip install deepl") from e
        self._loaded = True
        logger.info("DeepL 플러그인 로드 완료")

    async def unload(self) -> None:
        self._translator = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        errors = []
        if not self._api_key:
            errors.append("DeepL API 키 없음 (DEEPL_API_KEY 환경변수 또는 config.yaml)")
        return errors

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "translator",
            "plugin_name": self.PLUGIN_NAME,
            "batch_support": True,
            "context_support": False,
        }

    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        # DeepL은 모든 소스→타겟 지원 (auto 포함)
        return []  # 빈 목록 = 모든 쌍 지원

    def _to_deepl_lang(self, code: str) -> str:
        return _LANG_MAP.get(code.lower(), code.upper())

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str | None = None,
    ) -> TranslationResult:
        if not self._loaded:
            await self.load()

        t0 = time.time()
        target_code = self._to_deepl_lang(target_lang)
        source_code = None if source_lang == "auto" else self._to_deepl_lang(source_lang)

        try:
            result = self._translator.translate_text(
                text,
                source_lang=source_code,
                target_lang=target_code,
            )
            return TranslationResult(
                region_id="",
                source_text=text,
                translated_text=result.text,
                source_lang=source_lang,
                target_lang=target_lang,
                plugin_id=self.PLUGIN_NAME,
                latency_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            status = getattr(e, "http_status_code", None)
            if status == 429:
                raise RateLimitError(str(e), 429) from e
            raise TranslationAPIError(str(e), status) from e

    async def translate_batch(
        self,
        regions: list[TextRegion],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslationResult]:
        if not self._loaded:
            await self.load()

        texts = [r.raw_text for r in regions]
        target_code = self._to_deepl_lang(target_lang)
        source_code = None if source_lang == "auto" else self._to_deepl_lang(source_lang)

        t0 = time.time()
        try:
            results = self._translator.translate_text(
                texts,
                source_lang=source_code,
                target_lang=target_code,
            )
        except Exception as e:
            status = getattr(e, "http_status_code", None)
            if status == 429:
                raise RateLimitError(str(e), 429) from e
            raise TranslationAPIError(str(e), status) from e

        latency = (time.time() - t0) * 1000
        return [
            TranslationResult(
                region_id=region.region_id,
                source_text=region.raw_text,
                translated_text=r.text,
                source_lang=source_lang,
                target_lang=target_lang,
                plugin_id=self.PLUGIN_NAME,
                latency_ms=latency / len(regions),
            )
            for region, r in zip(regions, results)
        ]

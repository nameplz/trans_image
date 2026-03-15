"""Papago (Naver) 번역 플러그인."""
from __future__ import annotations

import asyncio
import time
from typing import Any

import requests

from src.core.exceptions import PluginConfigError, RateLimitError, TranslationAPIError
from src.models.text_region import TextRegion
from src.models.translation_result import TranslationResult
from src.plugins.base.translator_plugin import AbstractTranslatorPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.translator.papago")

_PAPAGO_URL = "https://openapi.naver.com/v1/papago/n2mt"

_SUPPORTED_LANGS = {"ko", "en", "ja", "zh-CN", "zh-TW", "es", "fr", "de", "ru", "pt", "it", "vi", "th", "id"}

_LANG_MAP = {
    "zh": "zh-CN",
    "pt": "pt",
}


class PapagoTranslatorPlugin(AbstractTranslatorPlugin):
    PLUGIN_NAME = "papago"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Naver Papago REST API 번역 플러그인"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client_id = self.get_config("client_id", "")
        self._client_secret = self.get_config("client_secret", "")

    async def load(self) -> None:
        errors = self.validate_config()
        if errors:
            raise PluginConfigError("; ".join(errors))
        self._loaded = True
        logger.info("Papago 플러그인 로드 완료")

    async def unload(self) -> None:
        self._loaded = False

    def validate_config(self) -> list[str]:
        errors = []
        if not self._client_id:
            errors.append("Papago CLIENT_ID 없음 (PAPAGO_CLIENT_ID 환경변수)")
        if not self._client_secret:
            errors.append("Papago CLIENT_SECRET 없음 (PAPAGO_CLIENT_SECRET 환경변수)")
        return errors

    def get_capabilities(self) -> dict[str, Any]:
        return {"plugin_type": "translator", "plugin_name": self.PLUGIN_NAME}

    def get_supported_language_pairs(self) -> list[tuple[str, str]]:
        pairs = []
        langs = list(_SUPPORTED_LANGS)
        for src in langs:
            for tgt in langs:
                if src != tgt:
                    pairs.append((src, tgt))
        return pairs

    def _normalize_lang(self, code: str) -> str:
        return _LANG_MAP.get(code.lower(), code.lower())

    async def translate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        context: str | None = None,
    ) -> TranslationResult:
        if not self._loaded:
            await self.load()

        src = self._normalize_lang(source_lang)
        tgt = self._normalize_lang(target_lang)
        t0 = time.time()

        try:
            response = await asyncio.to_thread(
                self._call_api, text, src, tgt
            )
        except RateLimitError:
            raise
        except Exception as e:
            raise TranslationAPIError(str(e)) from e

        return TranslationResult(
            region_id="",
            source_text=text,
            translated_text=response,
            source_lang=source_lang,
            target_lang=target_lang,
            plugin_id=self.PLUGIN_NAME,
            latency_ms=(time.time() - t0) * 1000,
        )

    def _call_api(self, text: str, source: str, target: str) -> str:
        headers = {
            "X-Naver-Client-Id": self._client_id,
            "X-Naver-Client-Secret": self._client_secret,
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {"source": source, "target": target, "text": text}
        resp = requests.post(_PAPAGO_URL, headers=headers, data=data, timeout=10)
        if resp.status_code == 429:
            raise RateLimitError("Papago 속도 제한", 429)
        if resp.status_code != 200:
            raise TranslationAPIError(f"Papago HTTP {resp.status_code}: {resp.text}", resp.status_code)
        return resp.json()["message"]["result"]["translatedText"]

    async def translate_batch(
        self,
        regions: list[TextRegion],
        source_lang: str,
        target_lang: str,
    ) -> list[TranslationResult]:
        tasks = [
            self.translate(r.raw_text, source_lang, target_lang)
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

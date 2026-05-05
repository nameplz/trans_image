"""Google Gemini 에이전트 플러그인."""
from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator
from typing import Any

from src.core.exceptions import AgentAPIError, PluginConfigError
from src.models.processing_job import ProcessingJob
from src.models.text_region import TextRegion
from src.plugins.base.agent_plugin import AbstractAgentPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.agent.gemini")


class GeminiAgentPlugin(AbstractAgentPlugin):
    PLUGIN_NAME = "gemini"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Google Gemini AI 에이전트 플러그인"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._api_key = self.get_config("api_key", "")
        self._model = self.get_config("model", "gemini-3.1-flash-lite-preview")

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
        logger.info("Gemini 에이전트 로드 완료 (모델: %s)", self._model)

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        if not self._api_key:
            return ["Gemini API 키 없음 (GOOGLE_API_KEY 환경변수)"]
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "agent",
            "plugin_name": self.PLUGIN_NAME,
            "model": self._model,
            "streaming": True,
        }

    async def _call(self, system: str, user_content: str) -> str:
        if not self._loaded:
            await self.load()
        try:
            response = await asyncio.to_thread(
                self._client.models.generate_content,
                model=self._model,
                contents=f"{system}\n\n{user_content}",
            )
            return (response.text or "").strip()
        except Exception as e:
            raise AgentAPIError(f"Gemini API 호출 실패: {e}") from e

    def _extract_json(self, text: str) -> Any:
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"[\[\{].*[\]\}]", text, re.DOTALL)
            if match:
                return json.loads(match.group())
            return None

    async def analyze_ocr_results(
        self,
        regions: list[TextRegion],
        image_description: str | None = None,
    ) -> list[TextRegion]:
        if not regions:
            return regions

        payload = [
            {"id": r.region_id, "text": r.raw_text, "confidence": r.confidence}
            for r in regions
        ]
        desc = f" 이미지 유형: {image_description}." if image_description else ""
        try:
            response = await self._call(
                "OCR 결과 분석 전문가. JSON 배열로 응답.",
                f"OCR 결과 분석.{desc}\n{json.dumps(payload, ensure_ascii=False)}\n"
                "각 항목에 corrected_text, reading_order 포함하여 반환.",
            )
            parsed = self._extract_json(response)
            if isinstance(parsed, list):
                id_map = {item["id"]: item for item in parsed if "id" in item}
                for region in regions:
                    item = id_map.get(region.region_id)
                    if not item:
                        continue
                    corrected_text = item.get("corrected_text")
                    if corrected_text:
                        region.raw_text = corrected_text
                    if "reading_order" in item:
                        region.reading_order = int(item["reading_order"])
        except Exception as e:
            logger.warning("Gemini OCR 분석 실패: %s", e)

        return sorted(regions, key=lambda region: region.reading_order)

    async def generate_translation_context(
        self,
        regions: list[TextRegion],
        job: ProcessingJob,
    ) -> dict[str, str]:
        if not regions:
            return {}

        payload = [{"id": r.region_id, "text": r.raw_text} for r in regions]
        try:
            response = await self._call(
                "번역 컨텍스트 전문가. {region_id: hint} JSON 객체로 응답.",
                f"소스: {job.source_lang}, 목표: {job.target_lang}\n"
                f"{json.dumps(payload, ensure_ascii=False)}\n컨텍스트 힌트 생성.",
            )
            parsed = self._extract_json(response)
            if isinstance(parsed, dict):
                return {key: str(value) for key, value in parsed.items()}
        except Exception as e:
            logger.warning("Gemini 컨텍스트 생성 실패: %s", e)
        return {}

    async def validate_translations(
        self,
        original_regions: list[TextRegion],
        translated_regions: list[TextRegion],
    ) -> list[TextRegion]:
        if not translated_regions:
            return translated_regions

        pairs = [
            {"id": orig.region_id, "original": orig.raw_text, "translated": trans.translated_text}
            for orig, trans in zip(original_regions, translated_regions)
        ]
        try:
            response = await self._call(
                "번역 검증 전문가. 문제 있는 region_id JSON 배열로 응답.",
                f"{json.dumps(pairs, ensure_ascii=False)}\n문제 있는 ID 목록 반환. 없으면 [].",
            )
            parsed = self._extract_json(response)
            if isinstance(parsed, list):
                flagged = set(parsed)
                for region in translated_regions:
                    if region.region_id in flagged:
                        region.needs_review = True
        except Exception as e:
            logger.warning("Gemini 번역 검증 실패: %s", e)
        return translated_regions

    async def stream_analysis(self, prompt: str) -> AsyncIterator[str]:
        response = await self._call("간결하게 응답하세요.", prompt)
        chunk_size = 32
        for start in range(0, len(response), chunk_size):
            yield response[start:start + chunk_size]

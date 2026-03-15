"""OpenAI GPT 에이전트 플러그인."""
from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from typing import Any

from src.core.exceptions import AgentAPIError, PluginConfigError
from src.models.processing_job import ProcessingJob
from src.models.text_region import TextRegion
from src.plugins.base.agent_plugin import AbstractAgentPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.agent.openai")


class OpenAIAgentPlugin(AbstractAgentPlugin):
    PLUGIN_NAME = "openai"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "OpenAI GPT-4o 에이전트 플러그인"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._api_key = self.get_config("api_key", "")
        self._model = self.get_config("model", "gpt-4o")
        self._max_tokens = int(self.get_config("max_tokens", 4096))

    async def load(self) -> None:
        errors = self.validate_config()
        if errors:
            raise PluginConfigError("; ".join(errors))
        try:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key)
        except ImportError as e:
            raise PluginConfigError("openai 미설치: pip install openai") from e
        self._loaded = True
        logger.info("OpenAI 에이전트 로드 완료 (모델: %s)", self._model)

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        if not self._api_key:
            return ["OpenAI API 키 없음 (OPENAI_API_KEY 환경변수)"]
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {"plugin_type": "agent", "plugin_name": self.PLUGIN_NAME, "model": self._model}

    async def _call(self, system: str, user_content: str) -> str:
        if not self._loaded:
            await self.load()
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
            )
            return resp.choices[0].message.content
        except Exception as e:
            raise AgentAPIError(f"OpenAI API 호출 실패: {e}") from e

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
        data = [
            {"id": r.region_id, "text": r.raw_text, "confidence": r.confidence}
            for r in regions
        ]
        desc = f" 이미지 유형: {image_description}." if image_description else ""
        resp = await self._call(
            "OCR 결과 분석 전문가. JSON 배열로 응답.",
            f"OCR 결과 분석.{desc}\n{json.dumps(data, ensure_ascii=False)}\n"
            "각 항목에 corrected_text, reading_order 포함하여 반환.",
        )
        try:
            parsed = self._extract_json(resp)
            if isinstance(parsed, list):
                id_map = {i["id"]: i for i in parsed if "id" in i}
                for r in regions:
                    if r.region_id in id_map:
                        item = id_map[r.region_id]
                        if item.get("corrected_text"):
                            r.raw_text = item["corrected_text"]
                        if "reading_order" in item:
                            r.reading_order = int(item["reading_order"])
        except Exception as e:
            logger.warning("OpenAI OCR 분석 실패: %s", e)
        return sorted(regions, key=lambda r: r.reading_order)

    async def generate_translation_context(
        self,
        regions: list[TextRegion],
        job: ProcessingJob,
    ) -> dict[str, str]:
        if not regions:
            return {}
        data = [{"id": r.region_id, "text": r.raw_text} for r in regions]
        resp = await self._call(
            "번역 컨텍스트 전문가. {region_id: hint} JSON 객체로 응답.",
            f"소스: {job.source_lang}, 목표: {job.target_lang}\n"
            f"{json.dumps(data, ensure_ascii=False)}\n컨텍스트 힌트 생성.",
        )
        try:
            parsed = self._extract_json(resp)
            if isinstance(parsed, dict):
                return {k: str(v) for k, v in parsed.items()}
        except Exception as e:
            logger.warning("OpenAI 컨텍스트 생성 실패: %s", e)
        return {}

    async def validate_translations(
        self,
        original_regions: list[TextRegion],
        translated_regions: list[TextRegion],
    ) -> list[TextRegion]:
        pairs = [
            {"id": o.region_id, "original": o.raw_text, "translated": t.translated_text}
            for o, t in zip(original_regions, translated_regions)
        ]
        resp = await self._call(
            "번역 검증 전문가. 문제 있는 region_id JSON 배열로 응답.",
            f"{json.dumps(pairs, ensure_ascii=False)}\n문제 있는 ID 목록 반환. 없으면 [].",
        )
        try:
            parsed = self._extract_json(resp)
            if isinstance(parsed, list):
                flagged = set(parsed)
                for r in translated_regions:
                    if r.region_id in flagged:
                        r.needs_review = True
        except Exception as e:
            logger.warning("OpenAI 번역 검증 실패: %s", e)
        return translated_regions

    async def stream_analysis(self, prompt: str) -> AsyncIterator[str]:
        if not self._loaded:
            await self.load()
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except Exception as e:
            raise AgentAPIError(f"OpenAI 스트리밍 실패: {e}") from e

"""Ollama 로컬 LLM 에이전트 플러그인."""
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

logger = get_logger("trans_image.agent.ollama")


class OllamaAgentPlugin(AbstractAgentPlugin):
    PLUGIN_NAME = "ollama"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Ollama 로컬 LLM 에이전트 플러그인 (API 키 불필요)"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._base_url = self.get_config("base_url", "http://localhost:11434")
        self._model = self.get_config("model", "llama3.1")
        self._max_tokens = int(self.get_config("max_tokens", 4096))

    async def load(self) -> None:
        try:
            import ollama
            self._client = ollama.AsyncClient(host=self._base_url)
        except ImportError as e:
            raise PluginConfigError("ollama 미설치: pip install ollama") from e
        self._loaded = True
        logger.info("Ollama 에이전트 로드 완료 (모델: %s)", self._model)

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {"plugin_type": "agent", "plugin_name": self.PLUGIN_NAME, "local": True}

    async def _call(self, system: str, user_content: str) -> str:
        if not self._loaded:
            await self.load()
        try:
            resp = await self._client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_content},
                ],
            )
            return resp["message"]["content"]
        except Exception as e:
            raise AgentAPIError(f"Ollama 호출 실패: {e}") from e

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
        data = [{"id": r.region_id, "text": r.raw_text} for r in regions]
        try:
            resp = await self._call(
                "OCR 분석 전문가. JSON 배열로 응답.",
                f"{json.dumps(data, ensure_ascii=False)}\ncorrected_text, reading_order 포함 반환.",
            )
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
            logger.warning("Ollama OCR 분석 실패: %s", e)
        return sorted(regions, key=lambda r: r.reading_order)

    async def generate_translation_context(
        self,
        regions: list[TextRegion],
        job: ProcessingJob,
    ) -> dict[str, str]:
        if not regions:
            return {}
        data = [{"id": r.region_id, "text": r.raw_text} for r in regions]
        try:
            resp = await self._call(
                "번역 컨텍스트 전문가. JSON 객체로 응답.",
                f"소스: {job.source_lang}, 목표: {job.target_lang}\n"
                f"{json.dumps(data, ensure_ascii=False)}\n컨텍스트 힌트 반환.",
            )
            parsed = self._extract_json(resp)
            if isinstance(parsed, dict):
                return {k: str(v) for k, v in parsed.items()}
        except Exception as e:
            logger.warning("Ollama 컨텍스트 생성 실패: %s", e)
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
        try:
            resp = await self._call(
                "번역 검증. 문제 ID JSON 배열 반환.",
                f"{json.dumps(pairs, ensure_ascii=False)}\n문제 있는 ID 목록. 없으면 [].",
            )
            parsed = self._extract_json(resp)
            if isinstance(parsed, list):
                flagged = set(parsed)
                for r in translated_regions:
                    if r.region_id in flagged:
                        r.needs_review = True
        except Exception as e:
            logger.warning("Ollama 번역 검증 실패: %s", e)
        return translated_regions

    async def stream_analysis(self, prompt: str) -> AsyncIterator[str]:
        if not self._loaded:
            await self.load()
        try:
            async for chunk in await self._client.generate(
                model=self._model,
                prompt=prompt,
                stream=True,
            ):
                if chunk.get("response"):
                    yield chunk["response"]
        except Exception as e:
            raise AgentAPIError(f"Ollama 스트리밍 실패: {e}") from e

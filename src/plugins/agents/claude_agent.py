"""Claude (Anthropic) 에이전트 플러그인."""
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

logger = get_logger("trans_image.agent.claude")

_ANALYZE_SYSTEM = """당신은 OCR 결과 분석 전문가입니다.
이미지에서 추출된 텍스트 영역 목록을 분석하여:
1. OCR 오류 교정 (명백한 오타, 문자 혼동)
2. 올바른 읽기 순서 부여 (만화는 오른쪽→왼쪽, 문서는 위→아래)
3. 병합이 필요한 분리된 영역 표시
JSON 배열 형식으로 응답하세요."""

_CONTEXT_SYSTEM = """당신은 번역 컨텍스트 전문가입니다.
각 텍스트 영역에 대해 번역 품질을 높이는 컨텍스트 힌트를 생성하세요.
장르, 말투, 고유명사, 문맥 등을 고려하세요.
{region_id: hint_string} JSON 객체로 응답하세요."""

_VALIDATE_SYSTEM = """당신은 번역 품질 검증 전문가입니다.
원문과 번역문을 비교하여:
1. 번역 누락 또는 미완성 항목
2. 언어 불일치 (목표 언어가 아닌 경우)
3. 의미 왜곡이 의심되는 항목
문제가 있는 region_id 목록을 JSON 배열로 응답하세요."""


class ClaudeAgentPlugin(AbstractAgentPlugin):
    PLUGIN_NAME = "claude"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "Anthropic Claude AI 에이전트 플러그인"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._client = None
        self._api_key = self.get_config("api_key", "")
        self._model = self.get_config("model", "claude-sonnet-4-6")
        self._max_tokens = int(self.get_config("max_tokens", 4096))

    async def load(self) -> None:
        errors = self.validate_config()
        if errors:
            raise PluginConfigError("; ".join(errors))
        try:
            import anthropic
            self._client = anthropic.AsyncAnthropic(api_key=self._api_key)
        except ImportError as e:
            raise PluginConfigError("anthropic 미설치: pip install anthropic") from e
        self._loaded = True
        logger.info("Claude 에이전트 로드 완료 (모델: %s)", self._model)

    async def unload(self) -> None:
        self._client = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        if not self._api_key:
            return ["Claude API 키 없음 (ANTHROPIC_API_KEY 환경변수)"]
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "agent",
            "plugin_name": self.PLUGIN_NAME,
            "model": self._model,
            "streaming": True,
        }

    async def _call(self, system: str, user_content: str) -> str:
        """단순 Claude API 호출."""
        if not self._loaded:
            await self.load()
        try:
            message = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": user_content}],
            )
            return message.content[0].text
        except Exception as e:
            raise AgentAPIError(f"Claude API 호출 실패: {e}") from e

    def _extract_json(self, text: str) -> Any:
        """응답 텍스트에서 JSON 추출."""
        # 코드 블록 제거
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 첫 번째 JSON 구조 추출 시도
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

        regions_data = [
            {
                "id": r.region_id,
                "text": r.raw_text,
                "confidence": r.confidence,
                "bbox": {"x": r.bbox.x, "y": r.bbox.y, "w": r.bbox.width, "h": r.bbox.height},
            }
            for r in regions
        ]
        desc = f"\n이미지 유형: {image_description}" if image_description else ""
        user_msg = (
            f"OCR 결과를 분석하세요.{desc}\n\n"
            f"영역 목록:\n{json.dumps(regions_data, ensure_ascii=False, indent=2)}\n\n"
            f"각 영역의 corrected_text와 reading_order를 포함하여 JSON 배열로 반환하세요."
        )
        try:
            response = await self._call(_ANALYZE_SYSTEM, user_msg)
            parsed = self._extract_json(response)
            if isinstance(parsed, list):
                id_to_result = {item["id"]: item for item in parsed if "id" in item}
                for region in regions:
                    if region.region_id in id_to_result:
                        item = id_to_result[region.region_id]
                        if "corrected_text" in item and item["corrected_text"]:
                            region.raw_text = item["corrected_text"]
                        if "reading_order" in item:
                            region.reading_order = int(item["reading_order"])
        except Exception as e:
            logger.warning("OCR 분석 실패, 원본 사용: %s", e)

        return sorted(regions, key=lambda r: r.reading_order)

    async def generate_translation_context(
        self,
        regions: list[TextRegion],
        job: ProcessingJob,
    ) -> dict[str, str]:
        if not regions:
            return {}

        regions_data = [
            {"id": r.region_id, "text": r.raw_text, "order": r.reading_order}
            for r in regions
        ]
        user_msg = (
            f"소스 언어: {job.source_lang}, 목표 언어: {job.target_lang}\n\n"
            f"영역 목록:\n{json.dumps(regions_data, ensure_ascii=False, indent=2)}\n\n"
            f"각 region_id에 대한 번역 컨텍스트 힌트를 JSON 객체로 반환하세요."
        )
        try:
            response = await self._call(_CONTEXT_SYSTEM, user_msg)
            parsed = self._extract_json(response)
            if isinstance(parsed, dict):
                return {k: str(v) for k, v in parsed.items()}
        except Exception as e:
            logger.warning("컨텍스트 생성 실패: %s", e)
        return {}

    async def validate_translations(
        self,
        original_regions: list[TextRegion],
        translated_regions: list[TextRegion],
    ) -> list[TextRegion]:
        if not translated_regions:
            return translated_regions

        pairs = [
            {
                "id": orig.region_id,
                "original": orig.raw_text,
                "translated": trans.translated_text,
            }
            for orig, trans in zip(original_regions, translated_regions)
        ]
        user_msg = (
            f"번역 쌍을 검증하세요:\n"
            f"{json.dumps(pairs, ensure_ascii=False, indent=2)}\n\n"
            f"문제가 있는 region_id 목록을 JSON 배열로 반환하세요. 문제없으면 []."
        )
        try:
            response = await self._call(_VALIDATE_SYSTEM, user_msg)
            parsed = self._extract_json(response)
            if isinstance(parsed, list):
                flagged = set(parsed)
                for region in translated_regions:
                    if region.region_id in flagged:
                        region.needs_review = True
        except Exception as e:
            logger.warning("번역 검증 실패: %s", e)
        return translated_regions

    async def stream_analysis(self, prompt: str) -> AsyncIterator[str]:
        if not self._loaded:
            await self.load()
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            raise AgentAPIError(f"Claude 스트리밍 실패: {e}") from e

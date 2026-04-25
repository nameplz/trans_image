"""에이전트 플러그인 단위 테스트 (Claude, OpenAI, Gemini, Ollama)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.processing_job import ProcessingJob
from src.models.text_region import BoundingBox, TextRegion


def make_region(text: str = "Hello", order: int = 0) -> TextRegion:
    r = TextRegion(
        raw_text=text,
        bbox=BoundingBox(x=0, y=order * 30, width=100, height=25),
        confidence=0.9,
    )
    r.reading_order = order
    return r


def make_job() -> ProcessingJob:
    return ProcessingJob(target_lang="ko", source_lang="en")


# ── Claude ─────────────────────────────────────────────────────────────────────

class TestClaudeAgentPlugin:
    async def test_analyze_ocr_results_returns_regions(self):
        """analyze_ocr_results → region 목록 반환 (reading_order 설정됨)."""
        from src.plugins.agents.claude_agent import ClaudeAgentPlugin

        regions = [make_region("Hello", 0), make_region("World", 1)]
        response_json = json.dumps([
            {"id": regions[0].region_id, "corrected_text": "Hello!", "reading_order": 0},
            {"id": regions[1].region_id, "corrected_text": "World!", "reading_order": 1},
        ])

        plugin = ClaudeAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._client = MagicMock()
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.analyze_ocr_results(regions)
        assert len(result) == 2
        assert all(isinstance(r, TextRegion) for r in result)

    async def test_generate_translation_context_returns_dict(self):
        """generate_translation_context → {region_id: str} 딕셔너리 반환."""
        from src.plugins.agents.claude_agent import ClaudeAgentPlugin

        regions = [make_region("Hello"), make_region("World")]
        job = make_job()
        context_map = {r.region_id: f"context for {r.raw_text}" for r in regions}
        response_json = json.dumps(context_map)

        plugin = ClaudeAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.generate_translation_context(regions, job)
        assert isinstance(result, dict)
        # 반환 딕셔너리는 str 값
        for v in result.values():
            assert isinstance(v, str)

    async def test_validate_translations_flags_needs_review(self):
        """validate_translations → needs_review 플래그 업데이트된 regions 반환."""
        from src.plugins.agents.claude_agent import ClaudeAgentPlugin

        orig = [make_region("Hello"), make_region("World")]
        # trans는 orig와 동일한 region_id 사용 (파이프라인 실제 동작과 동일)
        trans = [
            TextRegion(region_id=orig[0].region_id, raw_text="Hello", translated_text="안녕",
                       confidence=0.9, bbox=BoundingBox(x=0, y=0, width=100, height=25)),
            TextRegion(region_id=orig[1].region_id, raw_text="World", translated_text="세계",
                       confidence=0.9, bbox=BoundingBox(x=0, y=30, width=100, height=25)),
        ]

        # 첫 번째 region에 문제 있다고 응답
        flagged_ids = [orig[0].region_id]
        response_json = json.dumps(flagged_ids)

        plugin = ClaudeAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.validate_translations(orig, trans)
        assert result[0].needs_review is True
        assert result[1].needs_review is False

    async def test_analyze_empty_regions_returns_empty(self):
        """빈 regions → 그대로 반환."""
        from src.plugins.agents.claude_agent import ClaudeAgentPlugin

        plugin = ClaudeAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        result = await plugin.analyze_ocr_results([])
        assert result == []


# ── OpenAI ────────────────────────────────────────────────────────────────────

class TestOpenAIAgentPlugin:
    async def test_analyze_ocr_results_returns_regions(self):
        """analyze_ocr_results → region 목록 반환."""
        from src.plugins.agents.openai_agent import OpenAIAgentPlugin

        regions = [make_region("Text1", 0), make_region("Text2", 1)]
        response_json = json.dumps([
            {"id": regions[0].region_id, "corrected_text": "Text1!", "reading_order": 1},
            {"id": regions[1].region_id, "corrected_text": "Text2!", "reading_order": 0},
        ])

        plugin = OpenAIAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.analyze_ocr_results(regions)
        assert len(result) == 2

    async def test_generate_translation_context_returns_dict(self):
        """generate_translation_context → dict 반환."""
        from src.plugins.agents.openai_agent import OpenAIAgentPlugin

        regions = [make_region("Hello")]
        job = make_job()
        response_json = json.dumps({regions[0].region_id: "말풍선 텍스트"})

        plugin = OpenAIAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.generate_translation_context(regions, job)
        assert isinstance(result, dict)

    async def test_validate_translations_returns_regions(self):
        """validate_translations → regions 목록 반환."""
        from src.plugins.agents.openai_agent import OpenAIAgentPlugin

        orig = [make_region("Hello")]
        trans = [make_region("안녕")]
        trans[0].translated_text = "안녕"

        plugin = OpenAIAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value="[]")

        result = await plugin.validate_translations(orig, trans)
        assert len(result) == 1
        assert result[0].needs_review is False

    async def test_validate_config_no_key(self):
        """API 키 없음 → validate_config 오류 반환."""
        from src.plugins.agents.openai_agent import OpenAIAgentPlugin
        plugin = OpenAIAgentPlugin(config={"api_key": ""})
        errors = plugin.validate_config()
        assert len(errors) > 0


# ── Gemini ────────────────────────────────────────────────────────────────────

class TestGeminiAgentPlugin:
    async def test_analyze_ocr_results_returns_regions(self):
        """analyze_ocr_results → region 목록 반환."""
        from src.plugins.agents.gemini_agent import GeminiAgentPlugin

        regions = [make_region("Text1", 0), make_region("Text2", 1)]
        response_json = json.dumps([
            {"id": regions[0].region_id, "corrected_text": "Text1!", "reading_order": 1},
            {"id": regions[1].region_id, "corrected_text": "Text2!", "reading_order": 0},
        ])

        plugin = GeminiAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.analyze_ocr_results(regions)
        assert len(result) == 2
        assert result[0].reading_order == 0

    async def test_generate_translation_context_returns_dict(self):
        """generate_translation_context → dict 반환."""
        from src.plugins.agents.gemini_agent import GeminiAgentPlugin

        regions = [make_region("Hello")]
        job = make_job()
        response_json = json.dumps({regions[0].region_id: "말풍선 텍스트"})

        plugin = GeminiAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.generate_translation_context(regions, job)
        assert isinstance(result, dict)
        assert result[regions[0].region_id] == "말풍선 텍스트"

    async def test_validate_translations_flags_needs_review(self):
        """validate_translations → needs_review 플래그 업데이트."""
        from src.plugins.agents.gemini_agent import GeminiAgentPlugin

        orig = [make_region("Hello"), make_region("World")]
        trans = [
            TextRegion(
                region_id=orig[0].region_id,
                raw_text="Hello",
                translated_text="안녕",
                confidence=0.9,
                bbox=BoundingBox(x=0, y=0, width=100, height=25),
            ),
            TextRegion(
                region_id=orig[1].region_id,
                raw_text="World",
                translated_text="세계",
                confidence=0.9,
                bbox=BoundingBox(x=0, y=30, width=100, height=25),
            ),
        ]

        plugin = GeminiAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=json.dumps([orig[1].region_id]))

        result = await plugin.validate_translations(orig, trans)
        assert result[0].needs_review is False
        assert result[1].needs_review is True

    async def test_stream_analysis_yields_text_chunks(self):
        """stream_analysis → 모델 응답 텍스트를 청크로 분할 yield."""
        from src.plugins.agents.gemini_agent import GeminiAgentPlugin

        plugin = GeminiAgentPlugin(config={"api_key": "test-key"})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value="abcdef")

        chunks = [chunk async for chunk in plugin.stream_analysis("prompt")]
        assert "".join(chunks) == "abcdef"

    def test_validate_config_no_key(self):
        """API 키 없음 → validate_config 오류 반환."""
        from src.plugins.agents.gemini_agent import GeminiAgentPlugin

        plugin = GeminiAgentPlugin(config={"api_key": ""})
        errors = plugin.validate_config()
        assert len(errors) > 0


# ── Ollama ────────────────────────────────────────────────────────────────────

class TestOllamaAgentPlugin:
    async def test_analyze_ocr_results_returns_regions(self):
        """analyze_ocr_results → region 목록 반환."""
        from src.plugins.agents.ollama_agent import OllamaAgentPlugin

        regions = [make_region("Text1")]
        response_json = json.dumps([
            {"id": regions[0].region_id, "corrected_text": "Text1!", "reading_order": 0},
        ])

        plugin = OllamaAgentPlugin(config={})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.analyze_ocr_results(regions)
        assert len(result) == 1

    async def test_generate_translation_context_returns_dict(self):
        """generate_translation_context → dict 반환."""
        from src.plugins.agents.ollama_agent import OllamaAgentPlugin

        regions = [make_region("Hello")]
        job = make_job()
        response_json = json.dumps({regions[0].region_id: "컨텍스트"})

        plugin = OllamaAgentPlugin(config={})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.generate_translation_context(regions, job)
        assert isinstance(result, dict)

    async def test_validate_translations_flags_needs_review(self):
        """validate_translations → needs_review 플래그 업데이트."""
        from src.plugins.agents.ollama_agent import OllamaAgentPlugin

        orig = [make_region("Hello"), make_region("World")]
        # trans는 orig와 동일한 region_id 사용
        trans = [
            TextRegion(region_id=orig[0].region_id, raw_text="Hello", translated_text="안녕",
                       confidence=0.9, bbox=BoundingBox(x=0, y=0, width=100, height=25)),
            TextRegion(region_id=orig[1].region_id, raw_text="World", translated_text="세계",
                       confidence=0.9, bbox=BoundingBox(x=0, y=30, width=100, height=25)),
        ]

        flagged = [orig[1].region_id]
        response_json = json.dumps(flagged)

        plugin = OllamaAgentPlugin(config={})
        plugin._loaded = True
        plugin._call = AsyncMock(return_value=response_json)

        result = await plugin.validate_translations(orig, trans)
        assert result[0].needs_review is False
        assert result[1].needs_review is True

    def test_validate_config_always_empty(self):
        """Ollama는 API 키 불필요 → 항상 빈 목록."""
        from src.plugins.agents.ollama_agent import OllamaAgentPlugin
        plugin = OllamaAgentPlugin(config={})
        assert plugin.validate_config() == []

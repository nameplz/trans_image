"""Pipeline.run() 단위 테스트."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import cv2
import numpy as np
import pytest

from src.core.exceptions import PipelineError
from src.core.pipeline import Pipeline
from src.models.processing_job import JobStatus, ProcessingJob
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def make_translation_result(region: TextRegion, text: str = "번역됨") -> TranslationResult:
    return TranslationResult(
        region_id=region.region_id,
        source_text=region.raw_text,
        translated_text=text,
        source_lang="en",
        target_lang="ko",
    )


def make_dummy_image(tmp_path: Path) -> Path:
    """실제 PNG 파일 생성."""
    img_path = tmp_path / "test.png"
    img = np.zeros((100, 200, 3), dtype=np.uint8)
    cv2.imwrite(str(img_path), img)
    return img_path


def make_regions(n: int = 2) -> list[TextRegion]:
    return [
        TextRegion(
            raw_text=f"Text {i}",
            bbox=BoundingBox(x=10 * i, y=10, width=50, height=20),
            confidence=0.9,
        )
        for i in range(n)
    ]


# ── 픽스처 ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_pipeline(mock_config):
    """의존성이 모두 mock된 Pipeline 인스턴스."""
    plugin_manager = MagicMock()

    # OCR 플러그인 mock
    ocr_plugin = MagicMock()
    ocr_plugin.is_loaded = True
    regions = make_regions(2)
    ocr_plugin.detect_regions = AsyncMock(return_value=regions)
    plugin_manager.get_ocr_plugin.return_value = ocr_plugin

    # 번역 플러그인 mock
    translator_plugin = MagicMock()
    translator_plugin.is_loaded = True

    async def translate_batch_side(regs, src, tgt):
        return [make_translation_result(r) for r in regs]

    translator_plugin.translate_batch = AsyncMock(side_effect=translate_batch_side)
    plugin_manager.get_translator_plugin.return_value = translator_plugin

    # 에이전트 플러그인 mock
    agent_plugin = MagicMock()
    agent_plugin.is_loaded = True
    agent_plugin.analyze_ocr_results = AsyncMock(side_effect=lambda regs, **kw: regs)
    agent_plugin.generate_translation_context = AsyncMock(return_value={})
    agent_plugin.validate_translations = AsyncMock(side_effect=lambda orig, trans: trans)
    plugin_manager.get_agent_plugin.return_value = agent_plugin

    pipeline = Pipeline(config=mock_config, plugin_manager=plugin_manager)

    # 내부 서비스 mock
    pipeline._ocr_service = MagicMock()
    pipeline._ocr_service.normalize.side_effect = lambda r: r

    pipeline._lang_service = MagicMock()
    pipeline._lang_service.detect.return_value = "en"

    dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
    pipeline._inpainting_service = MagicMock()
    pipeline._inpainting_service.remove_text = AsyncMock(return_value=dummy_image)

    pipeline._rendering_service = MagicMock()
    pipeline._rendering_service.render = AsyncMock(return_value=dummy_image)

    pipeline._font_service = MagicMock()

    return pipeline, plugin_manager, agent_plugin


class TestPipelineSuccess:
    async def test_full_pipeline_complete_status(self, mock_pipeline, tmp_path):
        """전체 파이프라인 정상 실행 → job.status == COMPLETE."""
        pipeline, _, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        await pipeline.run(job)
        assert job.status == JobStatus.COMPLETE

    async def test_cancelled_error_sets_cancelled(self, mock_pipeline, tmp_path):
        """CancelledError 발생 → job.status == CANCELLED."""
        pipeline, plugin_manager, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        # OCR에서 CancelledError 발생 시뮬레이션
        ocr_plugin = MagicMock()
        ocr_plugin.is_loaded = True
        ocr_plugin.detect_regions = AsyncMock(side_effect=asyncio.CancelledError())
        plugin_manager.get_ocr_plugin.return_value = ocr_plugin

        with pytest.raises(asyncio.CancelledError):
            await pipeline.run(job)
        assert job.status == JobStatus.CANCELLED

    async def test_ocr_failure_sets_failed(self, mock_pipeline, tmp_path):
        """OCR 실패 (예외) → job.status == FAILED."""
        pipeline, plugin_manager, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        ocr_plugin = MagicMock()
        ocr_plugin.is_loaded = True
        ocr_plugin.detect_regions = AsyncMock(side_effect=RuntimeError("OCR 오류"))
        plugin_manager.get_ocr_plugin.return_value = ocr_plugin

        with pytest.raises(PipelineError):
            await pipeline.run(job)
        assert job.status == JobStatus.FAILED

    async def test_translation_failure_sets_failed(self, mock_pipeline, tmp_path):
        """번역 실패 → job.status == FAILED."""
        pipeline, plugin_manager, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        translator_plugin = MagicMock()
        translator_plugin.is_loaded = True
        translator_plugin.translate_batch = AsyncMock(side_effect=RuntimeError("번역 오류"))
        plugin_manager.get_translator_plugin.return_value = translator_plugin

        with pytest.raises(PipelineError):
            await pipeline.run(job)
        assert job.status == JobStatus.FAILED


class TestPipelineAgent:
    async def test_use_agent_true_calls_analyze(self, mock_pipeline, tmp_path):
        """use_agent=True → 에이전트의 analyze_ocr_results 호출."""
        pipeline, _, agent_plugin = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=True)

        await pipeline.run(job)
        agent_plugin.analyze_ocr_results.assert_called_once()

    async def test_use_agent_false_skips_agent(self, mock_pipeline, tmp_path):
        """use_agent=False → 에이전트 메서드 미호출."""
        pipeline, _, agent_plugin = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        # use_agent=False이면 if job.use_agent and ... 조건이 False
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        await pipeline.run(job)
        agent_plugin.analyze_ocr_results.assert_not_called()

    async def test_validate_translations_called_with_agent(self, mock_pipeline, tmp_path):
        """use_agent=True + agent_validate=True → validate_translations 호출."""
        pipeline, _, agent_plugin = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=True)

        # conftest mock_config는 agent_analyze=True, agent_validate=True를 반환
        await pipeline.run(job)
        agent_plugin.validate_translations.assert_called_once()


class TestPipelineProgressCallback:
    async def test_progress_callback_called_multiple_times(self, mock_pipeline, tmp_path):
        """progress_cb 최소 3회 이상 호출됨."""
        pipeline, _, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        calls = []
        await pipeline.run(job, progress_cb=lambda j, msg: calls.append(msg))
        assert len(calls) >= 3


class TestPipelineEdgeCases:
    async def test_zero_ocr_regions_completes(self, mock_pipeline, tmp_path):
        """OCR 결과 0개 → 정상 완료 (번역 스킵)."""
        pipeline, plugin_manager, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        ocr_plugin = MagicMock()
        ocr_plugin.is_loaded = True
        ocr_plugin.detect_regions = AsyncMock(return_value=[])
        plugin_manager.get_ocr_plugin.return_value = ocr_plugin

        await pipeline.run(job)
        assert job.status == JobStatus.COMPLETE

    async def test_nonexistent_file_raises(self, mock_pipeline, tmp_path):
        """존재하지 않는 파일 → PipelineError 발생."""
        pipeline, _, _ = mock_pipeline
        job = ProcessingJob(
            input_path=tmp_path / "nonexistent.png",
            target_lang="ko",
            use_agent=False,
        )
        with pytest.raises(PipelineError):
            await pipeline.run(job)
        assert job.status == JobStatus.FAILED

    async def test_output_path_saves_file(self, mock_pipeline, tmp_path):
        """output_path 설정 + 더미 이미지 → 파일 저장됨."""
        pipeline, _, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        output_path = tmp_path / "output.png"
        job = ProcessingJob(
            input_path=img_path,
            output_path=output_path,
            target_lang="ko",
            use_agent=False,
        )

        # render가 실제 저장 가능한 이미지를 반환하도록 설정
        real_image = np.zeros((100, 200, 3), dtype=np.uint8)
        pipeline._rendering_service.render = AsyncMock(return_value=real_image)

        await pipeline.run(job)
        assert output_path.exists()

    async def test_failed_regions_count(self, mock_pipeline, tmp_path):
        """번역 실패 region → failed_regions 카운트 증가."""
        pipeline, plugin_manager, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)

        regions = make_regions(2)
        ocr_plugin = MagicMock()
        ocr_plugin.is_loaded = True
        ocr_plugin.detect_regions = AsyncMock(return_value=regions)
        plugin_manager.get_ocr_plugin.return_value = ocr_plugin

        # 첫 번째만 성공, 나머지 실패
        translator_plugin = MagicMock()
        translator_plugin.is_loaded = True
        translator_plugin.translate_batch = AsyncMock(return_value=[
            TranslationResult(
                region_id=regions[0].region_id,
                source_text="Text 0",
                translated_text="번역됨",
                source_lang="en",
                target_lang="ko",
            ),
            TranslationResult(
                region_id=regions[1].region_id,
                source_text="Text 1",
                translated_text="",
                source_lang="en",
                target_lang="ko",
                error="실패",
            ),
        ])
        plugin_manager.get_translator_plugin.return_value = translator_plugin

        await pipeline.run(job)
        assert job.failed_regions == 1
        assert job.translated_regions == 1


class TestPipelinePreview:
    async def test_preview_region_translation_does_not_mutate_job(self, mock_pipeline, tmp_path):
        pipeline, _, _ = mock_pipeline
        img_path = make_dummy_image(tmp_path)
        regions = make_regions(2)
        job = ProcessingJob(input_path=img_path, target_lang="ko", use_agent=False)
        job.original_image = np.zeros((100, 200, 3), dtype=np.uint8)
        job.regions = regions

        preview = np.ones((100, 200, 3), dtype=np.uint8)
        pipeline._rendering_service.render = AsyncMock(return_value=preview)

        result = await pipeline.preview_region_translation(job, regions[0].region_id, "draft")

        assert result is preview
        assert job.regions[0].translated_text == ""
        render_regions = pipeline._rendering_service.render.await_args.args[1]
        assert render_regions[0].translated_text == "draft"
        assert render_regions[1].translated_text == ""

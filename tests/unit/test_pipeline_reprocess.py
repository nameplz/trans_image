"""Pipeline.reprocess_region() 단위 테스트 — Phase 5-2."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.core.pipeline import Pipeline
from src.models.processing_job import ProcessingJob, JobStatus
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


# ── 헬퍼 ─────────────────────────────────────────────────────────────────────

def make_region(region_id: str = "region-1", raw_text: str = "Hello") -> TextRegion:
    return TextRegion(
        region_id=region_id,
        raw_text=raw_text,
        translated_text="",
        confidence=0.9,
        bbox=BoundingBox(x=10, y=10, width=100, height=50),
    )


def make_job_with_regions(tmp_path: Path, regions: list[TextRegion]) -> ProcessingJob:
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"")
    job = ProcessingJob(input_path=img_path, target_lang="ko")
    job.original_image = np.zeros((100, 200, 3), dtype=np.uint8)
    job.inpainted_image = np.zeros((100, 200, 3), dtype=np.uint8)
    job.regions = regions
    return job


@pytest.fixture
def mock_pipeline_for_reprocess(mock_config):
    """reprocess_region용 mock Pipeline."""
    plugin_manager = MagicMock()

    # OCR 플러그인 mock
    ocr_plugin = MagicMock()
    ocr_plugin.is_loaded = True
    ocr_plugin.detect_text_in_region = AsyncMock(return_value="Re-detected text")
    plugin_manager.get_ocr_plugin.return_value = ocr_plugin

    # 번역 플러그인 mock
    translator_plugin = MagicMock()
    translator_plugin.is_loaded = True

    async def translate_batch_side(regs, src, tgt):
        return [
            TranslationResult(
                region_id=r.region_id,
                source_text=r.raw_text,
                translated_text=f"번역됨({r.raw_text})",
                source_lang="en",
                target_lang="ko",
            )
            for r in regs
        ]

    translator_plugin.translate_batch = AsyncMock(side_effect=translate_batch_side)
    plugin_manager.get_translator_plugin.return_value = translator_plugin

    pipeline = Pipeline(config=mock_config, plugin_manager=plugin_manager)

    dummy_image = np.zeros((100, 200, 3), dtype=np.uint8)
    pipeline._inpainting_service = MagicMock()
    pipeline._inpainting_service.remove_text = AsyncMock(return_value=dummy_image)
    pipeline._rendering_service = MagicMock()
    pipeline._rendering_service.render = AsyncMock(return_value=dummy_image)
    pipeline._font_service = MagicMock()
    pipeline._lang_service = MagicMock()
    pipeline._lang_service.detect.return_value = "en"

    return pipeline, plugin_manager


class TestPipelineReprocessRegion:
    async def test_reprocess_region_exists(self, mock_pipeline_for_reprocess, tmp_path):
        """Pipeline.reprocess_region() 메서드가 존재해야 한다."""
        pipeline, _ = mock_pipeline_for_reprocess
        assert hasattr(pipeline, "reprocess_region")
        assert callable(pipeline.reprocess_region)

    async def test_reprocess_region_updates_translation(
        self, mock_pipeline_for_reprocess, tmp_path
    ):
        """reprocess_region() 후 해당 region의 translated_text가 업데이트되어야 한다."""
        pipeline, _ = mock_pipeline_for_reprocess
        region = make_region("r1", "Hello")
        job = make_job_with_regions(tmp_path, [region])

        await pipeline.reprocess_region(job, "r1")

        assert region.translated_text != ""

    async def test_reprocess_region_rerenders_image(
        self, mock_pipeline_for_reprocess, tmp_path
    ):
        """reprocess_region() 후 rendering_service.render가 호출되어야 한다."""
        pipeline, _ = mock_pipeline_for_reprocess
        region = make_region("r1")
        job = make_job_with_regions(tmp_path, [region])

        await pipeline.reprocess_region(job, "r1")

        pipeline._rendering_service.render.assert_called_once()

    async def test_reprocess_region_updates_final_image(
        self, mock_pipeline_for_reprocess, tmp_path
    ):
        """reprocess_region() 후 job.final_image가 업데이트되어야 한다."""
        pipeline, _ = mock_pipeline_for_reprocess
        region = make_region("r1")
        job = make_job_with_regions(tmp_path, [region])

        await pipeline.reprocess_region(job, "r1")

        assert job.final_image is not None

    async def test_reprocess_region_unknown_id_raises(
        self, mock_pipeline_for_reprocess, tmp_path
    ):
        """존재하지 않는 region_id로 호출 시 ValueError가 발생해야 한다."""
        pipeline, _ = mock_pipeline_for_reprocess
        region = make_region("r1")
        job = make_job_with_regions(tmp_path, [region])

        with pytest.raises(ValueError, match="region_id"):
            await pipeline.reprocess_region(job, "nonexistent")

    async def test_reprocess_region_calls_translator(
        self, mock_pipeline_for_reprocess, tmp_path
    ):
        """reprocess_region()이 번역 플러그인을 호출해야 한다."""
        pipeline, plugin_manager = mock_pipeline_for_reprocess
        region = make_region("r1", "World")
        job = make_job_with_regions(tmp_path, [region])
        job.translator_plugin_id = "deepl"

        await pipeline.reprocess_region(job, "r1")

        plugin_manager.get_translator_plugin.assert_called()

    async def test_reprocess_region_progress_callback(
        self, mock_pipeline_for_reprocess, tmp_path
    ):
        """progress_cb가 전달되면 최소 1회 호출되어야 한다."""
        pipeline, _ = mock_pipeline_for_reprocess
        region = make_region("r1")
        job = make_job_with_regions(tmp_path, [region])

        calls = []
        await pipeline.reprocess_region(job, "r1", progress_cb=lambda j, msg: calls.append(msg))

        assert len(calls) >= 1

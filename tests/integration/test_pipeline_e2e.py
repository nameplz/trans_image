"""Pipeline E2E 성격의 통합 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import cv2
import numpy as np
import pytest

from src.core.pipeline import Pipeline
from src.models.processing_job import JobStatus, ProcessingJob
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


def make_dummy_image_file(tmp_path: Path, name: str = "input.png") -> Path:
    path = tmp_path / name
    image = np.zeros((80, 160, 3), dtype=np.uint8)
    cv2.imwrite(str(path), cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    return path


def make_regions() -> list[TextRegion]:
    return [
        TextRegion(
            raw_text="Hello",
            confidence=0.95,
            bbox=BoundingBox(10, 10, 60, 20),
        ),
        TextRegion(
            raw_text="World",
            confidence=0.90,
            bbox=BoundingBox(10, 40, 70, 20),
        ),
    ]


def make_result(
    region: TextRegion,
    translated_text: str,
    *,
    is_success: bool = True,
) -> TranslationResult:
    return TranslationResult(
        region_id=region.region_id,
        source_text=region.raw_text,
        translated_text=translated_text,
        source_lang="en",
        target_lang="ko",
        plugin_id="mock",
        error="" if is_success else "translation failed",
    )


@pytest.fixture
def pipeline_with_mocks(mock_config):
    plugin_manager = MagicMock()
    pipeline = Pipeline(config=mock_config, plugin_manager=plugin_manager)
    pipeline._inpainting_service.remove_text = AsyncMock(
        side_effect=lambda image, regions: image.copy()
    )
    pipeline._rendering_service.render = AsyncMock(
        side_effect=lambda image, regions, font_service: image.copy()
    )
    pipeline._lang_service.detect = MagicMock(return_value="en")
    return pipeline, plugin_manager


@pytest.mark.asyncio
async def test_pipeline_e2e_completes_and_saves_output(pipeline_with_mocks, tmp_path):
    pipeline, plugin_manager = pipeline_with_mocks
    input_path = make_dummy_image_file(tmp_path)
    output_path = tmp_path / "translated.png"
    regions = make_regions()

    ocr_plugin = MagicMock()
    ocr_plugin.is_loaded = True
    ocr_plugin.detect_regions = AsyncMock(return_value=regions)

    translator_plugin = MagicMock()
    translator_plugin.is_loaded = True
    translator_plugin.translate_batch = AsyncMock(
        return_value=[make_result(region, f"번역:{region.raw_text}") for region in regions]
    )

    plugin_manager.get_ocr_plugin.return_value = ocr_plugin
    plugin_manager.get_translator_plugin.return_value = translator_plugin

    progress_messages: list[str] = []
    job = ProcessingJob(
        input_path=input_path,
        output_path=output_path,
        target_lang="ko",
        use_agent=False,
    )

    result = await pipeline.run(job, progress_cb=lambda current_job, message: progress_messages.append(message))

    assert result is job
    assert job.status == JobStatus.COMPLETE
    assert job.translated_regions == 2
    assert job.failed_regions == 0
    assert job.final_image is not None
    assert output_path.exists()
    assert progress_messages[-1] == "완료"


@pytest.mark.asyncio
async def test_pipeline_e2e_runs_agent_flow_and_populates_context(pipeline_with_mocks, tmp_path):
    pipeline, plugin_manager = pipeline_with_mocks
    input_path = make_dummy_image_file(tmp_path)
    regions = make_regions()

    ocr_plugin = MagicMock()
    ocr_plugin.is_loaded = False
    ocr_plugin.load = AsyncMock()
    ocr_plugin.detect_regions = AsyncMock(return_value=regions)

    translator_plugin = MagicMock()
    translator_plugin.is_loaded = False
    translator_plugin.load = AsyncMock()
    translator_plugin.translate_batch = AsyncMock(
        return_value=[make_result(region, f"번역:{region.raw_text}") for region in regions]
    )

    agent_plugin = MagicMock()
    agent_plugin.is_loaded = False
    agent_plugin.load = AsyncMock()
    agent_plugin.analyze_ocr_results = AsyncMock(side_effect=lambda current_regions: current_regions)
    agent_plugin.generate_translation_context = AsyncMock(
        return_value={region.region_id: f"context:{region.raw_text}" for region in regions}
    )
    agent_plugin.validate_translations = AsyncMock(side_effect=lambda raw, translated: translated)

    plugin_manager.get_ocr_plugin.return_value = ocr_plugin
    plugin_manager.get_translator_plugin.return_value = translator_plugin
    plugin_manager.get_agent_plugin.return_value = agent_plugin

    job = ProcessingJob(input_path=input_path, target_lang="ko", use_agent=True)
    await pipeline.run(job)

    ocr_plugin.load.assert_called_once()
    translator_plugin.load.assert_called_once()
    agent_plugin.load.assert_called_once()
    agent_plugin.analyze_ocr_results.assert_called_once()
    agent_plugin.generate_translation_context.assert_called_once()
    agent_plugin.validate_translations.assert_called_once()
    assert all(region.source_lang_code == "en" for region in job.regions)
    assert all(region.context_hint.startswith("context:") for region in job.regions)


@pytest.mark.asyncio
async def test_pipeline_e2e_marks_failed_regions_but_completes_job(pipeline_with_mocks, tmp_path):
    pipeline, plugin_manager = pipeline_with_mocks
    input_path = make_dummy_image_file(tmp_path)
    regions = make_regions()

    ocr_plugin = MagicMock()
    ocr_plugin.is_loaded = True
    ocr_plugin.detect_regions = AsyncMock(return_value=regions)

    translator_plugin = MagicMock()
    translator_plugin.is_loaded = True
    translator_plugin.translate_batch = AsyncMock(
        return_value=[
            make_result(regions[0], "번역:Hello"),
            make_result(regions[1], "", is_success=False),
        ]
    )

    plugin_manager.get_ocr_plugin.return_value = ocr_plugin
    plugin_manager.get_translator_plugin.return_value = translator_plugin

    job = ProcessingJob(input_path=input_path, target_lang="ko", use_agent=False)
    await pipeline.run(job)

    assert job.status == JobStatus.COMPLETE
    assert job.translated_regions == 1
    assert job.failed_regions == 1
    assert job.regions[0].translated_text == "번역:Hello"
    assert job.regions[1].needs_review is True

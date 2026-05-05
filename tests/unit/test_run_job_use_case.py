from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import cv2
import numpy as np

from src.core.use_cases.run_job import RunJobUseCase
from src.models.processing_job import JobStatus, ProcessingJob
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


def make_image(tmp_path: Path) -> Path:
    path = tmp_path / "input.png"
    cv2.imwrite(str(path), np.zeros((20, 20, 3), dtype=np.uint8))
    return path


async def test_run_job_use_case_completes_without_agent(tmp_path, mock_config):
    plugin_manager = MagicMock()
    ocr_plugin = MagicMock(is_loaded=True)
    ocr_plugin.detect_regions = AsyncMock(
        return_value=[TextRegion(raw_text="Hello", bbox=BoundingBox(x=0, y=0, width=10, height=10))]
    )
    translator_plugin = MagicMock(is_loaded=True)
    translator_plugin.translate_batch = AsyncMock(
        return_value=[
            TranslationResult(
                region_id="region-1",
                source_text="Hello",
                translated_text="안녕",
                source_lang="en",
                target_lang="ko",
            )
        ]
    )
    plugin_manager.get_ocr_plugin.return_value = ocr_plugin
    plugin_manager.get_translator_plugin.return_value = translator_plugin

    use_case = RunJobUseCase(
        config=mock_config,
        plugin_manager=plugin_manager,
        ocr_service=MagicMock(normalize=MagicMock(side_effect=lambda regions: regions)),
        language_service=MagicMock(detect=MagicMock(return_value="en")),
        inpainting_service=MagicMock(remove_text=AsyncMock(return_value=np.zeros((20, 20, 3), dtype=np.uint8))),
        rendering_service=MagicMock(render=AsyncMock(return_value=np.zeros((20, 20, 3), dtype=np.uint8))),
        font_service=MagicMock(),
        save_image=MagicMock(),
    )
    job = ProcessingJob(input_path=make_image(tmp_path), target_lang="ko", use_agent=False)

    result = await use_case.execute(job)

    assert result.status == JobStatus.COMPLETE
    assert result.translated_regions == 1


async def test_run_job_use_case_completes_with_undetected_language(tmp_path, mock_config):
    plugin_manager = MagicMock()
    ocr_plugin = MagicMock(is_loaded=True)
    ocr_plugin.detect_regions = AsyncMock(
        return_value=[TextRegion(raw_text="Hello", bbox=BoundingBox(x=0, y=0, width=10, height=10))]
    )
    translator_plugin = MagicMock(is_loaded=True)
    translator_plugin.translate_batch = AsyncMock(
        return_value=[
            TranslationResult(
                region_id="region-1",
                source_text="Hello",
                translated_text="안녕",
                source_lang="und",
                target_lang="ko",
            )
        ]
    )
    plugin_manager.get_ocr_plugin.return_value = ocr_plugin
    plugin_manager.get_translator_plugin.return_value = translator_plugin

    use_case = RunJobUseCase(
        config=mock_config,
        plugin_manager=plugin_manager,
        ocr_service=MagicMock(normalize=MagicMock(side_effect=lambda regions: regions)),
        language_service=MagicMock(detect=MagicMock(return_value="und")),
        inpainting_service=MagicMock(remove_text=AsyncMock(return_value=np.zeros((20, 20, 3), dtype=np.uint8))),
        rendering_service=MagicMock(render=AsyncMock(return_value=np.zeros((20, 20, 3), dtype=np.uint8))),
        font_service=MagicMock(),
        save_image=MagicMock(),
    )
    job = ProcessingJob(input_path=make_image(tmp_path), target_lang="ko", use_agent=False)

    result = await use_case.execute(job)

    translator_plugin.translate_batch.assert_awaited_once()
    assert translator_plugin.translate_batch.await_args.args[1] == "und"
    assert result.status == JobStatus.COMPLETE
    assert result.translated_regions == 1

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np

from src.core.use_cases.reprocess_region import ReprocessRegionUseCase
from src.models.processing_job import ProcessingJob
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


async def test_reprocess_region_use_case_updates_translation():
    plugin_manager = MagicMock()
    translator = MagicMock(is_loaded=True)
    translator.translate_batch = AsyncMock(
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
    plugin_manager.get_translator_plugin.return_value = translator
    rendering_service = MagicMock(render=AsyncMock(return_value=np.zeros((10, 10, 3), dtype=np.uint8)))
    use_case = ReprocessRegionUseCase(plugin_manager, rendering_service, MagicMock())
    job = ProcessingJob(target_lang="ko", translator_plugin_id="deepl")
    region = TextRegion(region_id="region-1", raw_text="Hello", bbox=BoundingBox())
    job.regions = [region]
    job.original_image = np.zeros((10, 10, 3), dtype=np.uint8)

    await use_case.execute(job, "region-1")

    assert region.translated_text == "안녕"
    rendering_service.render.assert_called_once()

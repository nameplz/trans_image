from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np

from src.core.use_cases.preview_region_translation import PreviewRegionTranslationUseCase
from src.models.processing_job import ProcessingJob
from src.models.text_region import BoundingBox, TextRegion


async def test_preview_region_translation_use_case_does_not_mutate_job():
    rendering_service = MagicMock(render=AsyncMock(return_value=np.ones((10, 10, 3), dtype=np.uint8)))
    use_case = PreviewRegionTranslationUseCase(rendering_service, MagicMock())
    region = TextRegion(region_id="region-1", raw_text="Hello", bbox=BoundingBox())
    job = ProcessingJob(target_lang="ko")
    job.original_image = np.zeros((10, 10, 3), dtype=np.uint8)
    job.regions = [region]

    result = await use_case.execute(job, "region-1", "draft")

    assert result.shape == (10, 10, 3)
    render_regions = rendering_service.render.await_args.args[1]
    assert render_regions[0].translated_text == "draft"
    assert job.regions[0].translated_text == ""

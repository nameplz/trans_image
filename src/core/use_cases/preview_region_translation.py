"""Render a non-destructive single-region preview."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from src.models.processing_job import ProcessingJob
from src.services.font_service import FontService
from src.services.rendering_service import RenderingService


class PreviewRegionTranslationUseCase:
    def __init__(
        self,
        rendering_service: RenderingService,
        font_service: FontService,
    ) -> None:
        self._rendering_service = rendering_service
        self._font_service = font_service

    async def execute(
        self,
        job: ProcessingJob,
        region_id: str,
        draft_text: str,
    ) -> np.ndarray:
        target = next((region for region in job.regions if region.region_id == region_id), None)
        if target is None:
            raise ValueError(f"region_id '{region_id}' not found in job.regions")

        image_base = job.inpainted_image if job.inpainted_image is not None else job.original_image
        if image_base is None:
            raise ValueError("preview requires original_image or inpainted_image")

        preview_regions = [
            replace(region, translated_text=draft_text)
            if region.region_id == region_id
            else replace(region)
            for region in job.regions
        ]
        return await self._rendering_service.render(
            image_base.copy(),
            preview_regions,
            self._font_service,
        )

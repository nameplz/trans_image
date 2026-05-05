"""Reprocess a single region and rerender the image."""
from __future__ import annotations

from collections.abc import Callable

from src.core.plugin_manager import PluginManager
from src.models.processing_job import ProcessingJob
from src.services.font_service import FontService
from src.services.rendering_service import RenderingService
from src.utils.logger import get_logger

logger = get_logger("trans_image.use_cases.reprocess_region")

ProgressCallback = Callable[[ProcessingJob, str], None]


class ReprocessRegionUseCase:
    def __init__(
        self,
        plugin_manager: PluginManager,
        rendering_service: RenderingService,
        font_service: FontService,
    ) -> None:
        self._plugins = plugin_manager
        self._rendering_service = rendering_service
        self._font_service = font_service

    async def execute(
        self,
        job: ProcessingJob,
        region_id: str,
        progress_cb: ProgressCallback | None = None,
    ) -> ProcessingJob:
        def notify(msg: str) -> None:
            if progress_cb:
                progress_cb(job, msg)
            logger.info("[%s] reprocess: %s", job.job_id[:8], msg)

        target = next((region for region in job.regions if region.region_id == region_id), None)
        if target is None:
            raise ValueError(f"region_id '{region_id}' not found in job.regions")

        notify(f"영역 재번역 중: {region_id[:8]}…")
        translator = self._plugins.get_translator_plugin(job.translator_plugin_id)
        if not translator.is_loaded:
            await translator.load()

        source_lang = target.source_lang_code or job.source_lang or "auto"
        results = await translator.translate_batch([target], source_lang, job.target_lang)
        if results and results[0].is_success:
            target.translated_text = results[0].translated_text
        notify("재번역 완료")

        image_base = job.inpainted_image if job.inpainted_image is not None else job.original_image
        notify("이미지 재렌더링 중")
        final = await self._rendering_service.render(image_base, job.regions, self._font_service)
        job.final_image = final
        notify("재처리 완료")
        return job

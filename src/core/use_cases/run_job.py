"""Run full processing job use case."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from src.core.config_manager import ConfigManager
from src.core.exceptions import ImageProcessingError, PipelineError
from src.core.plugin_manager import PluginManager
from src.models.processing_job import JobStatus, ProcessingJob
from src.services.font_service import FontService
from src.services.inpainting_service import InpaintingService
from src.services.language_service import LanguageService
from src.services.ocr_service import OCRService
from src.services.rendering_service import RenderingService
from src.utils.logger import get_logger

logger = get_logger("trans_image.use_cases.run_job")

ProgressCallback = Callable[[ProcessingJob, str], None]


class RunJobUseCase:
    def __init__(
        self,
        config: ConfigManager,
        plugin_manager: PluginManager,
        ocr_service: OCRService,
        language_service: LanguageService,
        inpainting_service: InpaintingService,
        rendering_service: RenderingService,
        font_service: FontService,
        save_image: Any,
    ) -> None:
        self._config = config
        self._plugins = plugin_manager
        self._ocr_service = ocr_service
        self._lang_service = language_service
        self._inpainting_service = inpainting_service
        self._rendering_service = rendering_service
        self._font_service = font_service
        self._save_image = save_image

    async def execute(
        self,
        job: ProcessingJob,
        progress_cb: ProgressCallback | None = None,
    ) -> ProcessingJob:
        def notify(msg: str, status: JobStatus | None = None, progress: float | None = None) -> None:
            if status:
                job.status = status
            if progress is not None:
                job.progress = progress
            if progress_cb:
                progress_cb(job, msg)
            logger.info("[%s] %s (%.0f%%)", job.job_id[:8], msg, (progress or 0) * 100)

        try:
            job.start()

            notify("이미지 로드 중", JobStatus.OCR_RUNNING, 0.0)
            image = self._load_image(job.input_path)
            job.original_image = image

            notify("OCR 실행 중", JobStatus.OCR_RUNNING, 0.05)
            ocr_plugin = self._plugins.get_ocr_plugin(job.ocr_plugin_id)
            if not ocr_plugin.is_loaded:
                await ocr_plugin.load()

            raw_regions = await ocr_plugin.detect_regions(image)
            regions = self._ocr_service.normalize(raw_regions)
            job.total_regions = len(regions)
            notify(f"OCR 완료: {len(regions)}개 영역 탐지", progress=0.2)

            agent = None
            processing_settings = self._config.processing_settings
            if job.use_agent and processing_settings.agent_analyze:
                notify("에이전트 OCR 분석 중", JobStatus.AGENT_ANALYZING, 0.25)
                agent = self._plugins.get_agent_plugin(job.agent_plugin_id)
                if not agent.is_loaded:
                    await agent.load()
                regions = await agent.analyze_ocr_results(regions)
                notify("에이전트 분석 완료", progress=0.3)

            notify("언어 감지 중", JobStatus.DETECTING_LANGUAGE, 0.32)
            source_lang = job.source_lang
            if source_lang == "auto":
                source_lang = self._lang_service.detect(regions)
                logger.info("감지된 언어: %s", source_lang)
            for region in regions:
                region.source_lang_code = source_lang
            notify(f"언어 감지 완료: {source_lang}", progress=0.35)

            if agent is not None and processing_settings.agent_analyze:
                notify("번역 컨텍스트 생성 중", JobStatus.GENERATING_CONTEXT, 0.37)
                context_hints = await agent.generate_translation_context(regions, job)
                for region in regions:
                    region.context_hint = context_hints.get(region.region_id, "")
                notify("컨텍스트 생성 완료", progress=0.4)

            notify("번역 중", JobStatus.TRANSLATING, 0.42)
            translator = self._plugins.get_translator_plugin(job.translator_plugin_id)
            if not translator.is_loaded:
                await translator.load()

            results = await translator.translate_batch(regions, source_lang, job.target_lang)
            for region, result in zip(regions, results):
                if result.is_success:
                    region.translated_text = result.translated_text
                    job.translated_regions += 1
                else:
                    region.needs_review = True
                    job.failed_regions += 1

            notify(f"번역 완료: {job.translated_regions}/{job.total_regions}", progress=0.6)

            if agent is not None and processing_settings.agent_validate:
                notify("번역 검증 중", JobStatus.AGENT_VALIDATING, 0.62)
                regions = await agent.validate_translations(raw_regions, regions)
                notify("검증 완료", progress=0.65)

            job.regions = regions

            notify("원문 텍스트 제거 중", JobStatus.INPAINTING, 0.67)
            inpainted = await self._inpainting_service.remove_text(image, regions)
            job.inpainted_image = inpainted
            notify("텍스트 제거 완료", progress=0.8)

            notify("번역 텍스트 삽입 중", JobStatus.RENDERING, 0.82)
            final = await self._rendering_service.render(inpainted, regions, self._font_service)
            job.final_image = final
            notify("렌더링 완료", progress=0.95)

            if job.output_path:
                notify("저장 중", progress=0.97)
                self._save_image(final, job.output_path)
                notify(f"저장 완료: {job.output_path}", progress=1.0)

            job.complete()
            notify("완료", JobStatus.COMPLETE, 1.0)
            return job

        except asyncio.CancelledError:
            job.cancel()
            raise
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            job.fail(error_msg)
            logger.exception("파이프라인 실패 (%s): %s", job.job_id[:8], exc)
            raise PipelineError(error_msg) from exc

    def _load_image(self, path: Path) -> np.ndarray:
        import cv2

        img = cv2.imread(str(path))
        if img is None:
            raise ImageProcessingError(f"이미지 로드 실패: {path}")
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

"""전체 처리 흐름 오케스트레이터."""
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np

from src.core.config_manager import ConfigManager
from src.core.exceptions import PipelineError, ImageProcessingError
from src.core.plugin_manager import PluginManager
from src.models.processing_job import ProcessingJob, JobStatus
from src.models.export_options import ExportOptions, ImageFormat
from src.models.text_region import TextRegion
from src.services.export_service import ExportService
from src.services.font_service import FontService
from src.services.inpainting_service import InpaintingService
from src.services.language_service import LanguageService
from src.services.ocr_service import OCRService
from src.services.rendering_service import RenderingService
from src.utils.logger import get_logger

logger = get_logger("trans_image.pipeline")

ProgressCallback = Callable[[ProcessingJob, str], None]


class Pipeline:
    """이미지 텍스트 번역 전체 파이프라인.

    흐름:
      로드 → OCR → 에이전트 분석 → 언어 감지 → 컨텍스트 생성
          → 번역 → 에이전트 검증 → 인페인팅 → 렌더링
    """

    def __init__(
        self,
        config: ConfigManager,
        plugin_manager: PluginManager,
    ) -> None:
        self._config = config
        self._plugins = plugin_manager
        self._ocr_service = OCRService()
        self._lang_service = LanguageService()
        self._inpainting_service = InpaintingService(config)
        self._rendering_service = RenderingService(config)
        self._font_service = FontService(config)
        self._export_service = ExportService()

    async def run(
        self,
        job: ProcessingJob,
        progress_cb: ProgressCallback | None = None,
    ) -> ProcessingJob:
        """파이프라인 실행.

        Args:
            job: 처리할 작업 (input_path, target_lang 등 설정됨)
            progress_cb: 진행 상태 콜백 (job, message) → None

        Returns:
            완료된 ProcessingJob (final_image 포함)
        """
        def notify(msg: str, status: JobStatus | None = None, progress: float | None = None):
            if status:
                job.status = status
            if progress is not None:
                job.progress = progress
            if progress_cb:
                progress_cb(job, msg)
            logger.info("[%s] %s (%.0f%%)", job.job_id[:8], msg, (progress or 0) * 100)

        try:
            job.start()

            # 1. 이미지 로드
            notify("이미지 로드 중", JobStatus.OCR_RUNNING, 0.0)
            image = self._load_image(job.input_path)
            job.original_image = image

            # 2. OCR
            notify("OCR 실행 중", JobStatus.OCR_RUNNING, 0.05)
            ocr_plugin = self._plugins.get_ocr_plugin(job.ocr_plugin_id)
            if not ocr_plugin.is_loaded:
                await ocr_plugin.load()

            raw_regions = await ocr_plugin.detect_regions(image)
            regions = self._ocr_service.normalize(raw_regions)
            job.total_regions = len(regions)
            notify(f"OCR 완료: {len(regions)}개 영역 탐지", progress=0.2)

            # 3. 에이전트 분석 (옵션)
            if job.use_agent and self._config.get("processing", "agent_analyze"):
                notify("에이전트 OCR 분석 중", JobStatus.AGENT_ANALYZING, 0.25)
                agent = self._plugins.get_agent_plugin(job.agent_plugin_id)
                if not agent.is_loaded:
                    await agent.load()
                regions = await agent.analyze_ocr_results(regions)
                notify("에이전트 분석 완료", progress=0.3)

            # 4. 언어 감지
            notify("언어 감지 중", JobStatus.DETECTING_LANGUAGE, 0.32)
            source_lang = job.source_lang
            if source_lang == "auto":
                source_lang = self._lang_service.detect(regions)
                logger.info("감지된 언어: %s", source_lang)
            for r in regions:
                r.source_lang_code = source_lang
            notify(f"언어 감지 완료: {source_lang}", progress=0.35)

            # 5. 번역 컨텍스트 생성 (에이전트)
            if job.use_agent and self._config.get("processing", "agent_analyze"):
                notify("번역 컨텍스트 생성 중", JobStatus.GENERATING_CONTEXT, 0.37)
                context_hints = await agent.generate_translation_context(regions, job)
                for r in regions:
                    r.context_hint = context_hints.get(r.region_id, "")
                notify("컨텍스트 생성 완료", progress=0.4)

            # 6. 번역
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

            notify(
                f"번역 완료: {job.translated_regions}/{job.total_regions}",
                progress=0.6,
            )

            # 7. 에이전트 검증 (옵션)
            if job.use_agent and self._config.get("processing", "agent_validate"):
                notify("번역 검증 중", JobStatus.AGENT_VALIDATING, 0.62)
                regions = await agent.validate_translations(raw_regions, regions)
                notify("검증 완료", progress=0.65)

            job.regions = regions

            # 8. 인페인팅
            notify("원문 텍스트 제거 중", JobStatus.INPAINTING, 0.67)
            inpainted = await self._inpainting_service.remove_text(image, regions)
            job.inpainted_image = inpainted
            notify("텍스트 제거 완료", progress=0.8)

            # 9. 렌더링
            notify("번역 텍스트 삽입 중", JobStatus.RENDERING, 0.82)
            final = await self._rendering_service.render(inpainted, regions, self._font_service)
            job.final_image = final
            notify("렌더링 완료", progress=0.95)

            # 10. 저장
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
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            job.fail(error_msg)
            logger.exception("파이프라인 실패 (%s): %s", job.job_id[:8], e)
            raise PipelineError(error_msg) from e

    async def reprocess_region(
        self,
        job: ProcessingJob,
        region_id: str,
        progress_cb: ProgressCallback | None = None,
    ) -> ProcessingJob:
        """단일 영역 OCR+번역 재처리 후 전체 이미지 재렌더링.

        Args:
            job: 처리 중인 작업 (original_image, regions 포함)
            region_id: 재처리할 TextRegion의 ID
            progress_cb: 진행 상태 콜백 (job, message) → None

        Returns:
            업데이트된 ProcessingJob (final_image 갱신됨)

        Raises:
            ValueError: region_id가 job.regions에 없을 때
        """
        def notify(msg: str) -> None:
            if progress_cb:
                progress_cb(job, msg)
            logger.info("[%s] reprocess: %s", job.job_id[:8], msg)

        target = next((r for r in job.regions if r.region_id == region_id), None)
        if target is None:
            raise ValueError(f"region_id '{region_id}' not found in job.regions")

        notify(f"영역 재번역 중: {region_id[:8]}…")

        # 번역만 재실행
        translator = self._plugins.get_translator_plugin(job.translator_plugin_id)
        if not translator.is_loaded:
            await translator.load()

        source_lang = target.source_lang_code or job.source_lang or "auto"
        results = await translator.translate_batch([target], source_lang, job.target_lang)
        if results and results[0].is_success:
            target.translated_text = results[0].translated_text
        notify("재번역 완료")

        # 인페인팅은 기존 inpainted_image 재사용, 전체 regions로 재렌더링
        image_base = job.inpainted_image if job.inpainted_image is not None else job.original_image
        notify("이미지 재렌더링 중")
        final = await self._rendering_service.render(image_base, job.regions, self._font_service)
        job.final_image = final
        notify("재처리 완료")
        return job

    async def preview_region_translation(
        self,
        job: ProcessingJob,
        region_id: str,
        draft_text: str,
    ) -> np.ndarray:
        """영역 번역 draft를 비파괴적으로 반영한 프리뷰 이미지를 생성한다."""
        target = next((r for r in job.regions if r.region_id == region_id), None)
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

    def _load_image(self, path: Path) -> np.ndarray:
        """이미지 파일 로드 → RGB numpy 배열."""
        import cv2
        img = cv2.imread(str(path))
        if img is None:
            raise ImageProcessingError(f"이미지 로드 실패: {path}")
        return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    def _save_image(
        self,
        image: np.ndarray,
        path: Path,
        options: ExportOptions | None = None,
    ) -> None:
        """RGB numpy 배열 → 파일 저장."""
        export_options = options
        if export_options is None:
            ext = path.suffix.lower()
            image_format = ImageFormat.PNG
            if ext in (".jpg", ".jpeg"):
                image_format = ImageFormat.JPEG
            elif ext == ".webp":
                image_format = ImageFormat.WEBP
            export_options = ExportOptions(
                format=image_format,
                jpeg_quality=int(self._config.get("export", "jpg_quality", default=95) or 95),
                webp_quality=int(self._config.get("export", "webp_quality", default=90) or 90),
                png_compression=int(self._config.get("export", "png_compression", default=3) or 3),
            )
        self._export_service.save_image(image, path, export_options)

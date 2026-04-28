"""전체 처리 흐름 facade."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from src.core.config_manager import ConfigManager
from src.core.plugin_manager import PluginManager
from src.core.use_cases.preview_region_translation import PreviewRegionTranslationUseCase
from src.core.use_cases.reprocess_region import ReprocessRegionUseCase
from src.core.use_cases.run_job import ProgressCallback, RunJobUseCase
from src.models.export_options import ExportOptions, ImageFormat
from src.models.processing_job import ProcessingJob
from src.services.export_service import ExportService
from src.services.font_service import FontService
from src.services.inpainting_service import InpaintingService
from src.services.language_service import LanguageService
from src.services.ocr_service import OCRService
from src.services.rendering_service import RenderingService


class Pipeline:
    """Legacy facade that delegates to dedicated use cases."""

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
        return await self._create_run_job_use_case().execute(job, progress_cb)

    async def reprocess_region(
        self,
        job: ProcessingJob,
        region_id: str,
        progress_cb: ProgressCallback | None = None,
    ) -> ProcessingJob:
        return await self._create_reprocess_region_use_case().execute(
            job,
            region_id,
            progress_cb,
        )

    async def preview_region_translation(
        self,
        job: ProcessingJob,
        region_id: str,
        draft_text: str,
    ) -> np.ndarray:
        return await self._create_preview_region_translation_use_case().execute(
            job,
            region_id,
            draft_text,
        )

    def export_image(
        self,
        image: np.ndarray,
        path: Path,
        options: ExportOptions | None = None,
    ) -> Path:
        """Public export boundary for GUI and other callers."""
        return self._save_image(image, path, options)

    def _create_run_job_use_case(self) -> RunJobUseCase:
        return RunJobUseCase(
            config=self._config,
            plugin_manager=self._plugins,
            ocr_service=self._ocr_service,
            language_service=self._lang_service,
            inpainting_service=self._inpainting_service,
            rendering_service=self._rendering_service,
            font_service=self._font_service,
            save_image=self._save_image,
        )

    def _create_reprocess_region_use_case(self) -> ReprocessRegionUseCase:
        return ReprocessRegionUseCase(
            plugin_manager=self._plugins,
            rendering_service=self._rendering_service,
            font_service=self._font_service,
        )

    def _create_preview_region_translation_use_case(self) -> PreviewRegionTranslationUseCase:
        return PreviewRegionTranslationUseCase(
            rendering_service=self._rendering_service,
            font_service=self._font_service,
        )

    def _save_image(
        self,
        image: np.ndarray,
        path: Path,
        options: ExportOptions | None = None,
    ) -> Path:
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
        return self._export_service.save_image(image, path, export_options)

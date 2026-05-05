"""GUI job orchestration controller."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal

from src.core.exceptions import ConcurrencyLimitError
from src.core.pipeline import Pipeline
from src.core.session import Session
from src.gui.workers.pipeline_worker import WorkerPool
from src.models.export_options import ExportOptions
from src.models.processing_job import ProcessingJob
from src.models.text_region import TextRegion
from src.utils.logger import get_logger

logger = get_logger("trans_image.gui.job_controller")


@dataclass
class RegionEditState:
    region_id: str
    draft_text: str = ""
    preview_text: str = ""
    is_dirty: bool = False


class JobController(QObject):
    progress_updated = Signal(str, float, str)
    status_changed = Signal(str, str)
    job_completed = Signal(str)
    job_failed = Signal(str, str)
    region_reprocess_done = Signal(str, str)
    region_reprocess_failed = Signal(str, str, str)
    preview_display_ready = Signal(object)
    rendered_image_ready = Signal(object)

    def __init__(
        self,
        pipeline: Pipeline,
        session: Session,
        worker_pool: WorkerPool,
        *,
        reprocess_worker_factory: Callable[..., Any],
        preview_worker_factory: Callable[..., Any],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._pipeline = pipeline
        self._session = session
        self._worker_pool = worker_pool
        self._reprocess_worker_factory = reprocess_worker_factory
        self._preview_worker_factory = preview_worker_factory
        self._current_job: ProcessingJob | None = None
        self._reprocess_workers: dict[str, Any] = {}
        self._preview_worker: Any | None = None
        self._preview_debounce = QTimer(self)
        self._preview_debounce.setSingleShot(True)
        self._preview_debounce.setInterval(350)
        self._preview_debounce.timeout.connect(self._start_preview_worker)
        self._pending_preview_region_id: str | None = None
        self._pending_preview_text = ""
        self._preview_request_id = 0
        self._latest_preview_request_id = -1
        self._latest_preview_region_id: str | None = None
        self._latest_preview_text: str | None = None
        self._latest_preview_image: np.ndarray | None = None
        self._edit_states: dict[str, RegionEditState] = {}

    @property
    def current_job(self) -> ProcessingJob | None:
        return self._current_job

    @current_job.setter
    def current_job(self, value: ProcessingJob | None) -> None:
        self._current_job = value

    @property
    def reprocess_workers(self) -> dict[str, Any]:
        return self._reprocess_workers

    @property
    def preview_worker(self) -> Any | None:
        return self._preview_worker

    @property
    def preview_request_id(self) -> int:
        return self._preview_request_id

    @preview_request_id.setter
    def preview_request_id(self, value: int) -> None:
        self._preview_request_id = value

    @property
    def pending_preview_text(self) -> str:
        return self._pending_preview_text

    @pending_preview_text.setter
    def pending_preview_text(self, value: str) -> None:
        self._pending_preview_text = value

    @property
    def latest_preview_request_id(self) -> int:
        return self._latest_preview_request_id

    @latest_preview_request_id.setter
    def latest_preview_request_id(self, value: int) -> None:
        self._latest_preview_request_id = value

    @property
    def latest_preview_region_id(self) -> str | None:
        return self._latest_preview_region_id

    @latest_preview_region_id.setter
    def latest_preview_region_id(self, value: str | None) -> None:
        self._latest_preview_region_id = value

    @property
    def latest_preview_text(self) -> str | None:
        return self._latest_preview_text

    @latest_preview_text.setter
    def latest_preview_text(self, value: str | None) -> None:
        self._latest_preview_text = value

    @property
    def latest_preview_image(self) -> np.ndarray | None:
        return self._latest_preview_image

    @latest_preview_image.setter
    def latest_preview_image(self, value: np.ndarray | None) -> None:
        self._latest_preview_image = value

    def start_processing(
        self,
        input_path,
        settings: dict[str, Any],
        *,
        parent: QObject | None = None,
    ) -> ProcessingJob:
        if self._worker_pool.is_at_capacity is True:
            raise ConcurrencyLimitError(
                "현재 단일 이미지 작업이 최대 동시 실행 수에 도달했습니다."
            )
        job = self._session.create_job_for_file(
            input_path=input_path,
            target_lang=settings["target_lang"],
            source_lang=settings["source_lang"],
            ocr_plugin_id=settings["ocr_plugin"],
            translator_plugin_id=settings["translator_plugin"],
            agent_plugin_id=settings["agent_plugin"],
            use_agent=settings["use_agent"],
        )
        self._current_job = job
        worker = self._worker_pool.submit(job, parent=parent)
        worker.progress_updated.connect(self.progress_updated.emit)
        worker.status_changed.connect(self.status_changed.emit)
        worker.job_completed.connect(self._on_job_done)
        worker.job_failed.connect(self._on_job_failed)
        return job

    def cancel_processing(self) -> None:
        if self._current_job is not None:
            self._worker_pool.cancel(self._current_job.job_id)

    def export_current_image(self, output_path: Path, options: ExportOptions) -> Path:
        if self._current_job is None or self._current_job.final_image is None:
            raise ValueError("내보낼 번역 이미지가 없습니다.")
        return self._pipeline.export_image(
            self._current_job.final_image,
            output_path,
            options,
        )

    def select_job(self, job_id: str) -> ProcessingJob | None:
        job = self._session.get_job(job_id)
        if job is not None:
            self._current_job = job
        return job

    def get_region(self, region_id: str) -> TextRegion | None:
        if self._current_job is None:
            return None
        return next(
            (region for region in self._current_job.regions if region.region_id == region_id),
            None,
        )

    def request_reprocess(self, region_id: str, *, parent: QObject | None = None) -> None:
        if self._current_job is None:
            return
        target = self.get_region(region_id)
        if target is None:
            return
        worker = self._reprocess_worker_factory(
            self._pipeline,
            self._current_job,
            region_id,
            parent=parent,
        )
        self._reprocess_workers[region_id] = worker
        worker.progress_updated.connect(self.progress_updated.emit)
        worker.region_done.connect(self._on_region_reprocess_done)
        worker.region_failed.connect(self._on_region_reprocess_failed)
        worker.finished.connect(lambda rid=region_id: self._reprocess_workers.pop(rid, None))
        worker.start()

    def apply_translation_edit(self, region_id: str, new_text: str) -> TextRegion | None:
        region = self.get_region(region_id)
        if region is None or self._current_job is None:
            return None
        region.translated_text = new_text
        self._edit_states[region_id] = RegionEditState(
            region_id=region_id,
            draft_text=new_text,
            preview_text=new_text,
            is_dirty=True,
        )
        self._promote_preview_or_render(region_id, new_text)
        return region

    def request_translation_preview(self, region_id: str, draft_text: str) -> None:
        if self._current_job is None:
            return
        if self._current_job.is_running or self._reprocess_workers:
            return
        image_base = (
            self._current_job.inpainted_image
            if self._current_job.inpainted_image is not None
            else self._current_job.original_image
        )
        if image_base is None:
            return
        self._edit_states[region_id] = RegionEditState(
            region_id=region_id,
            draft_text=draft_text,
            preview_text=draft_text,
            is_dirty=True,
        )
        self._pending_preview_region_id = region_id
        self._pending_preview_text = draft_text
        self._preview_request_id += 1
        self._preview_debounce.start()

    def _start_preview_worker(self) -> None:
        if self._current_job is None or self._pending_preview_region_id is None:
            return
        request_id = self._preview_request_id
        worker = self._preview_worker_factory(
            self._pipeline,
            self._current_job,
            self._pending_preview_region_id,
            self._pending_preview_text,
            request_id,
            parent=self.parent(),
        )
        self._preview_worker = worker
        worker.preview_ready.connect(self._on_preview_ready)
        worker.preview_failed.connect(self._on_preview_failed)
        worker.finished.connect(self._on_preview_worker_finished)
        worker.start()

    def _on_job_done(self, job_id: str) -> None:
        self.job_completed.emit(job_id)

    def _on_job_failed(self, job_id: str, error: str) -> None:
        self.job_failed.emit(job_id, error)

    def _on_region_reprocess_done(self, job_id: str, region_id: str) -> None:
        self.region_reprocess_done.emit(job_id, region_id)
        if self._current_job is not None and self._current_job.final_image is not None:
            self.rendered_image_ready.emit(self._current_job.final_image)

    def _on_region_reprocess_failed(self, job_id: str, region_id: str, error: str) -> None:
        self.region_reprocess_failed.emit(job_id, region_id, error)

    def _on_preview_ready(self, job_id: str, region_id: str, request_id: int, image: object) -> None:
        if self._current_job is None or self._current_job.job_id != job_id:
            return
        if request_id != self._preview_request_id:
            return
        preview_image = image if isinstance(image, np.ndarray) else None
        if preview_image is None:
            return
        self._latest_preview_request_id = request_id
        self._latest_preview_region_id = region_id
        self._latest_preview_text = self._pending_preview_text
        self._latest_preview_image = preview_image
        self.preview_display_ready.emit(preview_image)

    def _on_preview_failed(self, job_id: str, region_id: str, request_id: int, error: str) -> None:
        if request_id != self._preview_request_id:
            return
        logger.error("영역 프리뷰 실패 [%s]: %s", region_id[:8], error)

    def _on_preview_worker_finished(self) -> None:
        self._preview_worker = None

    def _promote_preview_or_render(self, region_id: str, new_text: str) -> None:
        if self._current_job is None:
            return
        if (
            self._latest_preview_image is not None
            and self._latest_preview_region_id == region_id
            and self._latest_preview_text == new_text
            and self._latest_preview_request_id == self._preview_request_id
        ):
            self._current_job.final_image = self._latest_preview_image
        else:
            self._current_job.final_image = asyncio.run(
                self._pipeline.preview_region_translation(self._current_job, region_id, new_text)
            )
            self._latest_preview_image = self._current_job.final_image
            self._latest_preview_region_id = region_id
            self._latest_preview_text = new_text
            self._latest_preview_request_id = self._preview_request_id
        self.rendered_image_ready.emit(self._current_job.final_image)

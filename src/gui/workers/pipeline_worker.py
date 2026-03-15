"""QThread ↔ asyncio 브릿지 — 파이프라인 비동기 실행."""
from __future__ import annotations

import asyncio
import traceback
from typing import Any

from PySide6.QtCore import QThread, Signal

from src.core.pipeline import Pipeline
from src.models.processing_job import ProcessingJob
from src.utils.logger import get_logger

logger = get_logger("trans_image.worker")


class PipelineWorker(QThread):
    """파이프라인을 QThread 내에서 실행하고 결과를 Signal로 전달.

    설계 원칙:
    - QThread 내부에 독립 asyncio 이벤트 루프 생성
    - 메인 스레드의 Qt 이벤트 루프와 완전히 분리
    - 결과는 Qt Signal로 메인 스레드에 전달
    """

    # 시그널 정의
    progress_updated = Signal(str, float, str)   # job_id, progress(0~1), message
    job_completed = Signal(str)                   # job_id
    job_failed = Signal(str, str)                 # job_id, error_message
    status_changed = Signal(str, str)             # job_id, status_label

    def __init__(self, pipeline: Pipeline, job: ProcessingJob, parent=None) -> None:
        super().__init__(parent)
        self._pipeline = pipeline
        self._job = job
        self._loop: asyncio.AbstractEventLoop | None = None
        self._cancelled = False

    def run(self) -> None:
        """QThread 진입점 — 새 이벤트 루프에서 파이프라인 실행."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_pipeline())
        except Exception as e:
            logger.exception("워커 실행 오류: %s", e)
        finally:
            self._loop.close()
            self._loop = None

    async def _run_pipeline(self) -> None:
        try:
            await self._pipeline.run(
                self._job,
                progress_cb=self._on_progress,
            )
            if not self._cancelled:
                self.job_completed.emit(self._job.job_id)
        except asyncio.CancelledError:
            logger.info("작업 취소됨: %s", self._job.job_id)
        except Exception as e:
            error = traceback.format_exc()
            logger.error("파이프라인 오류: %s", error)
            self.job_failed.emit(self._job.job_id, str(e))

    def _on_progress(self, job: ProcessingJob, message: str) -> None:
        """파이프라인 콜백 → Qt Signal 전환."""
        self.progress_updated.emit(job.job_id, job.progress, message)
        self.status_changed.emit(job.job_id, job.status_label)

    def cancel(self) -> None:
        """작업 취소 요청."""
        self._cancelled = True
        self._job.cancel()
        if self._loop and self._loop.is_running():
            for task in asyncio.all_tasks(self._loop):
                task.cancel()
        logger.info("취소 요청: %s", self._job.job_id)


class WorkerPool:
    """여러 PipelineWorker를 관리하는 풀."""

    def __init__(self, pipeline: Pipeline, max_concurrent: int = 2) -> None:
        self._pipeline = pipeline
        self._max = max_concurrent
        self._workers: dict[str, PipelineWorker] = {}

    def submit(self, job: ProcessingJob, parent=None) -> PipelineWorker:
        """작업을 새 워커에 제출."""
        worker = PipelineWorker(self._pipeline, job, parent=parent)
        self._workers[job.job_id] = worker
        worker.finished.connect(lambda: self._workers.pop(job.job_id, None))
        worker.start()
        return worker

    def cancel(self, job_id: str) -> None:
        worker = self._workers.get(job_id)
        if worker:
            worker.cancel()

    def cancel_all(self) -> None:
        for worker in list(self._workers.values()):
            worker.cancel()

    @property
    def active_count(self) -> int:
        return len(self._workers)

    @property
    def is_at_capacity(self) -> bool:
        return self.active_count >= self._max

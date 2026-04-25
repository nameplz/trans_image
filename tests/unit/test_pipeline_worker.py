"""PipelineWorker 및 관련 워커 단위 테스트."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.core.exceptions import PipelineError
from src.gui.workers.pipeline_worker import (
    PipelineWorker,
    RegionPreviewWorker,
    RegionReprocessWorker,
    WorkerPool,
)
from src.models.processing_job import JobStatus, ProcessingJob
from src.models.text_region import BoundingBox, TextRegion


@pytest.fixture
def sample_job(tmp_path):
    path = tmp_path / "worker.png"
    path.write_bytes(b"")
    return ProcessingJob(input_path=path, target_lang="ko")


class TestPipelineWorker:
    async def test_run_pipeline_emits_completion_signal(self, qtbot, sample_job):
        pipeline = MagicMock()
        pipeline.run = AsyncMock()
        worker = PipelineWorker(pipeline, sample_job)

        completed: list[str] = []
        worker.job_completed.connect(completed.append)

        await worker._run_pipeline()

        assert completed == [sample_job.job_id]

    async def test_run_pipeline_emits_failure_signal(self, qtbot, sample_job):
        pipeline = MagicMock()
        pipeline.run = AsyncMock(side_effect=PipelineError("boom"))
        worker = PipelineWorker(pipeline, sample_job)

        failures: list[tuple[str, str]] = []
        worker.job_failed.connect(lambda job_id, error: failures.append((job_id, error)))

        await worker._run_pipeline()

        assert failures == [(sample_job.job_id, "boom")]

    async def test_on_progress_emits_progress_and_status(self, qtbot, sample_job):
        worker = PipelineWorker(MagicMock(), sample_job)
        sample_job.progress = 0.5
        sample_job.status = JobStatus.TRANSLATING

        progress_events: list[tuple[str, float, str]] = []
        status_events: list[tuple[str, str]] = []
        worker.progress_updated.connect(
            lambda job_id, progress, message: progress_events.append((job_id, progress, message))
        )
        worker.status_changed.connect(lambda job_id, status: status_events.append((job_id, status)))

        worker._on_progress(sample_job, "번역 중")

        assert progress_events == [(sample_job.job_id, 0.5, "번역 중")]
        assert status_events == [(sample_job.job_id, "translating")]

    def test_cancel_marks_job_and_cancels_loop_tasks(self, sample_job):
        pipeline = MagicMock()
        worker = PipelineWorker(pipeline, sample_job)
        loop = MagicMock()
        loop.is_running.return_value = True
        task = MagicMock()
        worker._loop = loop

        with patch("src.gui.workers.pipeline_worker.asyncio.all_tasks", return_value={task}):
            worker.cancel()

        assert worker._cancelled is True
        assert sample_job.status == JobStatus.CANCELLED
        task.cancel.assert_called_once()


class TestRegionWorkers:
    async def test_reprocess_worker_emits_done(self, qtbot, sample_job):
        pipeline = MagicMock()
        pipeline.reprocess_region = AsyncMock(return_value=sample_job)
        worker = RegionReprocessWorker(pipeline, sample_job, "region-1")

        done: list[tuple[str, str]] = []
        worker.region_done.connect(lambda job_id, region_id: done.append((job_id, region_id)))

        await worker._run()

        assert done == [(sample_job.job_id, "region-1")]

    async def test_reprocess_worker_emits_failure(self, qtbot, sample_job):
        pipeline = MagicMock()
        pipeline.reprocess_region = AsyncMock(side_effect=ValueError("missing"))
        worker = RegionReprocessWorker(pipeline, sample_job, "region-1")

        failures: list[tuple[str, str, str]] = []
        worker.region_failed.connect(
            lambda job_id, region_id, error: failures.append((job_id, region_id, error))
        )

        await worker._run()

        assert failures == [(sample_job.job_id, "region-1", "missing")]

    def test_reprocess_progress_signal(self, qtbot, sample_job):
        worker = RegionReprocessWorker(MagicMock(), sample_job, "region-1")
        events: list[tuple[str, float, str]] = []
        worker.progress_updated.connect(
            lambda job_id, progress, message: events.append((job_id, progress, message))
        )

        sample_job.progress = 0.3
        worker._on_progress(sample_job, "재처리 중")

        assert events == [(sample_job.job_id, 0.3, "재처리 중")]

    def test_preview_worker_run_emits_ready(self, qtbot, sample_job):
        preview = np.zeros((10, 10, 3), dtype=np.uint8)
        pipeline = MagicMock()
        pipeline.preview_region_translation = AsyncMock(return_value=preview)
        worker = RegionPreviewWorker(pipeline, sample_job, "region-1", "draft", 7)

        ready: list[tuple[str, str, int, object]] = []
        worker.preview_ready.connect(
            lambda job_id, region_id, request_id, image: ready.append(
                (job_id, region_id, request_id, image)
            )
        )

        worker.run()

        assert ready == [(sample_job.job_id, "region-1", 7, preview)]

    def test_preview_worker_run_emits_failure(self, qtbot, sample_job):
        pipeline = MagicMock()
        pipeline.preview_region_translation = AsyncMock(side_effect=ValueError("preview failed"))
        worker = RegionPreviewWorker(pipeline, sample_job, "region-1", "draft", 9)

        failures: list[tuple[str, str, int, str]] = []
        worker.preview_failed.connect(
            lambda job_id, region_id, request_id, error: failures.append(
                (job_id, region_id, request_id, error)
            )
        )

        worker.run()

        assert failures == [(sample_job.job_id, "region-1", 9, "preview failed")]


class TestWorkerPool:
    def test_submit_tracks_worker_and_starts_it(self, sample_job):
        pipeline = MagicMock()
        pool = WorkerPool(pipeline, max_concurrent=1)

        with patch("src.gui.workers.pipeline_worker.PipelineWorker") as MockWorker:
            worker = MockWorker.return_value
            submitted = pool.submit(sample_job)

        assert submitted is worker
        worker.start.assert_called_once()
        assert pool.active_count == 1
        assert pool.is_at_capacity is True

    def test_cancel_and_cancel_all_delegate_to_workers(self, sample_job):
        pool = WorkerPool(MagicMock(), max_concurrent=2)
        worker_a = MagicMock()
        worker_b = MagicMock()
        pool._workers = {
            "job-a": worker_a,
            "job-b": worker_b,
        }

        pool.cancel("job-a")
        pool.cancel_all()

        worker_a.cancel.assert_called()
        worker_b.cancel.assert_called_once()

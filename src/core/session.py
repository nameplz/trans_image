"""처리 세션 상태 관리."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from src.models.processing_job import ProcessingJob, JobStatus
from src.utils.logger import get_logger

logger = get_logger("trans_image.session")


class Session:
    """단일 앱 세션 내 작업 대기열 및 상태 추적."""

    def __init__(self) -> None:
        self._jobs: dict[str, ProcessingJob] = {}
        self._queue: list[str] = []  # job_id 순서

    def add_job(self, job: ProcessingJob) -> None:
        self._jobs[job.job_id] = job
        self._queue.append(job.job_id)
        logger.debug("작업 추가: %s (%s)", job.job_id, job.input_path)

    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        return self._jobs.get(job_id)

    def remove_job(self, job_id: str) -> None:
        self._jobs.pop(job_id, None)
        if job_id in self._queue:
            self._queue.remove(job_id)

    def next_pending(self) -> Optional[ProcessingJob]:
        """대기 상태인 다음 작업 반환."""
        for job_id in self._queue:
            job = self._jobs.get(job_id)
            if job and job.status == JobStatus.QUEUED:
                return job
        return None

    @property
    def all_jobs(self) -> list[ProcessingJob]:
        return [self._jobs[jid] for jid in self._queue if jid in self._jobs]

    @property
    def pending_count(self) -> int:
        return sum(
            1 for j in self._jobs.values() if j.status == JobStatus.QUEUED
        )

    @property
    def running_count(self) -> int:
        terminal = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.QUEUED}
        return sum(1 for j in self._jobs.values() if j.status not in terminal)

    def create_job_for_file(
        self,
        input_path: Path,
        target_lang: str = "ko",
        source_lang: str = "auto",
        **kwargs,
    ) -> ProcessingJob:
        job = ProcessingJob(
            input_path=input_path,
            target_lang=target_lang,
            source_lang=source_lang,
            **kwargs,
        )
        self.add_job(job)
        return job

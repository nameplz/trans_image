"""Session 클래스 단위 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.core.session import Session
from src.models.processing_job import JobStatus, ProcessingJob


def make_job(status: JobStatus = JobStatus.QUEUED) -> ProcessingJob:
    job = ProcessingJob(input_path=Path("/tmp/img.png"), target_lang="ko")
    job.status = status
    return job


class TestSessionCRUD:
    def test_add_and_get_job(self):
        session = Session()
        job = make_job()
        session.add_job(job)
        assert session.get_job(job.job_id) is job

    def test_get_nonexistent_returns_none(self):
        session = Session()
        assert session.get_job("nonexistent-id") is None

    def test_remove_job(self):
        session = Session()
        job = make_job()
        session.add_job(job)
        session.remove_job(job.job_id)
        assert session.get_job(job.job_id) is None

    def test_remove_nonexistent_no_exception(self):
        session = Session()
        # 없는 ID 삭제 시 예외 없음
        session.remove_job("nonexistent-id")

    def test_all_jobs_in_order(self):
        session = Session()
        jobs = [make_job() for _ in range(3)]
        for j in jobs:
            session.add_job(j)
        assert [j.job_id for j in session.all_jobs] == [j.job_id for j in jobs]


class TestSessionNextPending:
    def test_returns_queued_job(self):
        session = Session()
        job = make_job(JobStatus.QUEUED)
        session.add_job(job)
        assert session.next_pending() is job

    def test_skips_running_job(self):
        session = Session()
        running = make_job(JobStatus.OCR_RUNNING)
        queued = make_job(JobStatus.QUEUED)
        session.add_job(running)
        session.add_job(queued)
        assert session.next_pending() is queued

    def test_empty_queue_returns_none(self):
        session = Session()
        assert session.next_pending() is None

    def test_all_complete_returns_none(self):
        session = Session()
        for status in (JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED):
            session.add_job(make_job(status))
        assert session.next_pending() is None


class TestSessionRunningCount:
    def test_running_count_excludes_terminal_and_queued(self):
        session = Session()
        # 비터미널 & 비QUEUED 상태들
        running_statuses = [
            JobStatus.OCR_RUNNING,
            JobStatus.TRANSLATING,
            JobStatus.INPAINTING,
            JobStatus.RENDERING,
        ]
        for status in running_statuses:
            session.add_job(make_job(status))
        # QUEUED, COMPLETE, FAILED, CANCELLED는 제외
        for status in (JobStatus.QUEUED, JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED):
            session.add_job(make_job(status))
        assert session.running_count == len(running_statuses)

    def test_running_count_zero_when_empty(self):
        session = Session()
        assert session.running_count == 0

    def test_pending_count(self):
        session = Session()
        for _ in range(3):
            session.add_job(make_job(JobStatus.QUEUED))
        session.add_job(make_job(JobStatus.COMPLETE))
        assert session.pending_count == 3

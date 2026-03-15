"""파이프라인 통합 테스트 (모킹 사용)."""
from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.models.processing_job import ProcessingJob, JobStatus
from src.models.text_region import BoundingBox, TextRegion
from src.models.translation_result import TranslationResult


@pytest.fixture
def sample_image() -> np.ndarray:
    """테스트용 더미 이미지 (RGB)."""
    return np.zeros((100, 200, 3), dtype=np.uint8)


@pytest.fixture
def sample_regions() -> list[TextRegion]:
    return [
        TextRegion(
            bbox=BoundingBox(10, 10, 100, 20),
            raw_text="Hello World",
            confidence=0.95,
        ),
        TextRegion(
            bbox=BoundingBox(10, 40, 150, 20),
            raw_text="Test text",
            confidence=0.8,
        ),
    ]


@pytest.mark.asyncio
async def test_ocr_service_normalize(sample_regions):
    from src.services.ocr_service import OCRService
    service = OCRService()
    normalized = service.normalize(sample_regions)
    assert len(normalized) == 2
    assert all(r.reading_order > 0 for r in normalized)


@pytest.mark.asyncio
async def test_language_service_detect(sample_regions):
    from src.services.language_service import LanguageService
    service = LanguageService()
    lang = service.detect(sample_regions)
    # English 또는 und (lingua 미설치 시)
    assert lang in ("en", "und")


@pytest.mark.asyncio
async def test_translation_result_creation():
    result = TranslationResult(
        region_id="test-id",
        source_text="Hello",
        translated_text="안녕하세요",
        source_lang="en",
        target_lang="ko",
        plugin_id="mock",
    )
    assert result.is_success is True
    assert result.region_id == "test-id"


@pytest.mark.asyncio
async def test_processing_job_lifecycle():
    job = ProcessingJob(
        input_path=Path("test.png"),
        target_lang="ko",
    )
    assert job.status == JobStatus.QUEUED
    job.start()
    assert job.status == JobStatus.OCR_RUNNING
    job.complete()
    assert job.status == JobStatus.COMPLETE
    assert job.is_done


@pytest.mark.asyncio
async def test_session_job_management():
    from src.core.session import Session
    session = Session()
    job = session.create_job_for_file(Path("img.png"), target_lang="ko")
    assert session.pending_count == 1
    assert session.get_job(job.job_id) is job
    job.start()
    assert session.running_count == 1
    job.complete()
    assert session.running_count == 0

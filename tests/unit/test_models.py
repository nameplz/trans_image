"""핵심 데이터 모델 단위 테스트."""
from __future__ import annotations

import pytest
from src.models.text_region import BoundingBox, TextRegion, TextStyle, TextDirection
from src.models.processing_job import ProcessingJob, JobStatus
from src.models.translation_result import TranslationResult


class TestBoundingBox:
    def test_properties(self):
        bbox = BoundingBox(x=10, y=20, width=100, height=50)
        assert bbox.x2 == 110
        assert bbox.y2 == 70
        assert bbox.center == (60.0, 45.0)
        assert bbox.area == 5000

    def test_to_xyxy(self):
        bbox = BoundingBox(x=10.5, y=20.7, width=100.2, height=50.3)
        assert bbox.to_xyxy() == (10, 20, 110, 70)

    def test_dilate(self):
        bbox = BoundingBox(x=10, y=10, width=100, height=50)
        dilated = bbox.dilate(5)
        assert dilated.x == 5
        assert dilated.y == 5
        assert dilated.width == 110
        assert dilated.height == 60

    def test_dilate_clamps_negative(self):
        bbox = BoundingBox(x=2, y=2, width=100, height=50)
        dilated = bbox.dilate(10)
        assert dilated.x == 0
        assert dilated.y == 0

    def test_from_points(self):
        points = [(10, 20), (110, 20), (110, 70), (10, 70)]
        bbox = BoundingBox.from_points(points)
        assert bbox.x == 10
        assert bbox.y == 20
        assert bbox.width == 100
        assert bbox.height == 50


class TestTextRegion:
    def test_defaults(self):
        region = TextRegion()
        assert region.region_id != ""
        assert region.raw_text == ""
        assert region.confidence == 0.0
        assert region.is_low_confidence is True  # confidence=0 < 0.5

    def test_high_confidence(self):
        region = TextRegion(confidence=0.9)
        assert region.is_low_confidence is False

    def test_has_translation(self):
        region = TextRegion(raw_text="Hello")
        assert not region.has_translation
        region.translated_text = "안녕하세요"
        assert region.has_translation

    def test_display_text(self):
        region = TextRegion(raw_text="Hello", translated_text="안녕")
        assert region.display_text == "안녕"
        region.translated_text = ""
        assert region.display_text == "Hello"


class TestProcessingJob:
    def test_initial_status(self):
        job = ProcessingJob()
        assert job.status == JobStatus.QUEUED
        assert job.progress == 0.0

    def test_start(self):
        job = ProcessingJob()
        job.start()
        assert job.status == JobStatus.OCR_RUNNING
        assert job.started_at is not None

    def test_complete(self):
        job = ProcessingJob()
        job.start()
        job.complete()
        assert job.status == JobStatus.COMPLETE
        assert job.progress == 1.0
        assert job.is_done is True

    def test_fail(self):
        job = ProcessingJob()
        job.fail("테스트 오류")
        assert job.status == JobStatus.FAILED
        assert job.error_message == "테스트 오류"

    def test_cancel(self):
        job = ProcessingJob()
        job.cancel()
        assert job.status == JobStatus.CANCELLED
        assert job.is_done is True


class TestTranslationResult:
    def test_success(self):
        result = TranslationResult(
            region_id="123",
            source_text="Hello",
            translated_text="안녕하세요",
            source_lang="en",
            target_lang="ko",
        )
        assert result.is_success is True
        assert result.is_empty is False

    def test_failure(self):
        result = TranslationResult(
            region_id="123",
            source_text="Hello",
            translated_text="",
            source_lang="en",
            target_lang="ko",
            error="API 오류",
        )
        assert result.is_success is False
        assert result.is_empty is True

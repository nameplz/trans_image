"""OCRService 단위 테스트."""
from __future__ import annotations

from src.models.text_region import BoundingBox, TextRegion
from src.services.ocr_service import OCRService


class TestOCRService:
    def setup_method(self):
        self.service = OCRService()

    def test_normalize_removes_empty(self):
        regions = [
            TextRegion(raw_text="Hello", confidence=0.9,
                       bbox=BoundingBox(0, 0, 100, 20)),
            TextRegion(raw_text="", confidence=0.8,
                       bbox=BoundingBox(0, 30, 100, 20)),
            TextRegion(raw_text="  ", confidence=0.7,
                       bbox=BoundingBox(0, 60, 100, 20)),
        ]
        result = self.service.normalize(regions)
        assert len(result) == 1
        assert result[0].raw_text == "Hello"

    def test_normalize_sets_reading_order(self):
        regions = [
            TextRegion(raw_text="B", confidence=0.9,
                       bbox=BoundingBox(0, 100, 100, 20)),
            TextRegion(raw_text="A", confidence=0.9,
                       bbox=BoundingBox(0, 0, 100, 20)),
        ]
        result = self.service.normalize(regions)
        # y 오름차순 정렬됨
        assert result[0].raw_text == "A"
        assert result[0].reading_order == 1
        assert result[1].raw_text == "B"
        assert result[1].reading_order == 2

    def test_normalize_flags_low_confidence(self):
        regions = [
            TextRegion(raw_text="Low", confidence=0.3,
                       bbox=BoundingBox(0, 0, 100, 20)),
            TextRegion(raw_text="High", confidence=0.9,
                       bbox=BoundingBox(0, 30, 100, 20)),
        ]
        result = self.service.normalize(regions)
        low = next(r for r in result if r.raw_text == "Low")
        high = next(r for r in result if r.raw_text == "High")
        assert low.is_low_confidence is True
        assert high.is_low_confidence is False

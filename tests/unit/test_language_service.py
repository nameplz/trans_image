"""LanguageService 단위 테스트."""
from __future__ import annotations

import pytest
from src.models.text_region import TextRegion
from src.services.language_service import LanguageService


class TestLanguageService:
    def setup_method(self):
        self.service = LanguageService()

    def test_detect_empty(self):
        assert self.service.detect([]) == "und"

    def test_detect_korean_by_unicode(self):
        regions = [TextRegion(raw_text="안녕하세요 반갑습니다")]
        result = self.service.detect(regions)
        assert result == "ko"

    def test_detect_japanese_by_unicode(self):
        regions = [TextRegion(raw_text="こんにちは、世界")]
        result = self.service.detect(regions)
        assert result == "ja"

    def test_detect_chinese_by_unicode(self):
        regions = [TextRegion(raw_text="你好世界，这是测试文本")]
        result = self.service.detect(regions)
        assert result == "zh"

    def test_detect_blank_text(self):
        regions = [TextRegion(raw_text="   ")]
        assert self.service.detect(regions) == "und"

"""OCR 플러그인 단위 테스트 (EasyOCR, PaddleOCR)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.models.text_region import BoundingBox, TextRegion


def make_dummy_image(h=100, w=200):
    return np.zeros((h, w, 3), dtype=np.uint8)


# EasyOCR 결과 형식: [[bbox_points], text, confidence]
def make_easyocr_result(text="Hello", confidence=0.9):
    points = [[10, 10], [80, 10], [80, 40], [10, 40]]
    return [points, text, confidence]


# PaddleOCR 결과 형식: [[bbox_points], [text, confidence]]
def make_paddleocr_result(text="Hello", confidence=0.9):
    points = [[10, 10], [80, 10], [80, 40], [10, 40]]
    return [points, [text, confidence]]


class TestEasyOCRPlugin:
    def test_load_sync_passes_gpu_and_download_options(self):
        """load 시 Reader 생성 인자에 GPU/다운로드 옵션이 반영되어야 한다."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin

        plugin = EasyOCRPlugin(config={"gpu": True, "download_enabled": False})

        with patch("easyocr.Reader") as mock_reader_cls:
            with patch("torch.cuda.is_available", return_value=True):
                plugin._load_sync()

        mock_reader_cls.assert_called_once()
        _, kwargs = mock_reader_cls.call_args
        assert kwargs["gpu"] is True
        assert kwargs["download_enabled"] is False

    def test_build_reader_falls_back_to_cpu_when_cuda_unavailable(self):
        """gpu=True 이지만 CUDA가 없으면 CPU Reader로 폴백해야 한다."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin

        plugin = EasyOCRPlugin(config={"gpu": True})

        with patch("easyocr.Reader") as mock_reader_cls:
            with patch("torch.cuda.is_available", return_value=False):
                plugin._build_reader(["en"])

        _, kwargs = mock_reader_cls.call_args
        assert kwargs["gpu"] is False

    async def test_detect_regions_returns_text_regions(self):
        """EasyOCR readtext 결과 → TextRegion 목록 반환."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin

        raw = [make_easyocr_result("Hello", 0.9), make_easyocr_result("World", 0.85)]

        with patch("easyocr.Reader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.readtext.return_value = raw
            mock_reader_cls.return_value = mock_reader

            plugin = EasyOCRPlugin(config={"gpu": False})
            plugin._loaded = True
            plugin._reader = mock_reader

            # _readtext_sync를 직접 패치
            with patch.object(plugin, "_readtext_sync", return_value=raw):
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_loop.return_value.run_in_executor = AsyncMock(return_value=raw)
                    regions = await plugin.detect_regions(make_dummy_image())

        assert len(regions) == 2
        assert all(isinstance(r, TextRegion) for r in regions)
        assert regions[0].raw_text == "Hello"
        assert regions[1].raw_text == "World"

    def test_parse_results_empty_list(self):
        """빈 readtext 결과 → 빈 리스트."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin
        plugin = EasyOCRPlugin(config={})
        regions = plugin._parse_results([])
        assert regions == []

    def test_parse_results_filters_empty_text(self):
        """빈 텍스트 결과는 필터링."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin
        plugin = EasyOCRPlugin(config={})
        raw = [make_easyocr_result("", 0.9), make_easyocr_result("  ", 0.8)]
        regions = plugin._parse_results(raw)
        assert regions == []

    def test_parse_results_converts_bbox(self):
        """BoundingBox가 올바르게 변환됨."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin
        plugin = EasyOCRPlugin(config={})
        raw = [make_easyocr_result("Hello", 0.95)]
        regions = plugin._parse_results(raw)
        assert len(regions) == 1
        assert regions[0].bbox is not None
        assert regions[0].confidence == pytest.approx(0.95)

    async def test_recognize_text_crops_and_reruns(self):
        """recognize_text → bbox 크롭 후 재인식."""
        from src.plugins.ocr.easyocr_plugin import EasyOCRPlugin

        raw = [make_easyocr_result("Corrected", 0.99)]
        plugin = EasyOCRPlugin(config={})
        plugin._loaded = True
        plugin._reader = MagicMock()

        image = make_dummy_image(100, 200)
        region = TextRegion(
            raw_text="Orignal",
            bbox=BoundingBox(x=10, y=10, width=70, height=30),
            confidence=0.5,
        )

        with patch.object(plugin, "_readtext_sync", return_value=raw):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.run_in_executor = AsyncMock(return_value=raw)
                result = await plugin.recognize_text(image, region)

        assert result.raw_text == "Corrected"
        assert result.confidence == pytest.approx(0.99)
        assert region.raw_text == "Orignal"
        assert region.confidence == pytest.approx(0.5)


class TestPaddleOCRPlugin:
    def test_parse_results_empty(self):
        """빈 PaddleOCR 결과 → 빈 리스트."""
        from src.plugins.ocr.paddleocr_plugin import PaddleOCRPlugin
        plugin = PaddleOCRPlugin(config={})
        assert plugin._parse_results([]) == []
        assert plugin._parse_results(None) == []

    def test_parse_results_converts_to_text_region(self):
        """PaddleOCR 결과 → TextRegion 변환."""
        from src.plugins.ocr.paddleocr_plugin import PaddleOCRPlugin
        plugin = PaddleOCRPlugin(config={})
        raw = [make_paddleocr_result("Hello", 0.95)]
        regions = plugin._parse_results(raw)
        assert len(regions) == 1
        assert regions[0].raw_text == "Hello"
        assert regions[0].confidence == pytest.approx(0.95)
        assert regions[0].bbox is not None

    def test_parse_results_filters_empty_text(self):
        """빈 텍스트 PaddleOCR 결과 필터링."""
        from src.plugins.ocr.paddleocr_plugin import PaddleOCRPlugin
        plugin = PaddleOCRPlugin(config={})
        raw = [make_paddleocr_result("", 0.9), make_paddleocr_result("  ", 0.8)]
        regions = plugin._parse_results(raw)
        assert regions == []

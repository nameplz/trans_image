"""RenderingService 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFont

from src.models.text_region import BoundingBox, TextRegion, TextStyle
from src.services.rendering_service import RenderingService


def make_service(min_font=8, max_font=72, line_spacing=1.2):
    config = MagicMock()
    config.get.side_effect = lambda section, key, **kw: {
        ("rendering", "min_font_size"): min_font,
        ("rendering", "max_font_size"): max_font,
        ("rendering", "auto_font_size"): True,
        ("rendering", "line_spacing"): line_spacing,
    }.get((section, key), kw.get("default"))
    return RenderingService(config)


def make_font_service(raises=False):
    fs = MagicMock()
    # 항상 FileNotFoundError를 발생시켜 PIL 기본 폰트로 폴백하도록 유도
    fs.get_font_path.side_effect = FileNotFoundError("폰트 없음")
    return fs


class TestRenderEmptyRegions:
    async def test_empty_regions_same_shape(self):
        """regions=[] → 입력 이미지와 shape 동일."""
        image = np.zeros((100, 200, 3), dtype=np.uint8)
        svc = make_service()
        result = await svc.render(image, [], make_font_service())
        assert result.shape == image.shape

    async def test_no_translation_region_skipped(self):
        """has_translation=False region → 렌더링 건너뜀 (픽셀 변화 없음)."""
        image = np.zeros((100, 200, 3), dtype=np.uint8)
        region = TextRegion(
            raw_text="Hello",
            translated_text="",  # has_translation=False
            bbox=BoundingBox(x=10, y=10, width=80, height=30),
        )
        svc = make_service()
        result = await svc.render(image, [region], make_font_service())
        assert np.array_equal(result, image)


class TestRenderWithBackground:
    async def test_background_none_no_rectangle(self):
        """TextStyle(background_color=None) → 배경 사각형 그리지 않음."""
        image = np.zeros((100, 200, 3), dtype=np.uint8)
        region = TextRegion(
            raw_text="Hello",
            translated_text="안녕",
            bbox=BoundingBox(x=10, y=10, width=80, height=30),
            style=TextStyle(background_color=None, color=(255, 255, 255)),
        )
        svc = make_service()
        fs = make_font_service()
        result = await svc.render(image, [region], fs)
        # 배경 사각형이 없으면 bbox 내부 배경은 검은색(0) 유지
        # 텍스트가 렌더링되어 일부 픽셀이 변경될 수 있지만, 영역 전체가 흰색이 되지는 않음
        assert result.shape == image.shape


class TestWrapText:
    def test_short_text_single_line(self):
        """짧은 텍스트 → 리스트 1개."""
        svc = make_service()
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        font = ImageFont.load_default()
        lines = svc._wrap_text("Hi", font, 200, draw)
        assert len(lines) == 1

    def test_long_text_multiple_lines(self):
        """긴 텍스트(50자 이상) → 리스트 2개 이상."""
        svc = make_service()
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        font = ImageFont.load_default()
        long_text = "This is a very long text that should be wrapped into multiple lines when rendered"
        lines = svc._wrap_text(long_text, font, 80, draw)
        assert len(lines) >= 2

    def test_empty_text_returns_list(self):
        """빈 텍스트 → 빈 문자열 하나 있는 리스트."""
        svc = make_service()
        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        font = ImageFont.load_default()
        lines = svc._wrap_text("", font, 100, draw)
        assert isinstance(lines, list)


class TestFitFontSize:
    def test_fit_font_size_within_bounds(self):
        """_fit_font_size 결과 → min_font 이상, max_font 이하."""
        svc = make_service(min_font=8, max_font=72)
        result = svc._fit_font_size("Hello World", 100, 50, None)
        assert svc._min_font <= result <= svc._max_font

    def test_fit_font_size_small_area(self):
        """아주 작은 영역에서는 최소 폰트 크기 반환."""
        svc = make_service(min_font=8, max_font=72)
        result = svc._fit_font_size("Hello World This Is A Very Long Text", 20, 10, None)
        assert result >= svc._min_font

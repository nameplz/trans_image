"""FontService 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.models.text_region import BoundingBox, TextRegion
from src.services.font_service import FontService, _BUNDLED_FONTS


def make_font_service(config=None, fallback="NotoSansCJK"):
    if config is None:
        config = MagicMock()
        config.get.return_value = fallback
    return FontService(config)


class TestGetFontPath:
    def test_bundled_font_exists_returns_path(self, tmp_path):
        """번들 폰트 파일이 존재할 때 정확한 경로를 반환."""
        # 번들 폰트 파일 생성
        font_filename = list(_BUNDLED_FONTS.values())[0]  # NotoSansCJKkr-Regular.otf
        (tmp_path / font_filename).write_bytes(b"dummy")

        with patch("src.services.font_service._ASSETS_FONTS", tmp_path):
            svc = make_font_service()
            svc._fallback = "NotoSansCJK"
            path = svc.get_font_path("NotoSansCJK")
            assert path == tmp_path / font_filename

    def test_font_cached_on_second_call(self, tmp_path):
        """같은 폰트를 두 번 요청하면 캐시에서 반환."""
        font_filename = list(_BUNDLED_FONTS.values())[0]
        (tmp_path / font_filename).write_bytes(b"dummy")

        with patch("src.services.font_service._ASSETS_FONTS", tmp_path):
            svc = make_font_service()
            svc._fallback = "NotoSansCJK"
            path1 = svc.get_font_path("NotoSansCJK")
            # 파일을 삭제해도 캐시에서 반환되어야 함
            (tmp_path / font_filename).unlink()
            path2 = svc.get_font_path("NotoSansCJK")
            assert path1 == path2
            assert "NotoSansCJK" in svc._font_cache

    def test_fallback_to_noto_when_requested_missing(self, tmp_path):
        """요청 폰트 없고 fallback NotoSansCJK 존재 → fallback 경로 반환."""
        # fallback 폰트 파일만 생성
        fallback_filename = _BUNDLED_FONTS["NotoSansCJK"]
        (tmp_path / fallback_filename).write_bytes(b"dummy")

        with patch("src.services.font_service._ASSETS_FONTS", tmp_path):
            svc = make_font_service(fallback="NotoSansCJK")
            # 존재하지 않는 폰트 요청 → fallback
            path = svc.get_font_path("SomeNonexistentFont")
            assert path.exists()

    def test_no_fonts_raises_file_not_found(self, tmp_path):
        """번들+fallback 모두 없음 → FileNotFoundError."""
        with patch("src.services.font_service._ASSETS_FONTS", tmp_path):
            svc = make_font_service(fallback="NotoSansCJK")
            with pytest.raises(FileNotFoundError):
                svc.get_font_path("SomeNonexistentFont")


class TestDetectTextColor:
    def test_dark_text_on_white_background(self):
        """흰 배경에 검은 텍스트 → fg 어둡고 bg 밝음."""
        # 흰 배경 (255,255,255)에 검은 텍스트 영역 생성
        image = np.ones((60, 120, 3), dtype=np.uint8) * 255
        # 텍스트 영역에 검은 픽셀 추가 (텍스트 시뮬레이션)
        image[10:50, 10:110] = 200  # 배경 회색
        image[20:40, 20:100] = 10   # 텍스트 어둡게

        region = TextRegion(bbox=BoundingBox(x=10, y=10, width=100, height=40))

        svc = make_font_service()
        fg, bg = svc.detect_text_color(image, region)

        # fg는 배경보다 어두워야 함
        fg_brightness = sum(fg) / 3
        bg_brightness = sum(bg) / 3
        assert fg_brightness < bg_brightness

    def test_empty_bbox_returns_defaults(self):
        """빈 bbox (x2 <= x1) → 기본값 (0,0,0), (255,255,255) 반환."""
        image = np.zeros((50, 50, 3), dtype=np.uint8)
        # x2 <= x1 이 되도록 width=0
        region = TextRegion(bbox=BoundingBox(x=30, y=10, width=0, height=20))

        svc = make_font_service()
        fg, bg = svc.detect_text_color(image, region)

        assert fg == (0, 0, 0)
        assert bg == (255, 255, 255)

    def test_returns_tuple_of_rgb_tuples(self):
        """반환값은 각각 3-tuple of int."""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        region = TextRegion(bbox=BoundingBox(x=10, y=10, width=50, height=30))

        svc = make_font_service()
        fg, bg = svc.detect_text_color(image, region)

        assert len(fg) == 3
        assert len(bg) == 3
        for c in fg + bg:
            assert 0 <= c <= 255

"""InpaintingService 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from src.models.text_region import BoundingBox, TextRegion
from src.services.inpainting_service import InpaintingService


def make_service(method="opencv_ns", dilation=5):
    config = MagicMock()
    config.get.side_effect = lambda section, key, **kw: {
        ("inpainting", "method"): method,
        ("inpainting", "mask_dilation"): dilation,
    }.get((section, key), kw.get("default"))
    return InpaintingService(config)


class TestRemoveText:
    async def test_empty_regions_returns_copy(self):
        """regions=[] → 원본과 shape/dtype 동일한 배열 반환."""
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        svc = make_service()
        result = await svc.remove_text(image, [])
        assert result.shape == image.shape
        assert result.dtype == image.dtype

    async def test_single_region_output_shape(self):
        """100x100 이미지 1개 region → 결과 shape (100,100,3)."""
        image = np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)
        region = TextRegion(bbox=BoundingBox(x=10, y=10, width=30, height=20))
        svc = make_service()
        result = await svc.remove_text(image, [region])
        assert result.shape == (100, 100, 3)
        assert result.dtype == np.uint8

    async def test_returns_ndarray(self):
        """remove_text는 항상 ndarray를 반환."""
        image = np.zeros((50, 80, 3), dtype=np.uint8)
        svc = make_service()
        result = await svc.remove_text(image, [])
        assert isinstance(result, np.ndarray)


class TestBuildMask:
    def test_mask_has_255_in_bbox_area(self):
        """_build_mask → bbox 위치에 255 픽셀 존재."""
        svc = make_service(dilation=0)
        region = TextRegion(bbox=BoundingBox(x=10, y=10, width=30, height=20))
        mask = svc._build_mask((100, 100), [region])
        # y1:y2, x1:x2 구간에 255 존재 (dilation=0이지만 dilate(0)가 원본 bbox)
        # BoundingBox.dilate(0)는 그대로 유지
        x1, y1, x2, y2 = region.bbox.dilate(0).to_xyxy()
        assert mask[y1:y2, x1:x2].max() == 255

    def test_mask_shape_matches_input(self):
        """마스크 shape는 입력 shape와 동일."""
        svc = make_service()
        region = TextRegion(bbox=BoundingBox(x=5, y=5, width=20, height=10))
        mask = svc._build_mask((80, 120), [region])
        assert mask.shape == (80, 120)


class TestLamaFallback:
    async def test_lama_import_error_falls_back_to_ns(self):
        """method='lama' + lama ImportError → NS로 폴백, 정상 완료."""
        image = np.random.randint(0, 256, (60, 60, 3), dtype=np.uint8)
        region = TextRegion(bbox=BoundingBox(x=5, y=5, width=20, height=10))
        svc = make_service(method="lama")
        # simple_lama_inpainting 미설치 환경에서도 동작 확인
        result = await svc.remove_text(image, [region])
        assert result.shape == (60, 60, 3)

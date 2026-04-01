"""image_utils 단위 테스트."""
from __future__ import annotations

import numpy as np
import pytest

from src.utils.image_utils import crop_region, cv2_to_pil, pil_to_cv2, resize_keep_aspect


class TestResizeKeepAspect:
    def test_landscape_resized_correctly(self):
        """300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨."""
        img = np.zeros((200, 300, 3), dtype=np.uint8)
        resized, scale = resize_keep_aspect(img, max_dim=100)
        h, w = resized.shape[:2]
        assert max(h, w) == 100
        assert abs(scale - (100 / 300)) < 0.01

    def test_portrait_resized_correctly(self):
        """200x300 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨."""
        img = np.zeros((300, 200, 3), dtype=np.uint8)
        resized, scale = resize_keep_aspect(img, max_dim=100)
        h, w = resized.shape[:2]
        assert max(h, w) == 100

    def test_small_image_not_upscaled(self):
        """max_dim 이하 이미지는 scale=1.0 반환, 원본 크기 유지."""
        img = np.zeros((50, 80, 3), dtype=np.uint8)
        resized, scale = resize_keep_aspect(img, max_dim=100)
        assert scale == 1.0
        assert resized.shape == img.shape

    def test_exact_max_dim_no_resize(self):
        """정확히 max_dim 크기 이미지는 그대로 반환."""
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        resized, scale = resize_keep_aspect(img, max_dim=100)
        assert scale == 1.0
        assert resized.shape[:2] == (100, 100)


class TestCropRegion:
    def test_normal_crop(self):
        """정상 범위 크롭."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = crop_region(img, 10, 10, 50, 60)
        assert cropped.shape == (50, 40, 3)

    def test_negative_coords_clipped(self):
        """음수 좌표는 0으로 클리핑."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = crop_region(img, -10, -10, 50, 50)
        assert cropped.shape == (50, 50, 3)

    def test_out_of_bounds_clipped(self):
        """이미지 크기 초과 좌표는 이미지 경계로 클리핑."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = crop_region(img, 150, 80, 300, 200)
        # x: 150~200=50, y: 80~100=20
        assert cropped.shape[0] == 20
        assert cropped.shape[1] == 50

    def test_fully_out_of_bounds_returns_empty(self):
        """완전히 범위 밖 → 빈 배열."""
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        cropped = crop_region(img, -10, -10, 0, 0)
        assert cropped.size == 0


class TestCv2PilRoundtrip:
    def test_roundtrip_preserves_shape(self):
        """cv2→PIL→cv2 변환 시 shape 보존."""
        bgr = np.random.randint(0, 256, (50, 80, 3), dtype=np.uint8)
        pil = cv2_to_pil(bgr)
        back = pil_to_cv2(pil)
        assert back.shape == bgr.shape
        assert back.dtype == bgr.dtype

    def test_pil_image_mode(self):
        """cv2_to_pil 결과는 RGB 모드 PIL 이미지."""
        bgr = np.zeros((10, 10, 3), dtype=np.uint8)
        pil = cv2_to_pil(bgr)
        assert pil.mode == "RGB"

"""cv2 ↔ Pillow 변환 헬퍼."""
from __future__ import annotations

import numpy as np


def cv2_to_pil(image: np.ndarray):
    """BGR numpy 배열 → PIL Image (RGB)."""
    from PIL import Image
    import cv2
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def pil_to_cv2(pil_image) -> np.ndarray:
    """PIL Image (RGB) → BGR numpy 배열."""
    import cv2
    rgb = np.array(pil_image)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def rgb_to_bgr(image: np.ndarray) -> np.ndarray:
    import cv2
    return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)


def bgr_to_rgb(image: np.ndarray) -> np.ndarray:
    import cv2
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def resize_keep_aspect(
    image: np.ndarray,
    max_dim: int,
) -> tuple[np.ndarray, float]:
    """긴 쪽이 max_dim을 넘지 않도록 리사이즈.

    Returns:
        (resized_image, scale_factor)
    """
    import cv2
    h, w = image.shape[:2]
    scale = min(max_dim / max(h, w), 1.0)
    if scale == 1.0:
        return image, 1.0
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return resized, scale


def crop_region(image: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
    """안전한 크롭 — 범위 자동 클리핑."""
    h, w = image.shape[:2]
    x1 = max(0, x1)
    y1 = max(0, y1)
    x2 = min(w, x2)
    y2 = min(h, y2)
    return image[y1:y2, x1:x2]

"""내보내기 옵션 데이터 모델."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ImageFormat(str, Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"


class ResizeMode(str, Enum):
    ORIGINAL = "original"
    SCALE_PERCENT = "scale_percent"
    LONG_EDGE = "long_edge"


@dataclass(frozen=True)
class ExportOptions:
    """저장 직전에만 적용되는 이미지 내보내기 옵션."""

    format: ImageFormat = ImageFormat.PNG
    jpeg_quality: int = 95
    webp_quality: int = 90
    png_compression: int = 3
    resize_mode: ResizeMode = ResizeMode.ORIGINAL
    resize_value: int = 100

"""이미지 저장 직전 옵션 적용 및 파일 저장."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from src.core.exceptions import ImageProcessingError
from src.models.export_options import ExportOptions, ImageFormat, ResizeMode


class ExportService:
    """포맷별 옵션과 리사이즈를 적용해 이미지를 저장한다."""

    def save_image(
        self,
        image: np.ndarray,
        path: Path,
        options: ExportOptions,
    ) -> Path:
        export_path = self._normalize_output_path(path, options.format)
        export_path.parent.mkdir(parents=True, exist_ok=True)

        processed = self._resize_image(image, options)
        bgr = cv2.cvtColor(processed, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(str(export_path), bgr, self._build_params(options))
        if not ok:
            raise ImageProcessingError(f"이미지 저장 실패: {export_path}")
        return export_path

    def _normalize_output_path(self, path: Path, image_format: ImageFormat) -> Path:
        suffix = {
            ImageFormat.PNG: ".png",
            ImageFormat.JPEG: ".jpg",
            ImageFormat.WEBP: ".webp",
        }[image_format]
        return path.with_suffix(suffix)

    def _resize_image(self, image: np.ndarray, options: ExportOptions) -> np.ndarray:
        if options.resize_mode == ResizeMode.ORIGINAL:
            return image.copy()

        height, width = image.shape[:2]
        if width <= 0 or height <= 0:
            raise ImageProcessingError("유효하지 않은 이미지 크기입니다.")

        if options.resize_mode == ResizeMode.SCALE_PERCENT:
            scale = max(1, int(options.resize_value)) / 100.0
            target_width = max(1, int(round(width * scale)))
            target_height = max(1, int(round(height * scale)))
        else:
            long_edge = max(1, int(options.resize_value))
            current_long_edge = max(width, height)
            scale = long_edge / current_long_edge
            target_width = max(1, int(round(width * scale)))
            target_height = max(1, int(round(height * scale)))

        if target_width == width and target_height == height:
            return image.copy()

        interpolation = cv2.INTER_AREA
        if target_width > width or target_height > height:
            interpolation = cv2.INTER_LINEAR

        return cv2.resize(
            image,
            (target_width, target_height),
            interpolation=interpolation,
        )

    def _build_params(self, options: ExportOptions) -> list[int]:
        if options.format == ImageFormat.JPEG:
            return [cv2.IMWRITE_JPEG_QUALITY, int(options.jpeg_quality)]
        if options.format == ImageFormat.WEBP:
            return [cv2.IMWRITE_WEBP_QUALITY, int(options.webp_quality)]
        if options.format == ImageFormat.PNG:
            return [cv2.IMWRITE_PNG_COMPRESSION, int(options.png_compression)]
        return []

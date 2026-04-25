"""ExportService 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from src.models.export_options import ExportOptions, ImageFormat, ResizeMode
from src.services.export_service import ExportService


class TestExportService:
    def test_jpeg_save_uses_quality_param(self, tmp_path):
        service = ExportService()
        image = np.zeros((10, 20, 3), dtype=np.uint8)
        out_path = tmp_path / "image.png"
        options = ExportOptions(format=ImageFormat.JPEG, jpeg_quality=88)

        with patch("src.services.export_service.cv2.imwrite", return_value=True) as mock_imwrite:
            saved_path = service.save_image(image, out_path, options)

        assert saved_path.suffix == ".jpg"
        params = mock_imwrite.call_args.args[2]
        assert params == [cv2.IMWRITE_JPEG_QUALITY, 88]

    def test_png_save_uses_compression_param(self, tmp_path):
        service = ExportService()
        image = np.zeros((10, 20, 3), dtype=np.uint8)
        options = ExportOptions(format=ImageFormat.PNG, png_compression=5)

        with patch("src.services.export_service.cv2.imwrite", return_value=True) as mock_imwrite:
            service.save_image(image, tmp_path / "image.png", options)

        params = mock_imwrite.call_args.args[2]
        assert params == [cv2.IMWRITE_PNG_COMPRESSION, 5]

    def test_resize_scale_percent_changes_output_shape(self, tmp_path):
        service = ExportService()
        image = np.zeros((20, 40, 3), dtype=np.uint8)
        options = ExportOptions(
            format=ImageFormat.PNG,
            resize_mode=ResizeMode.SCALE_PERCENT,
            resize_value=50,
        )

        with patch("src.services.export_service.cv2.imwrite", return_value=True):
            with patch("src.services.export_service.cv2.cvtColor", side_effect=lambda img, code: img):
                saved = service.save_image(image, tmp_path / "image.png", options)

        assert saved == tmp_path / "image.png"
        resized = service._resize_image(image, options)
        assert resized.shape[:2] == (10, 20)

    def test_resize_long_edge_preserves_original_image(self, tmp_path):
        service = ExportService()
        image = np.zeros((20, 40, 3), dtype=np.uint8)
        original = image.copy()
        options = ExportOptions(
            format=ImageFormat.WEBP,
            resize_mode=ResizeMode.LONG_EDGE,
            resize_value=80,
        )

        with patch("src.services.export_service.cv2.imwrite", return_value=True):
            service.save_image(image, tmp_path / "image.webp", options)

        assert np.array_equal(image, original)

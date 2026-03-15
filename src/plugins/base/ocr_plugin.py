"""AbstractOCRPlugin ABC."""
from __future__ import annotations

from abc import abstractmethod
from typing import Any

import numpy as np

from src.models.text_region import TextRegion
from src.plugins.base.plugin_base import PluginBase


class AbstractOCRPlugin(PluginBase):
    """OCR 플러그인 추상 기반 클래스."""

    PLUGIN_TYPE = "ocr"

    @abstractmethod
    async def detect_regions(
        self,
        image: np.ndarray,
        languages: list[str] | None = None,
    ) -> list[TextRegion]:
        """이미지에서 텍스트 영역을 탐지하고 TextRegion 목록 반환.

        Args:
            image: BGR 또는 RGB numpy 배열 (H, W, C)
            languages: OCR 힌트 언어 코드 목록 (None이면 자동)

        Returns:
            탐지된 TextRegion 목록 (bbox, raw_text, confidence 포함)
        """

    @abstractmethod
    async def recognize_text(
        self,
        image: np.ndarray,
        region: TextRegion,
    ) -> TextRegion:
        """특정 영역의 텍스트를 재인식 (수동 재처리용).

        Args:
            image: 전체 이미지
            region: 재처리할 TextRegion (bbox 기준으로 크롭)

        Returns:
            raw_text, confidence 업데이트된 TextRegion
        """

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "ocr",
            "plugin_name": self.PLUGIN_NAME,
        }

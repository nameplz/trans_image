"""PaddleOCR 플러그인 구현 (옵션)."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import numpy as np

from src.core.exceptions import OCRError
from src.models.text_region import BoundingBox, TextRegion
from src.plugins.base.ocr_plugin import AbstractOCRPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.ocr.paddleocr")

_executor = ThreadPoolExecutor(max_workers=1)


class PaddleOCRPlugin(AbstractOCRPlugin):
    PLUGIN_NAME = "paddleocr"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "PaddleOCR 기반 OCR (CJK 특화)"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._ocr = None
        self._use_gpu = self.get_config("use_gpu", False)
        self._lang = self.get_config("lang", "ch")

    async def load(self) -> None:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._load_sync)
        self._loaded = True
        logger.info("PaddleOCR 로드 완료")

    def _load_sync(self) -> None:
        try:
            from paddleocr import PaddleOCR
        except ImportError as e:
            raise OCRError(
                "paddleocr 미설치: pip install paddlepaddle paddleocr"
            ) from e
        self._ocr = PaddleOCR(
            use_angle_cls=True,
            lang=self._lang,
            use_gpu=self._use_gpu,
            show_log=False,
        )

    async def unload(self) -> None:
        self._ocr = None
        self._loaded = False

    def validate_config(self) -> list[str]:
        return []

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "ocr",
            "plugin_name": self.PLUGIN_NAME,
            "specialization": "CJK",
        }

    async def detect_regions(
        self,
        image: np.ndarray,
        languages: list[str] | None = None,
    ) -> list[TextRegion]:
        if not self._loaded or self._ocr is None:
            await self.load()

        loop = asyncio.get_event_loop()
        raw = await loop.run_in_executor(_executor, self._ocr_sync, image)
        return self._parse_results(raw)

    def _ocr_sync(self, image: np.ndarray) -> list:
        try:
            result = self._ocr.ocr(image, cls=True)
            return result[0] if result else []
        except Exception as e:
            raise OCRError(f"PaddleOCR 처리 실패: {e}") from e

    def _parse_results(self, raw: list) -> list[TextRegion]:
        """PaddleOCR 결과 형식: [[bbox_points], [text, confidence]]"""
        regions = []
        if not raw:
            return regions
        for item in raw:
            if not item:
                continue
            points, (text, conf) = item
            if not text.strip():
                continue
            bbox = BoundingBox.from_points([(p[0], p[1]) for p in points])
            regions.append(TextRegion(
                bbox=bbox,
                raw_text=text.strip(),
                confidence=float(conf),
            ))
        return regions

    async def recognize_text(
        self,
        image: np.ndarray,
        region: TextRegion,
    ) -> TextRegion:
        x1, y1, x2, y2 = region.bbox.to_xyxy()
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return region
        raw = await asyncio.get_event_loop().run_in_executor(
            _executor, self._ocr_sync, crop
        )
        parsed = self._parse_results(raw)
        if parsed:
            region.raw_text = parsed[0].raw_text
            region.confidence = parsed[0].confidence
        return region

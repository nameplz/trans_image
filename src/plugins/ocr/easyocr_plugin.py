"""EasyOCR 플러그인 구현."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from typing import Any

import numpy as np

from src.core.exceptions import OCRError
from src.models.text_region import BoundingBox, TextRegion
from src.plugins.base.ocr_plugin import AbstractOCRPlugin
from src.utils.logger import get_logger

logger = get_logger("trans_image.ocr.easyocr")

_executor = ThreadPoolExecutor(max_workers=1)


class EasyOCRPlugin(AbstractOCRPlugin):
    PLUGIN_NAME = "easyocr"
    PLUGIN_VERSION = "1.0.0"
    PLUGIN_DESCRIPTION = "EasyOCR 기반 OCR (80+ 언어 지원)"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._reader = None
        self._gpu = self.get_config("gpu", False)
        self._model_dir = self.get_config("model_storage_directory", None)
        self._download_enabled = self.get_config("download_enabled", True)
        self._readers: dict[tuple[str, ...], Any] = {}

    async def load(self) -> None:
        """EasyOCR Reader 초기화 (모델 다운로드 포함, 수 분 소요 가능)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._load_sync)
        self._loaded = True
        logger.info("EasyOCR 로드 완료 (GPU=%s)", self._gpu)

    def _load_sync(self) -> None:
        try:
            self._reader = self._get_or_create_reader(["en"])
        except ImportError as e:
            raise OCRError("easyocr 미설치: pip install easyocr") from e

    async def unload(self) -> None:
        self._reader = None
        self._readers = {}
        self._loaded = False
        logger.info("EasyOCR 언로드 완료")

    def validate_config(self) -> list[str]:
        return []  # EasyOCR는 API 키 불필요

    def get_capabilities(self) -> dict[str, Any]:
        return {
            "plugin_type": "ocr",
            "plugin_name": self.PLUGIN_NAME,
            "gpu_available": self._gpu,
            "max_languages": 80,
        }

    async def detect_regions(
        self,
        image: np.ndarray,
        languages: list[str] | None = None,
    ) -> list[TextRegion]:
        """이미지에서 텍스트 영역 탐지."""
        if not self._loaded or self._reader is None:
            await self.load()

        lang_list = languages or ["en"]
        loop = asyncio.get_event_loop()
        raw_results = await loop.run_in_executor(
            _executor,
            self._readtext_sync,
            image,
            lang_list,
        )
        return self._parse_results(raw_results)

    def _readtext_sync(self, image: np.ndarray, languages: list[str]) -> list:
        """동기 EasyOCR 호출."""
        try:
            reader = self._get_or_create_reader(languages)
            return reader.readtext(image, detail=1)
        except Exception as e:
            raise OCRError(f"EasyOCR 처리 실패: {e}") from e

    def _normalize_languages(self, languages: list[str] | None) -> tuple[str, ...]:
        normalized = tuple(languages or ["en"])
        return normalized or ("en",)

    def _get_or_create_reader(self, languages: list[str] | None) -> Any:
        lang_key = self._normalize_languages(languages)
        reader = self._readers.get(lang_key)
        if reader is not None:
            return reader

        reader = self._build_reader(list(lang_key))
        self._readers[lang_key] = reader
        if lang_key == ("en",):
            self._reader = reader
        return reader

    def _build_reader(self, languages: list[str]) -> Any:
        try:
            import easyocr
        except ImportError as e:
            raise OCRError("easyocr 미설치: pip install easyocr") from e

        use_gpu = bool(self._gpu)
        if use_gpu:
            try:
                import torch
            except ImportError:
                logger.warning("PyTorch 미설치로 EasyOCR GPU를 사용할 수 없어 CPU로 폴백합니다.")
                use_gpu = False
            else:
                if not torch.cuda.is_available():
                    logger.warning("CUDA 미지원 환경이라 EasyOCR를 CPU 모드로 실행합니다.")
                    use_gpu = False

        kwargs: dict[str, Any] = {
            "gpu": use_gpu,
            "download_enabled": self._download_enabled,
        }
        if self._model_dir:
            kwargs["model_storage_directory"] = self._model_dir
        return easyocr.Reader(languages, **kwargs)

    def _parse_results(self, raw_results: list) -> list[TextRegion]:
        """EasyOCR 결과 → TextRegion 목록 변환.

        EasyOCR 결과 형식: [[bbox_points], text, confidence]
        bbox_points: [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
        """
        regions = []
        for item in raw_results:
            points, text, confidence = item
            if not text.strip():
                continue

            bbox = BoundingBox.from_points([(p[0], p[1]) for p in points])
            region = TextRegion(
                bbox=bbox,
                raw_text=text.strip(),
                confidence=float(confidence),
            )
            regions.append(region)

        logger.debug("EasyOCR 결과: %d개 영역", len(regions))
        return regions

    async def recognize_text(
        self,
        image: np.ndarray,
        region: TextRegion,
    ) -> TextRegion:
        """특정 영역 텍스트 재인식."""
        x1, y1, x2, y2 = region.bbox.to_xyxy()
        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return region

        crops_results = await asyncio.get_event_loop().run_in_executor(
            _executor,
            self._readtext_sync,
            crop,
            ["en"],
        )
        if crops_results:
            _, text, confidence = crops_results[0]
            return replace(
                region,
                raw_text=text.strip(),
                confidence=float(confidence),
            )
        return region

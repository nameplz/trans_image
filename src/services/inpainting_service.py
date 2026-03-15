"""텍스트 제거 인페인팅 서비스 (OpenCV NS + LaMa 옵션)."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from src.core.config_manager import ConfigManager
from src.core.exceptions import InpaintingError
from src.models.text_region import TextRegion
from src.utils.logger import get_logger

logger = get_logger("trans_image.inpainting")

_executor = ThreadPoolExecutor(max_workers=2)


class InpaintingService:
    """이미지에서 텍스트 영역을 제거하고 배경을 복원."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._method = config.get("inpainting", "method") or "opencv_ns"
        self._dilation = int(config.get("inpainting", "mask_dilation") or 5)

    async def remove_text(
        self,
        image: np.ndarray,
        regions: list[TextRegion],
    ) -> np.ndarray:
        """비동기 래퍼 — 실제 처리는 스레드풀에서 실행."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._remove_text_sync,
            image,
            regions,
        )

    def _remove_text_sync(
        self,
        image: np.ndarray,
        regions: list[TextRegion],
    ) -> np.ndarray:
        """동기 인페인팅 처리."""
        try:
            import cv2
        except ImportError as e:
            raise InpaintingError("opencv-python 미설치") from e

        if not regions:
            return image.copy()

        # BGR 변환 (OpenCV 작업)
        is_rgb = True
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR) if is_rgb else image.copy()

        # 마스크 생성
        mask = self._build_mask(bgr.shape[:2], regions)

        if self._method == "lama":
            result_bgr = self._inpaint_lama(bgr, mask)
        else:
            result_bgr = self._inpaint_opencv_ns(bgr, mask)

        # RGB로 다시 변환
        return cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB) if is_rgb else result_bgr

    def _build_mask(
        self,
        shape: tuple[int, int],
        regions: list[TextRegion],
    ) -> np.ndarray:
        """텍스트 영역 마스크 생성 (흰색=인페인팅 대상)."""
        import cv2
        mask = np.zeros(shape, dtype=np.uint8)
        for region in regions:
            bbox = region.bbox.dilate(self._dilation)
            x1, y1, x2, y2 = bbox.to_xyxy()
            # 이미지 경계 클리핑
            h, w = shape
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if x2 > x1 and y2 > y1:
                mask[y1:y2, x1:x2] = 255

        # 마스크 팽창으로 스트로크까지 완전 제거
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.dilate(mask, kernel, iterations=1)
        return mask

    def _inpaint_opencv_ns(self, bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """OpenCV Navier-Stokes 인페인팅."""
        import cv2
        return cv2.inpaint(bgr, mask, inpaintRadius=3, flags=cv2.INPAINT_NS)

    def _inpaint_lama(self, bgr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """LaMa 딥러닝 인페인팅 (미설치 시 NS 폴백)."""
        try:
            # simple-lama-inpainting 패키지 지원
            from simple_lama_inpainting import SimpleLama
            lama = SimpleLama()
            from PIL import Image
            pil_img = Image.fromarray(bgr[:, :, ::-1])  # BGR→RGB
            pil_mask = Image.fromarray(mask)
            result = lama(pil_img, pil_mask)
            import numpy as np
            result_np = np.array(result)
            import cv2
            return cv2.cvtColor(result_np, cv2.COLOR_RGB2BGR)
        except ImportError:
            logger.warning("LaMa 미설치. OpenCV NS로 폴백.")
            return self._inpaint_opencv_ns(bgr, mask)

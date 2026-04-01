"""번역 텍스트 이미지 삽입 서비스."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from src.core.config_manager import ConfigManager
from src.core.exceptions import RenderingError
from src.models.text_region import TextRegion, TextDirection
from src.services.font_service import FontService
from src.utils.logger import get_logger

logger = get_logger("trans_image.rendering")

_executor = ThreadPoolExecutor(max_workers=2)


class RenderingService:
    """인페인팅된 이미지에 번역 텍스트를 삽입."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._min_font = int(config.get("rendering", "min_font_size") or 8)
        self._max_font = int(config.get("rendering", "max_font_size") or 72)
        self._auto_size = bool(config.get("rendering", "auto_font_size") if True else True)
        self._line_spacing = float(config.get("rendering", "line_spacing") or 1.2)

    async def render(
        self,
        image: np.ndarray,
        regions: list[TextRegion],
        font_service: FontService,
    ) -> np.ndarray:
        """비동기 래퍼."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            _executor,
            self._render_sync,
            image,
            regions,
            font_service,
        )

    def _render_sync(
        self,
        image: np.ndarray,
        regions: list[TextRegion],
        font_service: FontService,
    ) -> np.ndarray:
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError as e:
            raise RenderingError("Pillow 미설치") from e

        pil_img = Image.fromarray(image)
        draw = ImageDraw.Draw(pil_img)

        for region in regions:
            if not region.has_translation:
                continue
            try:
                self._render_region(draw, pil_img, region, font_service)
            except Exception as e:
                logger.warning("영역 렌더링 실패 (%s): %s", region.region_id[:8], e)

        return np.array(pil_img)

    def _render_region(
        self,
        draw,
        image,
        region: TextRegion,
        font_service: FontService,
    ) -> None:
        from PIL import ImageFont, ImageDraw

        text = region.translated_text
        bbox = region.bbox
        x1, y1, x2, y2 = bbox.to_xyxy()
        max_w = x2 - x1
        max_h = y2 - y1

        if max_w <= 0 or max_h <= 0:
            return

        # 폰트 경로 결정
        try:
            font_path = font_service.get_font_path(region.style.font_family)
            font_path_str = str(font_path)
        except FileNotFoundError:
            font_path_str = None  # PIL 기본 폰트

        # 폰트 크기 자동 조절 (이진 탐색)
        font_size = self._fit_font_size(
            text, max_w, max_h, font_path_str,
            initial=region.style.font_size,
        )

        # 폰트 로드
        try:
            font = (
                ImageFont.truetype(font_path_str, int(font_size))
                if font_path_str
                else ImageFont.load_default()
            )
        except Exception:
            font = ImageFont.load_default()

        # 색상
        fg_color = region.style.color
        bg_color = region.style.background_color

        # 배경 사각형 그리기 (선택적)
        if bg_color is not None:
            draw.rectangle([x1, y1, x2, y2], fill=bg_color)

        # 텍스트 줄바꿈 후 렌더링
        lines = self._wrap_text(text, font, max_w, draw)
        y_offset = y1
        for line in lines:
            if y_offset >= y2:
                break
            draw.text((x1, y_offset), line, font=font, fill=fg_color)
            bbox_line = draw.textbbox((x1, y_offset), line, font=font)
            line_h = (bbox_line[3] - bbox_line[1]) * self._line_spacing
            y_offset += int(line_h)

    def _fit_font_size(
        self,
        text: str,
        max_w: int,
        max_h: int,
        font_path: str | None,
        initial: float = 12.0,
    ) -> float:
        """이진 탐색으로 bbox에 맞는 최대 폰트 크기 반환."""
        from PIL import ImageFont, ImageDraw, Image

        dummy_img = Image.new("RGB", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)

        lo, hi = float(self._min_font), float(self._max_font)
        best = lo

        for _ in range(10):  # 최대 10 이터레이션
            mid = (lo + hi) / 2
            try:
                font = (
                    ImageFont.truetype(font_path, int(mid))
                    if font_path
                    else ImageFont.load_default()
                )
            except Exception:
                return best

            lines = self._wrap_text(text, font, max_w, dummy_draw)
            total_h = 0
            for line in lines:
                bb = dummy_draw.textbbox((0, 0), line, font=font)
                total_h += int((bb[3] - bb[1]) * self._line_spacing)

            if total_h <= max_h:
                best = mid
                lo = mid
            else:
                hi = mid

        return max(self._min_font, best)

    def _wrap_text(self, text: str, font, max_w: int, draw) -> list[str]:
        """텍스트를 max_w 안에 들어오도록 줄바꿈."""
        words = text.split()
        lines: list[str] = []
        current = ""

        for word in words:
            test = (current + " " + word).strip()
            bb = draw.textbbox((0, 0), test, font=font)
            if bb[2] - bb[0] <= max_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        return lines or [text]

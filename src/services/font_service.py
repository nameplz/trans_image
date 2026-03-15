"""폰트 매칭, 색상 감지, 시스템 폰트 조회."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from src.core.config_manager import ConfigManager
from src.models.text_region import TextRegion
from src.utils.logger import get_logger

logger = get_logger("trans_image.font_service")

_ASSETS_FONTS = Path(__file__).parent.parent.parent / "assets" / "fonts"

# 번들 폰트 파일 목록
_BUNDLED_FONTS = {
    "NotoSansCJK": "NotoSansCJKkr-Regular.otf",
    "NotoSansCJKBold": "NotoSansCJKkr-Bold.otf",
}


class FontService:
    """번역 텍스트 렌더링용 폰트 선택 및 색상 감지."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._fallback = config.get("rendering", "font_fallback") or "NotoSansCJK"
        self._font_cache: dict[str, Path] = {}

    def get_font_path(self, font_family: str | None = None) -> Path:
        """폰트 이름으로 폰트 파일 경로 반환.
        시스템 폰트 → 번들 폰트 → NotoSansCJK 순으로 폴백.
        """
        name = font_family or self._fallback
        if name in self._font_cache:
            return self._font_cache[name]

        # 번들 폰트 우선
        bundled = _ASSETS_FONTS / _BUNDLED_FONTS.get(name, _BUNDLED_FONTS.get(self._fallback, ""))
        if bundled.exists():
            self._font_cache[name] = bundled
            return bundled

        # 시스템 폰트 탐색
        sys_path = self._find_system_font(name)
        if sys_path:
            self._font_cache[name] = sys_path
            return sys_path

        # 최종 폴백: 번들 NotoSansCJK
        fallback_path = _ASSETS_FONTS / list(_BUNDLED_FONTS.values())[0]
        if fallback_path.exists():
            return fallback_path

        # PIL 기본 폰트 (비트맵, 최후 수단)
        raise FileNotFoundError(f"사용 가능한 폰트 없음: {name}")

    def _find_system_font(self, font_family: str) -> Optional[Path]:
        """시스템에 설치된 폰트 탐색."""
        try:
            from fonttools.ttLib import TTFont
            import platform
            search_dirs: list[Path] = []
            sys_name = platform.system()
            if sys_name == "Windows":
                search_dirs = [Path("C:/Windows/Fonts")]
            elif sys_name == "Darwin":
                search_dirs = [
                    Path("/Library/Fonts"),
                    Path.home() / "Library/Fonts",
                ]
            else:  # Linux
                search_dirs = [
                    Path("/usr/share/fonts"),
                    Path.home() / ".fonts",
                ]

            family_lower = font_family.lower()
            for d in search_dirs:
                if not d.exists():
                    continue
                for f in d.rglob("*.ttf"):
                    if family_lower in f.stem.lower():
                        return f
                for f in d.rglob("*.otf"):
                    if family_lower in f.stem.lower():
                        return f
        except Exception as e:
            logger.debug("시스템 폰트 탐색 실패: %s", e)
        return None

    def detect_text_color(
        self,
        image: np.ndarray,
        region: TextRegion,
    ) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
        """텍스트 영역에서 전경색·배경색 감지.

        Returns:
            (foreground_rgb, background_rgb)
        """
        bbox = region.bbox
        x1, y1, x2, y2 = bbox.to_xyxy()
        h, w = image.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        if x2 <= x1 or y2 <= y1:
            return (0, 0, 0), (255, 255, 255)

        crop = image[y1:y2, x1:x2]
        if crop.size == 0:
            return (0, 0, 0), (255, 255, 255)

        # 이진화로 전경/배경 분리
        try:
            import cv2
            gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            fg_mask = binary < 128
            bg_mask = ~fg_mask

            fg_pixels = crop[fg_mask]
            bg_pixels = crop[bg_mask]

            fg_color = tuple(int(c) for c in fg_pixels.mean(axis=0)) if len(fg_pixels) > 0 else (0, 0, 0)
            bg_color = tuple(int(c) for c in bg_pixels.mean(axis=0)) if len(bg_pixels) > 0 else (255, 255, 255)
            return fg_color, bg_color  # type: ignore[return-value]
        except Exception:
            return (0, 0, 0), (255, 255, 255)

"""언어 감지 서비스 (lingua-py 래퍼)."""
from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Optional

from src.models.text_region import TextRegion
from src.utils.logger import get_logger

logger = get_logger("trans_image.language_service")

# lingua Language → BCP-47 코드 매핑 (주요 언어)
_LINGUA_TO_BCP47: dict[str, str] = {
    "KOREAN": "ko",
    "ENGLISH": "en",
    "JAPANESE": "ja",
    "CHINESE": "zh",
    "FRENCH": "fr",
    "GERMAN": "de",
    "SPANISH": "es",
    "ITALIAN": "it",
    "PORTUGUESE": "pt",
    "RUSSIAN": "ru",
    "ARABIC": "ar",
    "THAI": "th",
    "VIETNAMESE": "vi",
    "INDONESIAN": "id",
}


class LanguageService:
    """페이지 전체 텍스트를 연결해 언어 감지."""

    def __init__(self) -> None:
        self._detector = None

    def _get_detector(self):
        if self._detector is None:
            try:
                from lingua import LanguageDetectorBuilder
                self._detector = (
                    LanguageDetectorBuilder.from_all_languages()
                    .with_preloaded_language_models()
                    .build()
                )
                logger.info("lingua 언어 감지기 초기화 완료")
            except ImportError:
                logger.warning("lingua-language-detector 미설치. 폴백 감지 사용.")
        return self._detector

    def detect(self, regions: list[TextRegion]) -> str:
        """TextRegion 목록에서 주 언어 코드(BCP-47) 반환.

        전략:
        1. Unicode 블록 분석으로 CJK 사전 필터링
        2. lingua-py로 감지
        3. 실패 시 "und" (undetermined) 반환
        """
        if not regions:
            return "und"

        combined_text = " ".join(r.raw_text for r in regions if r.raw_text.strip())
        if not combined_text.strip():
            return "und"

        # CJK 빠른 사전 필터
        cjk_lang = self._detect_by_unicode_block(combined_text)
        if cjk_lang:
            logger.debug("Unicode 블록으로 언어 감지: %s", cjk_lang)
            return cjk_lang

        detector = self._get_detector()
        if detector is None:
            return self._simple_detect(combined_text)

        try:
            result = detector.detect_language_of(combined_text)
            if result is None:
                return "und"
            lang_name = result.name  # 예: "KOREAN"
            bcp47 = _LINGUA_TO_BCP47.get(lang_name, lang_name.lower()[:2])
            logger.debug("lingua 감지 결과: %s → %s", lang_name, bcp47)
            return bcp47
        except Exception as e:
            logger.warning("언어 감지 실패: %s", e)
            return "und"

    def detect_single(self, text: str) -> str:
        """단일 텍스트 언어 감지."""
        regions = [TextRegion(raw_text=text)]
        return self.detect(regions)

    def _detect_by_unicode_block(self, text: str) -> Optional[str]:
        """Unicode 블록 비율로 CJK 언어 빠른 판별."""
        if not text:
            return None

        hangul = sum(1 for c in text if "\uAC00" <= c <= "\uD7A3" or "\u1100" <= c <= "\u11FF")
        hiragana_katakana = sum(
            1 for c in text if "\u3040" <= c <= "\u30FF"
        )
        cjk = sum(1 for c in text if "\u4E00" <= c <= "\u9FFF")
        total = len(text.replace(" ", ""))

        if total == 0:
            return None

        if hangul / total > 0.15:
            return "ko"
        if hiragana_katakana / total > 0.1:
            return "ja"
        if cjk / total > 0.2:
            return "zh"
        return None

    def _simple_detect(self, text: str) -> str:
        """lingua 미설치 시 간단한 폴백 감지."""
        result = self._detect_by_unicode_block(text)
        return result or "en"

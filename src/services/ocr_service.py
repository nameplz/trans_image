"""OCR 결과 정규화 서비스."""
from __future__ import annotations

from src.models.text_region import TextRegion
from src.utils.logger import get_logger

logger = get_logger("trans_image.ocr_service")


class OCRService:
    """OCR 플러그인 출력 정규화 및 후처리."""

    def normalize(self, regions: list[TextRegion]) -> list[TextRegion]:
        """정규화:
        - 빈 텍스트 영역 제거
        - 신뢰도 임계값 아래 영역 is_low_confidence 플래그 설정
        - reading_order 기본값 설정 (y 좌표 정렬)
        """
        filtered = [r for r in regions if r.raw_text.strip()]
        # y → x 순서로 기본 읽기 순서 부여
        sorted_regions = sorted(filtered, key=lambda r: (r.bbox.y, r.bbox.x))
        for idx, region in enumerate(sorted_regions):
            if region.reading_order == 0:
                region.reading_order = idx + 1
            # is_low_confidence 는 confidence < 0.5 로 자동 계산되는 프로퍼티이므로 별도 설정 불필요
        logger.debug("OCR 정규화: %d → %d 영역", len(regions), len(sorted_regions))
        return sorted_regions

    def merge_nearby(
        self,
        regions: list[TextRegion],
        gap_threshold: float = 10.0,
    ) -> list[TextRegion]:
        """인접한 TextRegion 병합 (같은 줄로 판단되는 경우).

        gap_threshold: 같은 줄로 판단하는 y 오차 픽셀
        """
        if not regions:
            return regions

        merged: list[TextRegion] = []
        used = [False] * len(regions)

        for i, r in enumerate(regions):
            if used[i]:
                continue
            group = [r]
            for j, other in enumerate(regions[i + 1:], start=i + 1):
                if used[j]:
                    continue
                same_line = abs(r.bbox.y - other.bbox.y) < gap_threshold
                adjacent = abs(r.bbox.x2 - other.bbox.x) < gap_threshold * 3
                if same_line and adjacent:
                    group.append(other)
                    used[j] = True

            if len(group) == 1:
                merged.append(r)
            else:
                merged.append(self._merge_group(group))
            used[i] = True

        return merged

    def _merge_group(self, group: list[TextRegion]) -> TextRegion:
        from src.models.text_region import BoundingBox
        xs = [r.bbox.x for r in group]
        ys = [r.bbox.y for r in group]
        x2s = [r.bbox.x2 for r in group]
        y2s = [r.bbox.y2 for r in group]
        merged_bbox = BoundingBox(
            x=min(xs), y=min(ys),
            width=max(x2s) - min(xs),
            height=max(y2s) - min(ys),
        )
        merged_text = " ".join(r.raw_text for r in group)
        avg_conf = sum(r.confidence for r in group) / len(group)
        base = group[0]
        base.bbox = merged_bbox
        base.raw_text = merged_text
        base.confidence = avg_conf
        return base

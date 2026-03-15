"""bbox_utils 단위 테스트."""
from __future__ import annotations

import pytest
from src.models.text_region import BoundingBox
from src.utils.bbox_utils import iou, merge_boxes, scale_bbox, is_inside, sort_reading_order


class TestIoU:
    def test_no_overlap(self):
        a = BoundingBox(0, 0, 10, 10)
        b = BoundingBox(20, 20, 10, 10)
        assert iou(a, b) == 0.0

    def test_full_overlap(self):
        a = BoundingBox(0, 0, 10, 10)
        assert iou(a, a) == pytest.approx(1.0)

    def test_partial_overlap(self):
        a = BoundingBox(0, 0, 10, 10)
        b = BoundingBox(5, 5, 10, 10)
        result = iou(a, b)
        assert 0 < result < 1


class TestMergeBoxes:
    def test_single(self):
        b = BoundingBox(5, 5, 10, 10)
        merged = merge_boxes([b])
        assert merged.x == 5
        assert merged.width == 10

    def test_multiple(self):
        boxes = [
            BoundingBox(0, 0, 10, 10),
            BoundingBox(5, 5, 20, 20),
        ]
        merged = merge_boxes(boxes)
        assert merged.x == 0
        assert merged.y == 0
        assert merged.x2 == 25
        assert merged.y2 == 25

    def test_empty(self):
        merged = merge_boxes([])
        assert merged.area == 0


class TestScaleBbox:
    def test_scale_up(self):
        b = BoundingBox(10, 10, 100, 50)
        scaled = scale_bbox(b, 2.0)
        assert scaled.x == 20
        assert scaled.width == 200


class TestSortReadingOrder:
    def test_ltr_order(self):
        boxes = [
            BoundingBox(100, 0, 10, 10),  # 두 번째 줄 오른쪽
            BoundingBox(0, 0, 10, 10),    # 첫 번째 줄 왼쪽
            BoundingBox(50, 0, 10, 10),   # 첫 번째 줄 중간
        ]
        order = sort_reading_order(boxes)
        # 왼쪽(0) → 중간(50) → 오른쪽(100)
        assert order == [1, 2, 0]

    def test_empty(self):
        assert sort_reading_order([]) == []

"""바운딩박스 수학 유틸리티."""
from __future__ import annotations

from src.models.text_region import BoundingBox


def iou(a: BoundingBox, b: BoundingBox) -> float:
    """두 바운딩박스의 IoU (Intersection over Union) 계산."""
    x_left = max(a.x, b.x)
    y_top = max(a.y, b.y)
    x_right = min(a.x2, b.x2)
    y_bottom = min(a.y2, b.y2)

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    inter_area = (x_right - x_left) * (y_bottom - y_top)
    union_area = a.area + b.area - inter_area
    return inter_area / union_area if union_area > 0 else 0.0


def merge_boxes(boxes: list[BoundingBox]) -> BoundingBox:
    """여러 박스를 감싸는 최소 경계 박스 반환."""
    if not boxes:
        return BoundingBox(0, 0, 0, 0)
    xs = [b.x for b in boxes]
    ys = [b.y for b in boxes]
    x2s = [b.x2 for b in boxes]
    y2s = [b.y2 for b in boxes]
    x = min(xs)
    y = min(ys)
    return BoundingBox(x=x, y=y, width=max(x2s) - x, height=max(y2s) - y)


def scale_bbox(bbox: BoundingBox, scale: float) -> BoundingBox:
    """스케일 팩터 적용."""
    return BoundingBox(
        x=bbox.x * scale,
        y=bbox.y * scale,
        width=bbox.width * scale,
        height=bbox.height * scale,
        rotation=bbox.rotation,
    )


def is_inside(inner: BoundingBox, outer: BoundingBox, threshold: float = 0.8) -> bool:
    """inner가 outer 안에 threshold 이상 포함되는지 확인."""
    x_left = max(inner.x, outer.x)
    y_top = max(inner.y, outer.y)
    x_right = min(inner.x2, outer.x2)
    y_bottom = min(inner.y2, outer.y2)

    if x_right < x_left or y_bottom < y_top:
        return False

    inter = (x_right - x_left) * (y_bottom - y_top)
    return (inter / inner.area) >= threshold if inner.area > 0 else False


def sort_reading_order(
    boxes: list[BoundingBox],
    right_to_left: bool = False,
    line_height_factor: float = 0.5,
) -> list[int]:
    """박스 목록을 읽기 순서로 정렬한 인덱스 반환.

    Args:
        boxes: 정렬할 박스 목록
        right_to_left: True이면 만화 등 오른쪽→왼쪽 순서
        line_height_factor: 같은 줄로 판단하는 높이 오차 비율

    Returns:
        정렬된 원래 인덱스 목록
    """
    if not boxes:
        return []

    avg_h = sum(b.height for b in boxes) / len(boxes)
    threshold = avg_h * line_height_factor

    indexed = list(enumerate(boxes))
    # y 기준 1차 정렬
    indexed.sort(key=lambda t: t[1].y)

    # 같은 줄 그룹화
    lines: list[list[tuple[int, BoundingBox]]] = []
    for idx, box in indexed:
        placed = False
        for line in lines:
            if abs(box.y - line[0][1].y) < threshold:
                line.append((idx, box))
                placed = True
                break
        if not placed:
            lines.append([(idx, box)])

    # 각 줄 내 x 정렬
    result = []
    for line in lines:
        line.sort(key=lambda t: t[1].x, reverse=right_to_left)
        result.extend(idx for idx, _ in line)
    return result

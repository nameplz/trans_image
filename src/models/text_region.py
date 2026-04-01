"""텍스트 영역 및 바운딩 박스 데이터 모델."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TextDirection(Enum):
    LTR = "ltr"
    RTL = "rtl"
    VERTICAL = "vertical"


@dataclass
class TextStyle:
    """텍스트 렌더링 스타일."""

    font_family: str = ""
    font_size: float = 12.0
    color: tuple[int, int, int] = (0, 0, 0)
    background_color: tuple[int, int, int] | None = None
    bold: bool = False
    italic: bool = False


@dataclass
class BoundingBox:
    """이미지 내 사각형 영역 (x, y: 좌상단 좌표)."""

    x: float = 0.0
    y: float = 0.0
    width: float = 0.0
    height: float = 0.0
    rotation: float = 0.0

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2, self.y + self.height / 2)

    @property
    def area(self) -> float:
        return self.width * self.height

    def to_xyxy(self) -> tuple[int, int, int, int]:
        """(x1, y1, x2, y2) 정수 튜플 반환 (각 좌표를 독립적으로 int 변환)."""
        return (int(self.x), int(self.y), int(self.x) + int(self.width), int(self.y) + int(self.height))

    def dilate(self, amount: float) -> "BoundingBox":
        """모든 방향으로 amount 픽셀 확장 (음수 좌표는 0으로 클램프)."""
        return BoundingBox(
            x=max(0.0, self.x - amount),
            y=max(0.0, self.y - amount),
            width=self.width + amount * 2,
            height=self.height + amount * 2,
        )

    @classmethod
    def from_points(cls, points: list[tuple[float, float]]) -> "BoundingBox":
        """점 목록에서 바운딩 박스 생성."""
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x = min(xs)
        y = min(ys)
        return cls(x=x, y=y, width=max(xs) - x, height=max(ys) - y)


@dataclass
class TextRegion:
    """OCR 이 탐지한 텍스트 영역."""

    region_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw_text: str = ""
    translated_text: str = ""
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None
    source_lang_code: str = ""
    context_hint: str = ""
    reading_order: int = 0
    needs_review: bool = False
    direction: TextDirection = field(default=TextDirection.LTR)
    style: TextStyle = field(default_factory=TextStyle)

    @property
    def is_low_confidence(self) -> bool:
        return self.confidence < 0.5

    @property
    def has_translation(self) -> bool:
        return bool(self.translated_text)

    @property
    def display_text(self) -> str:
        return self.translated_text if self.translated_text else self.raw_text

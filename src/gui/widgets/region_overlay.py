"""바운딩박스 오버레이 QGraphicsItem."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
)

from src.models.text_region import TextRegion


class RegionOverlayItem(QGraphicsRectItem):
    """단일 TextRegion 바운딩박스를 표시하는 QGraphicsItem.

    ScrollHandDrag 충돌 방지를 위해 mousePressEvent를 오버라이드한다.
    클릭 시 등록된 콜백으로 region_id를 전달한다.
    """

    # 색상 테마
    COLOR_NORMAL = QColor(0, 120, 255, 120)        # 파란색 (정상)
    COLOR_LOW_CONF = QColor(255, 140, 0, 120)       # 주황색 (저신뢰도)
    COLOR_NEEDS_REVIEW = QColor(220, 50, 50, 120)   # 빨간색 (검증 실패)
    COLOR_SELECTED = QColor(255, 255, 0, 160)       # 노란색 (선택됨)
    COLOR_TRANSLATED = QColor(0, 200, 80, 100)      # 초록색 (번역 완료)

    def __init__(self, region: TextRegion, parent=None) -> None:
        bbox = region.bbox
        super().__init__(bbox.x, bbox.y, bbox.width, bbox.height, parent)
        self._region = region
        self._selected_flag = False
        self._selection_callback: Callable[[str], None] | None = None
        self._update_appearance()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setToolTip(f"원문: {region.raw_text}\n번역: {region.translated_text}")

    def region(self) -> TextRegion:
        return self._region

    def set_selection_callback(self, callback: Callable[[str], None]) -> None:
        """클릭 시 호출할 콜백 등록. callback(region_id: str)."""
        self._selection_callback = callback

    def update_region(self, region: TextRegion) -> None:
        self._region = region
        bbox = region.bbox
        self.setRect(QRectF(bbox.x, bbox.y, bbox.width, bbox.height))
        self._update_appearance()
        self.setToolTip(f"원문: {region.raw_text}\n번역: {region.translated_text}")

    def set_selected_flag(self, selected: bool) -> None:
        self._selected_flag = selected
        self._update_appearance()

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """좌클릭 시 콜백으로 region_id 전달. ScrollHandDrag 패닝 차단."""
        event.accept()
        if event.button() == Qt.MouseButton.LeftButton:
            if self._selection_callback is not None:
                self._selection_callback(self._region.region_id)
        super().mousePressEvent(event)

    def _update_appearance(self) -> None:
        r = self._region
        if self._selected_flag:
            color = self.COLOR_SELECTED
        elif r.needs_review:
            color = self.COLOR_NEEDS_REVIEW
        elif r.is_low_confidence:
            color = self.COLOR_LOW_CONF
        elif r.has_translation:
            color = self.COLOR_TRANSLATED
        else:
            color = self.COLOR_NORMAL

        pen = QPen(color.darker(150), 2)
        brush = QBrush(color)
        self.setPen(pen)
        self.setBrush(brush)


class RegionOverlayManager(QObject):
    """씬의 모든 RegionOverlayItem 관리.

    QObject를 상속하여 region_selected 시그널을 제공한다.
    아이템 클릭 시 이 시그널이 발행된다.
    """

    region_selected = Signal(str)  # region_id

    def __init__(self, scene) -> None:
        super().__init__()
        self._scene = scene
        self._items: dict[str, RegionOverlayItem] = {}

    def add_region(self, region: TextRegion) -> RegionOverlayItem:
        item = RegionOverlayItem(region)
        item.set_selection_callback(self._on_item_clicked)
        self._scene.addItem(item)
        self._items[region.region_id] = item
        return item

    def _on_item_clicked(self, region_id: str) -> None:
        self.region_selected.emit(region_id)

    def update_region(self, region: TextRegion) -> None:
        if region.region_id in self._items:
            self._items[region.region_id].update_region(region)

    def remove_region(self, region_id: str) -> None:
        item = self._items.pop(region_id, None)
        if item:
            self._scene.removeItem(item)

    def clear(self) -> None:
        for item in self._items.values():
            self._scene.removeItem(item)
        self._items.clear()

    def set_regions(self, regions: list[TextRegion]) -> None:
        self.clear()
        for r in regions:
            self.add_region(r)

    def select(self, region_id: str) -> None:
        for rid, item in self._items.items():
            item.set_selected_flag(rid == region_id)

    def get_item(self, region_id: str) -> RegionOverlayItem | None:
        return self._items.get(region_id)

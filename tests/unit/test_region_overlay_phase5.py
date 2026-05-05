"""RegionOverlayItem Phase 5 단위 테스트.

5-1: mousePressEvent 오버라이드 — ScrollHandDrag 충돌 방지
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGraphicsScene

from src.gui.widgets.region_overlay import RegionOverlayItem, RegionOverlayManager
from src.models.text_region import BoundingBox, TextRegion


# ── 픽스처 ────────────────────────────────────────────────────────────────────

def make_region(region_id: str = "test-id") -> TextRegion:
    return TextRegion(
        region_id=region_id,
        raw_text="Hello",
        translated_text="안녕",
        confidence=0.9,
        bbox=BoundingBox(x=10, y=10, width=100, height=50),
    )


# ── RegionOverlayItem.set_selection_callback ──────────────────────────────────

class TestRegionOverlayItemSelectionCallback:
    def test_item_has_set_selection_callback(self, qtbot):
        """RegionOverlayItem이 set_selection_callback 메서드를 가져야 한다."""
        scene = QGraphicsScene()
        region = make_region()
        item = RegionOverlayItem(region)
        scene.addItem(item)

        assert hasattr(item, "set_selection_callback")
        assert callable(item.set_selection_callback)

    def test_item_has_mousePressEvent_override(self, qtbot):
        """RegionOverlayItem이 mousePressEvent 오버라이드를 가져야 한다."""
        scene = QGraphicsScene()
        region = make_region()
        item = RegionOverlayItem(region)
        scene.addItem(item)

        assert "mousePressEvent" in type(item).__dict__

    def test_callback_called_on_left_click_simulation(self, qtbot):
        """좌클릭 시 등록된 콜백이 region_id와 함께 호출되어야 한다."""
        scene = QGraphicsScene()
        region = make_region("click-test-id")
        item = RegionOverlayItem(region)
        scene.addItem(item)

        received_ids = []
        item.set_selection_callback(lambda rid: received_ids.append(rid))

        # 내부 콜백 직접 호출로 테스트 (Qt 이벤트 스택 없이)
        item._selection_callback(region.region_id)

        assert received_ids == ["click-test-id"]

    def test_no_callback_by_default(self, qtbot):
        """기본적으로 콜백이 None이어야 한다."""
        scene = QGraphicsScene()
        region = make_region()
        item = RegionOverlayItem(region)
        scene.addItem(item)

        assert item._selection_callback is None

    def test_callback_can_be_overwritten(self, qtbot):
        """콜백을 덮어쓸 수 있어야 한다."""
        scene = QGraphicsScene()
        region = make_region()
        item = RegionOverlayItem(region)
        scene.addItem(item)

        first_calls = []
        second_calls = []

        item.set_selection_callback(lambda rid: first_calls.append(rid))
        item.set_selection_callback(lambda rid: second_calls.append(rid))

        item._selection_callback(region.region_id)

        assert first_calls == []
        assert second_calls == [region.region_id]

    def test_mousePressEvent_left_click_triggers_callback(self, qtbot):
        """mousePressEvent에서 좌클릭 시 콜백이 호출되는 로직이 구현되어야 한다."""
        scene = QGraphicsScene()
        region = make_region("left-click-id")
        item = RegionOverlayItem(region)
        scene.addItem(item)

        received_ids = []
        item.set_selection_callback(lambda rid: received_ids.append(rid))

        # Qt 이벤트 없이 내부 로직을 직접 테스트
        # mousePressEvent의 조건 분기 로직을 패치로 검증
        event_mock = MagicMock()
        event_mock.button.return_value = Qt.MouseButton.LeftButton

        with patch.object(type(item).__bases__[0], "mousePressEvent"):
            item.mousePressEvent(event_mock)

        assert received_ids == ["left-click-id"]

    def test_mousePressEvent_right_click_does_not_trigger_callback(self, qtbot):
        """우클릭 시 콜백이 호출되지 않아야 한다."""
        scene = QGraphicsScene()
        region = make_region("right-click-id")
        item = RegionOverlayItem(region)
        scene.addItem(item)

        received_ids = []
        item.set_selection_callback(lambda rid: received_ids.append(rid))

        event_mock = MagicMock()
        event_mock.button.return_value = Qt.MouseButton.RightButton

        with patch.object(type(item).__bases__[0], "mousePressEvent"):
            item.mousePressEvent(event_mock)

        assert received_ids == []

    def test_mousePressEvent_no_callback_does_not_crash(self, qtbot):
        """콜백이 없을 때 클릭해도 크래시가 없어야 한다."""
        scene = QGraphicsScene()
        region = make_region()
        item = RegionOverlayItem(region)
        scene.addItem(item)

        event_mock = MagicMock()
        event_mock.button.return_value = Qt.MouseButton.LeftButton

        with patch.object(type(item).__bases__[0], "mousePressEvent"):
            # 크래시 없이 실행되어야 함
            item.mousePressEvent(event_mock)

    def test_mousePressEvent_calls_accept(self, qtbot):
        """mousePressEvent가 event.accept()를 호출해야 한다."""
        scene = QGraphicsScene()
        region = make_region()
        item = RegionOverlayItem(region)
        scene.addItem(item)

        event_mock = MagicMock()
        event_mock.button.return_value = Qt.MouseButton.LeftButton

        with patch.object(type(item).__bases__[0], "mousePressEvent"):
            item.mousePressEvent(event_mock)

        event_mock.accept.assert_called_once()


# ── RegionOverlayManager selection 시그널 ─────────────────────────────────────

class TestRegionOverlayManagerSelectionSignal:
    def test_manager_has_region_selected_signal(self, qtbot):
        """RegionOverlayManager에 region_selected 시그널이 존재해야 한다."""
        scene = QGraphicsScene()
        manager = RegionOverlayManager(scene)
        assert hasattr(manager, "region_selected")

    def test_manager_is_qobject(self, qtbot):
        """RegionOverlayManager가 QObject를 상속해야 한다."""
        from PySide6.QtCore import QObject
        scene = QGraphicsScene()
        manager = RegionOverlayManager(scene)
        assert isinstance(manager, QObject)

    def test_manager_emits_region_selected_via_callback(self, qtbot):
        """아이템 콜백 → manager.region_selected 시그널 발행이 연결되어 있어야 한다."""
        scene = QGraphicsScene()
        manager = RegionOverlayManager(scene)
        region = make_region("manager-signal-test")
        manager.add_region(region)

        received = []
        manager.region_selected.connect(lambda rid: received.append(rid))

        item = manager.get_item("manager-signal-test")
        assert item is not None

        # 아이템 콜백 직접 호출 — _on_item_clicked을 통해 시그널이 발행되어야 함
        item._selection_callback("manager-signal-test")

        assert received == ["manager-signal-test"]

    def test_add_region_connects_callback_to_manager(self, qtbot):
        """add_region() 후 아이템의 콜백이 manager._on_item_clicked에 연결되어야 한다."""
        scene = QGraphicsScene()
        manager = RegionOverlayManager(scene)
        region = make_region("cb-test")
        manager.add_region(region)

        item = manager.get_item("cb-test")
        assert item._selection_callback is not None

    def test_clear_removes_all_items(self, qtbot):
        """clear() 후 모든 아이템이 제거되어야 한다."""
        scene = QGraphicsScene()
        manager = RegionOverlayManager(scene)
        for i in range(3):
            manager.add_region(make_region(f"region-{i}"))

        manager.clear()

        assert len(manager._items) == 0

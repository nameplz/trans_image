"""ImageViewer 위젯 단위 테스트 — 줌/패닝/이미지 로드 동작 검증."""
from __future__ import annotations

import numpy as np
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QPixmap, QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsPixmapItem

from src.gui.widgets.image_viewer import ImageViewer


class TestImageViewer:
    def test_set_image_creates_pixmap_item(self, qtbot, sample_image):
        """set_image() 호출 후 씬에 QGraphicsPixmapItem이 존재해야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        viewer.set_image(sample_image)

        items = viewer.scene_ref.items()
        assert any(isinstance(item, QGraphicsPixmapItem) for item in items)

    def test_set_image_updates_scene_rect(self, qtbot, sample_image):
        """set_image() 후 sceneRect가 이미지 크기(200x100)와 일치해야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        viewer.set_image(sample_image)

        rect = viewer.scene_ref.sceneRect()
        # sample_image shape=(100, 200, 3) → w=200, h=100
        assert rect.width() == pytest.approx(200.0)
        assert rect.height() == pytest.approx(100.0)

    def test_zoom_in_increases_zoom(self, qtbot):
        """zoom_in() 호출 후 내부 _zoom 값이 증가해야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        initial_zoom = viewer._zoom
        viewer.zoom_in()

        assert viewer._zoom > initial_zoom

    def test_zoom_out_decreases_zoom(self, qtbot):
        """zoom_out() 호출 후 내부 _zoom 값이 감소해야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        initial_zoom = viewer._zoom
        viewer.zoom_out()

        assert viewer._zoom < initial_zoom

    def test_zoom_reset_restores_default(self, qtbot):
        """zoom_in 여러 번 후 zoom_reset() 호출 시 _zoom이 1.0으로 복원되어야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        viewer.zoom_in()
        viewer.zoom_in()
        viewer.zoom_in()
        assert viewer._zoom != pytest.approx(1.0)

        viewer.zoom_reset()

        assert viewer._zoom == pytest.approx(1.0)

    def test_fit_in_view_no_crash_without_image(self, qtbot):
        """이미지 없이 fit_in_view() 호출해도 예외가 발생하지 않아야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        # _pixmap_item is None 상태에서 호출
        viewer.fit_in_view()  # should not raise

    def test_wheel_event_zooms_in(self, qtbot):
        """양의 angleDelta를 가진 WheelEvent 발생 시 _zoom이 증가해야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)
        viewer.show()

        initial_zoom = viewer._zoom

        # QWheelEvent 생성 (Qt6 시그니처)
        event = QWheelEvent(
            QPointF(0, 0),          # position
            QPointF(0, 0),          # globalPosition
            QPoint(0, 0),           # pixelDelta
            QPoint(0, 120),         # angleDelta (양수 → zoom in)
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        viewer.wheelEvent(event)

        assert viewer._zoom > initial_zoom

    def test_zoom_changed_signal_emitted_on_zoom_in(self, qtbot):
        """zoom_in() 호출 시 zoom_changed signal이 emit되어야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        emitted: list[float] = []
        viewer.zoom_changed.connect(emitted.append)

        viewer.zoom_in()

        assert len(emitted) == 1
        assert emitted[0] > 1.0

    def test_zoom_changed_signal_emitted_on_reset(self, qtbot):
        """zoom_reset() 호출 시 zoom_changed signal이 1.0으로 emit되어야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        viewer.zoom_in()

        emitted: list[float] = []
        viewer.zoom_changed.connect(emitted.append)

        viewer.zoom_reset()

        assert len(emitted) == 1
        assert emitted[0] == pytest.approx(1.0)

    def test_set_image_called_twice_reuses_pixmap_item(self, qtbot, sample_image):
        """set_image() 두 번 호출해도 씬에 pixmap 아이템이 1개만 존재해야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        viewer.set_image(sample_image)
        viewer.set_image(sample_image)

        items = [i for i in viewer.scene_ref.items() if isinstance(i, QGraphicsPixmapItem)]
        assert len(items) == 1

    def test_zoom_clamped_at_minimum(self, qtbot):
        """연속 zoom_out으로 _zoom_min(0.05) 아래로 내려가지 않아야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        for _ in range(100):
            viewer.zoom_out()

        assert viewer._zoom >= viewer._zoom_min

    def test_zoom_clamped_at_maximum(self, qtbot):
        """연속 zoom_in으로 _zoom_max(20.0) 위로 올라가지 않아야 한다."""
        viewer = ImageViewer()
        qtbot.addWidget(viewer)

        for _ in range(100):
            viewer.zoom_in()

        assert viewer._zoom <= viewer._zoom_max

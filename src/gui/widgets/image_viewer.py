"""줌/패닝 지원 QGraphicsView 이미지 뷰어."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QImage, QPixmap, QWheelEvent, QKeyEvent
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsView,
    QGraphicsPixmapItem,
)


class ImageViewer(QGraphicsView):
    """드래그 패닝, 휠 줌 지원 이미지 뷰어."""

    zoom_changed = Signal(float)  # 현재 줌 배율

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item: QGraphicsPixmapItem | None = None
        self._zoom = 1.0
        self._zoom_step = 1.15
        self._zoom_min = 0.05
        self._zoom_max = 20.0

        self.setScene(self._scene)
        self.setRenderHints(
            self.renderHints()
            | self.renderHints().Antialiasing
            | self.renderHints().SmoothPixmapTransform
        )
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(Qt.GlobalColor.darkGray)

    def set_image(self, image: np.ndarray) -> None:
        """numpy RGB 배열 → 뷰어에 표시."""
        h, w, ch = image.shape
        bytes_per_line = ch * w
        fmt = QImage.Format.Format_RGB888 if ch == 3 else QImage.Format.Format_RGBA8888
        qimg = QImage(image.data, w, h, bytes_per_line, fmt)
        pixmap = QPixmap.fromImage(qimg)

        if self._pixmap_item is None:
            self._pixmap_item = self._scene.addPixmap(pixmap)
        else:
            self._pixmap_item.setPixmap(pixmap)

        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fit_in_view()

    def set_pixmap(self, pixmap: QPixmap) -> None:
        if self._pixmap_item is None:
            self._pixmap_item = self._scene.addPixmap(pixmap)
        else:
            self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))

    def fit_in_view(self) -> None:
        """이미지를 뷰포트에 맞게 축소/확대."""
        if self._pixmap_item is None:
            return
        self.fitInView(self._pixmap_item, Qt.AspectRatioMode.KeepAspectRatio)
        self._zoom = self.transform().m11()
        self.zoom_changed.emit(self._zoom)

    def zoom_in(self) -> None:
        self._apply_zoom(self._zoom_step)

    def zoom_out(self) -> None:
        self._apply_zoom(1 / self._zoom_step)

    def zoom_reset(self) -> None:
        self.resetTransform()
        self._zoom = 1.0
        self.zoom_changed.emit(self._zoom)

    def _apply_zoom(self, factor: float) -> None:
        new_zoom = self._zoom * factor
        new_zoom = max(self._zoom_min, min(self._zoom_max, new_zoom))
        actual = new_zoom / self._zoom
        self.scale(actual, actual)
        self._zoom = new_zoom
        self.zoom_changed.emit(self._zoom)

    def wheelEvent(self, event: QWheelEvent) -> None:
        delta = event.angleDelta().y()
        if delta > 0:
            self._apply_zoom(self._zoom_step)
        elif delta < 0:
            self._apply_zoom(1 / self._zoom_step)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Plus:
            self.zoom_in()
        elif event.key() == Qt.Key.Key_Minus:
            self.zoom_out()
        elif event.key() == Qt.Key.Key_0:
            self.fit_in_view()
        else:
            super().keyPressEvent(event)

    @property
    def scene_ref(self) -> QGraphicsScene:
        return self._scene

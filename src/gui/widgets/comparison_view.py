"""원본/번역 비교 뷰 (슬라이더 방식)."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
    QSplitter,
)

from src.gui.widgets.image_viewer import ImageViewer


class ComparisonView(QWidget):
    """원본과 번역 이미지를 나란히 비교."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 라벨
        from PySide6.QtWidgets import QHBoxLayout
        label_row = QHBoxLayout()
        label_row.addWidget(QLabel("원본"), alignment=Qt.AlignmentFlag.AlignCenter)
        label_row.addWidget(QLabel("번역"), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(label_row)

        # 분할 뷰
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._original_view = ImageViewer()
        self._translated_view = ImageViewer()
        splitter.addWidget(self._original_view)
        splitter.addWidget(self._translated_view)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)

    def set_images(
        self,
        original: np.ndarray,
        translated: np.ndarray,
    ) -> None:
        self._original_view.set_image(original)
        self._translated_view.set_image(translated)

    def set_original(self, image: np.ndarray) -> None:
        self._original_view.set_image(image)

    def set_translated(self, image: np.ndarray) -> None:
        self._translated_view.set_image(image)

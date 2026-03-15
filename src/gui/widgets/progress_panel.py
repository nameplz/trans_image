"""처리 단계 진행 표시 패널."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class ProgressPanel(QWidget):
    """파이프라인 처리 진행 상태 표시."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._status_label = QLabel("대기 중")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        layout.addWidget(self._progress_bar)

        self._message_label = QLabel("")
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._message_label)

    def update_progress(self, progress: float, message: str) -> None:
        """progress: 0.0 ~ 1.0"""
        pct = int(progress * 100)
        self._progress_bar.setValue(pct)
        self._message_label.setText(message)

    def set_status(self, status_label: str) -> None:
        self._status_label.setText(status_label)

    def reset(self) -> None:
        self._progress_bar.setValue(0)
        self._status_label.setText("대기 중")
        self._message_label.setText("")

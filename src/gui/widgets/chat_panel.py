"""채팅 패널 위젯 — @경로 멘션으로 배치 번역을 지시하는 대화형 UI."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import (
    QCompleter,
    QFileSystemModel,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.utils.logger import get_logger

logger = get_logger("trans_image.gui.chat_panel")


class _MessageBubble(QFrame):
    """단일 채팅 메시지 버블."""

    def __init__(self, role: str, content: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._role = role
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        label = QLabel(content)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        if self._role == "user":
            label.setAlignment(Qt.AlignRight)
            label.setStyleSheet(
                "background:#2b5278; color:white; border-radius:8px; padding:6px;"
            )
            layout.addStretch()
            layout.addWidget(label)
        elif self._role == "system":
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color:#888; font-style:italic; padding:2px;")
            layout.addWidget(label)
        else:  # assistant
            label.setAlignment(Qt.AlignLeft)
            label.setStyleSheet(
                "background:#3c3c3c; color:#ddd; border-radius:8px; padding:6px;"
            )
            layout.addWidget(label)
            layout.addStretch()


class _ChatInput(QLineEdit):
    """@를 입력하면 경로 자동완성을 표시하는 입력창."""

    submit = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setPlaceholderText("메시지 입력... (@경로 로 디렉토리 지정, Enter로 전송)")
        self._fs_model = QFileSystemModel()
        self._fs_model.setRootPath("")
        self._completer = QCompleter(self._fs_model, self)
        self._completer.setCompletionMode(QCompleter.PopupCompletion)
        self.textChanged.connect(self._on_text_changed)

    def _on_text_changed(self, text: str) -> None:
        # @ 이후의 토큰을 찾아서 자동완성 시작
        at_idx = text.rfind("@")
        if at_idx == -1:
            self.setCompleter(None)
            return
        token = text[at_idx + 1:]
        if not token or " " in token:
            self.setCompleter(None)
            return
        # 자동완성을 활성화하고 현재 토큰으로 필터
        self.setCompleter(self._completer)
        self._completer.setCompletionPrefix(token)
        if self._completer.completionCount() > 0:
            self._completer.complete()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text().strip()
            if text:
                self.submit.emit(text)
                self.clear()
            return
        super().keyPressEvent(event)


class ChatPanel(QWidget):
    """채팅 기반 배치 번역 인터페이스 패널.

    사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해
    파이프라인을 실행하고 결과를 채팅 형식으로 표시한다.
    """

    message_sent = Signal(str)
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()
        self._progress_bar: QProgressBar | None = None

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 메시지 목록 스크롤 영역
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)

        self._msg_container = QWidget()
        self._msg_layout = QVBoxLayout(self._msg_container)
        self._msg_layout.setContentsMargins(4, 4, 4, 4)
        self._msg_layout.setSpacing(4)
        self._msg_layout.addStretch()
        self._scroll.setWidget(self._msg_container)
        layout.addWidget(self._scroll)

        # 하단 입력 영역
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(4, 4, 4, 4)

        self._input = _ChatInput()
        self._input.submit.connect(self._on_submit)

        self._stop_btn = QPushButton("중단")
        self._stop_btn.setFixedWidth(60)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.cancel_requested)

        bottom_layout.addWidget(self._input)
        bottom_layout.addWidget(self._stop_btn)
        layout.addWidget(bottom)

    # ── 공개 메서드 ─────────────────────────────────────────────────────────

    def add_message(self, role: str, content: str) -> None:
        """채팅 메시지를 추가한다."""
        bubble = _MessageBubble(role, content)
        # stretch 앞에 삽입
        count = self._msg_layout.count()
        self._msg_layout.insertWidget(count - 1, bubble)
        self._scroll_to_bottom()

    def set_batch_running(self, running: bool) -> None:
        """배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화."""
        self._input.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        if running:
            self._show_progress_bar()
        else:
            self._hide_progress_bar()

    def update_progress(self, current: int, total: int) -> None:
        if self._progress_bar:
            self._progress_bar.setMaximum(total)
            self._progress_bar.setValue(current)

    # ── 내부 메서드 ─────────────────────────────────────────────────────────

    def _on_submit(self, text: str) -> None:
        self.add_message("user", text)
        self.message_sent.emit(text)

    def _show_progress_bar(self) -> None:
        if self._progress_bar is not None:
            return
        self._progress_bar = QProgressBar()
        self._progress_bar.setTextVisible(True)
        count = self._msg_layout.count()
        self._msg_layout.insertWidget(count - 1, self._progress_bar)

    def _hide_progress_bar(self) -> None:
        if self._progress_bar is None:
            return
        self._msg_layout.removeWidget(self._progress_bar)
        self._progress_bar.deleteLater()
        self._progress_bar = None

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

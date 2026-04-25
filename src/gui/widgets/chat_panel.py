"""채팅 패널 위젯 — @경로 멘션으로 배치 번역을 지시하는 대화형 UI."""
from __future__ import annotations

from PySide6.QtCore import QTimer, Qt, Signal
from PySide6.QtGui import QKeyEvent
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
        self.setProperty("messageRole", role)
        self._setup_ui(content)

    def _setup_ui(self, content: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self._label = QLabel(content)
        self._label.setObjectName("messageLabel")
        self._label.setProperty("messageRole", self._role)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        if self._role == "user":
            self._label.setAlignment(Qt.AlignRight)
            layout.addStretch()
            layout.addWidget(self._label)
        elif self._role == "system":
            self._label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self._label)
        else:  # assistant
            self._label.setAlignment(Qt.AlignLeft)
            layout.addWidget(self._label)
            layout.addStretch()

    @property
    def content(self) -> str:
        return self._label.text()

    def append_content(self, chunk: str) -> None:
        self._label.setText(self._label.text() + chunk)

    def set_content(self, content: str) -> None:
        self._label.setText(content)


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
        self.setObjectName("chatPanel")
        self._setup_ui()
        self._progress_bar: QProgressBar | None = None
        self._stream_bubble: _MessageBubble | None = None
        self._stream_pending = ""
        self._stream_timer = QTimer(self)
        self._stream_timer.setInterval(20)
        self._stream_timer.timeout.connect(self._drain_stream_chunk)

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

    def start_stream(self, role: str) -> None:
        """스트리밍 메시지를 시작한다. 기존 미완료 스트림은 즉시 마무리한다."""
        if self._stream_bubble is not None:
            self.finish_stream()
        self._stream_pending = ""
        self._stream_bubble = _MessageBubble(role, "")
        count = self._msg_layout.count()
        self._msg_layout.insertWidget(count - 1, self._stream_bubble)
        self._scroll_to_bottom()

    def append_stream_chunk(self, chunk: str) -> None:
        """현재 스트리밍 메시지에 chunk를 추가한다."""
        if self._stream_bubble is None:
            self.start_stream("assistant")
        self._stream_pending += chunk
        if not self._stream_timer.isActive():
            self._stream_timer.start()

    def finish_stream(self) -> None:
        """현재 스트리밍 메시지를 즉시 완료한다."""
        if self._stream_bubble is None:
            return
        if self._stream_pending:
            self._stream_bubble.append_content(self._stream_pending)
            self._stream_pending = ""
        self._stream_timer.stop()
        self._stream_bubble = None
        self._scroll_to_bottom()

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

    def _drain_stream_chunk(self) -> None:
        if self._stream_bubble is None:
            self._stream_timer.stop()
            self._stream_pending = ""
            return
        if not self._stream_pending:
            self._stream_timer.stop()
            return
        step = min(3, len(self._stream_pending))
        next_chunk = self._stream_pending[:step]
        self._stream_pending = self._stream_pending[step:]
        self._stream_bubble.append_content(next_chunk)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

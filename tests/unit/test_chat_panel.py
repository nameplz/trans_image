"""ChatPanel / _ChatInput 단위 테스트 — Signal 동작 및 자동완성 로직."""
from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from src.gui.widgets.chat_panel import ChatPanel, _ChatInput


class TestChatPanelSignals:
    def test_message_sent_on_enter(self, qtbot):
        """Enter 키 → message_sent signal emit, 입력창 초기화."""
        panel = ChatPanel()
        qtbot.addWidget(panel)

        messages: list[str] = []
        panel.message_sent.connect(messages.append)

        panel._input.setText("안녕하세요")
        QTest.keyClick(panel._input, Qt.Key_Return)

        assert messages == ["안녕하세요"]
        assert panel._input.text() == ""

    def test_empty_input_not_sent(self, qtbot):
        """공백만 있는 입력은 message_sent를 emit하지 않음."""
        panel = ChatPanel()
        qtbot.addWidget(panel)

        messages: list[str] = []
        panel.message_sent.connect(messages.append)

        panel._input.setText("   ")
        QTest.keyClick(panel._input, Qt.Key_Return)

        assert messages == []

    def test_cancel_requested_on_stop_button(self, qtbot):
        """중단 버튼 클릭 → cancel_requested signal emit."""
        panel = ChatPanel()
        qtbot.addWidget(panel)
        panel.set_batch_running(True)

        cancelled: list[int] = []
        panel.cancel_requested.connect(lambda: cancelled.append(1))

        QTest.mouseClick(panel._stop_btn, Qt.LeftButton)

        assert cancelled == [1]

    def test_set_batch_running_toggles_controls(self, qtbot):
        """set_batch_running(True) → 입력 비활성화, 중단 버튼 활성화."""
        panel = ChatPanel()
        qtbot.addWidget(panel)

        panel.set_batch_running(True)
        assert not panel._input.isEnabled()
        assert panel._stop_btn.isEnabled()

        panel.set_batch_running(False)
        assert panel._input.isEnabled()
        assert not panel._stop_btn.isEnabled()


class TestChatInputCompleter:
    def test_at_prefix_enables_completer(self, qtbot):
        """'@경로' 입력 → completer 활성화."""
        inp = _ChatInput()
        qtbot.addWidget(inp)

        inp.setText("@/tmp")

        assert inp.completer() is not None

    def test_no_at_sign_removes_completer(self, qtbot):
        """'@' 없는 텍스트 → completer None."""
        inp = _ChatInput()
        qtbot.addWidget(inp)

        inp.setText("hello")

        assert inp.completer() is None

    def test_space_after_at_removes_completer(self, qtbot):
        """'@경로 ' (토큰에 공백) → completer 제거."""
        inp = _ChatInput()
        qtbot.addWidget(inp)

        inp.setText("@/tmp ")

        assert inp.completer() is None

    def test_empty_token_after_at_removes_completer(self, qtbot):
        """'@' 직후 아무것도 없으면 completer 제거."""
        inp = _ChatInput()
        qtbot.addWidget(inp)

        inp.setText("@")

        assert inp.completer() is None

"""MainWindow 단위 테스트 — H-4 이전 BatchWorker 미정리."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.gui.main_window import MainWindow


def make_main_window(qtbot):
    """테스트용 MainWindow 생성 — 모든 의존성 Mock 처리."""
    config = MagicMock()
    config.get.return_value = "anthropic"
    config.get_api_key.return_value = ""

    plugin_manager = MagicMock()
    pipeline = MagicMock()
    session = MagicMock()

    with patch("src.gui.main_window.WorkerPool"):
        window = MainWindow(
            config=config,
            plugin_manager=plugin_manager,
            pipeline=pipeline,
            session=session,
        )
    qtbot.addWidget(window)
    return window


class TestOnChatMessageEarlyReturn:
    def test_ignores_message_while_running(self, qtbot):
        """이전 배치가 실행 중일 때 새 메시지를 무시하고 안내 메시지를 발행해야 한다."""
        window = make_main_window(qtbot)

        # 이전 워커가 실행 중인 상태 모킹
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        window._batch_worker = mock_worker

        # 채팅 패널의 add_message 추적
        window._chat_panel.add_message = MagicMock()

        with patch("src.gui.main_window.BatchWorker") as MockBatchWorker:
            window._on_chat_message("@./images 한국어로 번역해줘")

        # 새 워커가 생성되지 않아야 함
        MockBatchWorker.assert_not_called()
        # 안내 메시지가 발행되어야 함
        window._chat_panel.add_message.assert_called_once()
        args = window._chat_panel.add_message.call_args[0]
        assert args[0] == "system"
        assert "실행 중" in args[1]

    def test_accepts_message_when_not_running(self, qtbot):
        """이전 배치가 없거나 완료된 상태이면 새 워커를 정상 생성해야 한다."""
        window = make_main_window(qtbot)

        # 워커 없는 상태 (초기)
        assert window._batch_worker is None

        mock_worker = MagicMock()
        with patch("src.gui.main_window.BatchWorker", return_value=mock_worker) as MockBatchWorker:
            window._on_chat_message("@./images 한국어로 번역해줘")

        MockBatchWorker.assert_called_once()
        mock_worker.start.assert_called_once()

    def test_accepts_message_after_previous_finished(self, qtbot):
        """이전 워커가 완료(isRunning=False)된 상태이면 새 워커를 생성해야 한다."""
        window = make_main_window(qtbot)

        # 이전 워커가 완료된 상태
        mock_old_worker = MagicMock()
        mock_old_worker.isRunning.return_value = False
        window._batch_worker = mock_old_worker

        mock_new_worker = MagicMock()
        with patch("src.gui.main_window.BatchWorker", return_value=mock_new_worker) as MockBatchWorker:
            window._on_chat_message("@./images 한국어로 번역해줘")

        MockBatchWorker.assert_called_once()
        mock_new_worker.start.assert_called_once()


class TestOnBatchCompleted:
    def test_clears_batch_worker_after_completion(self, qtbot):
        """배치 완료 후 _batch_worker 필드가 None으로 초기화되어야 한다."""
        window = make_main_window(qtbot)

        mock_worker = MagicMock()
        window._batch_worker = mock_worker

        result = MagicMock()
        result.output_dir = MagicMock()

        window._on_batch_completed(result)

        assert window._batch_worker is None

    def test_updates_last_directory_after_completion(self, qtbot):
        """배치 완료 후 _chat_session.last_directory가 result.output_dir로 갱신되어야 한다."""
        from pathlib import Path
        window = make_main_window(qtbot)

        output_dir = Path("/tmp/images_translated")
        result = MagicMock()
        result.output_dir = output_dir

        window._on_batch_completed(result)

        assert window._chat_session.last_directory == output_dir

    def test_does_not_set_last_directory_without_output_dir(self, qtbot):
        """result에 output_dir이 없으면 last_directory를 갱신하지 않아야 한다."""
        window = make_main_window(qtbot)

        result = object()  # output_dir 속성 없음

        window._on_batch_completed(result)

        assert window._chat_session.last_directory is None

"""BatchWorker._run_batch 에러 경로 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.chat.conversation import ConversationSession, ParsedMessage
from src.gui.workers.batch_worker import BatchWorker


def _make_parsed(directory_path: Path | None = None, target_lang: str = "ko") -> ParsedMessage:
    return ParsedMessage(
        raw_text="",
        directory_path=directory_path,
        target_lang=target_lang,
        translator_id=None,
        agent_id=None,
        output_dir=None,
        use_agent=None,
        intent=None,
    )


@pytest.fixture
def session() -> ConversationSession:
    return ConversationSession()


@pytest.fixture
def pipeline() -> MagicMock:
    return MagicMock()


class TestRunBatchErrorPaths:
    async def test_clarification_emits_agent_message(self, qtbot, session, pipeline):
        """resolve_params가 clarification을 반환하면 agent_message emit 후 종료."""
        parsed = _make_parsed(directory_path=None, target_lang="ko")
        worker = BatchWorker(parsed=parsed, session=session, pipeline=pipeline, chat_config={})

        messages: list[str] = []
        worker.agent_message.connect(messages.append)

        with patch("src.gui.workers.batch_worker.ChatAgent") as MockAgent:
            MockAgent.return_value.resolve_params.return_value = (parsed, "경로를 알려주세요")
            await worker._run_batch()

        assert len(messages) == 1
        assert "경로" in messages[0]

    async def test_file_not_found_emits_agent_message(self, qtbot, session, pipeline, tmp_path):
        """scan_directory가 FileNotFoundError를 발생시키면 agent_message emit."""
        parsed = _make_parsed(directory_path=tmp_path, target_lang="ko")
        worker = BatchWorker(parsed=parsed, session=session, pipeline=pipeline, chat_config={})

        messages: list[str] = []
        worker.agent_message.connect(messages.append)

        with patch("src.gui.workers.batch_worker.ChatAgent") as MockAgent, \
             patch("src.gui.workers.batch_worker.BatchProcessor") as MockProcessor:
            MockAgent.return_value.resolve_params.return_value = (parsed, None)
            MockProcessor.return_value.scan_directory.side_effect = FileNotFoundError("없음")
            await worker._run_batch()

        assert len(messages) == 1
        assert "찾을 수 없습니다" in messages[0]

    async def test_no_images_emits_agent_message(self, qtbot, session, pipeline, tmp_path):
        """scan_directory가 빈 리스트를 반환하면 agent_message emit."""
        parsed = _make_parsed(directory_path=tmp_path, target_lang="ko")
        worker = BatchWorker(parsed=parsed, session=session, pipeline=pipeline, chat_config={})

        messages: list[str] = []
        worker.agent_message.connect(messages.append)

        with patch("src.gui.workers.batch_worker.ChatAgent") as MockAgent, \
             patch("src.gui.workers.batch_worker.BatchProcessor") as MockProcessor:
            MockAgent.return_value.resolve_params.return_value = (parsed, None)
            MockProcessor.return_value.scan_directory.return_value = []
            await worker._run_batch()

        assert len(messages) == 1
        assert "이미지 파일이 없습니다" in messages[0]

    async def test_cancelled_skips_batch_completed(self, qtbot, session, pipeline, tmp_path):
        """배치 실행 중 취소되면 batch_completed signal을 emit하지 않음."""
        img = tmp_path / "test.png"
        img.touch()
        parsed = _make_parsed(directory_path=tmp_path, target_lang="ko")
        worker = BatchWorker(parsed=parsed, session=session, pipeline=pipeline, chat_config={})

        completed: list = []
        worker.batch_completed.connect(completed.append)

        async def fake_run_batch(jobs, pipeline, on_progress):
            worker._cancelled = True
            return MagicMock()

        with patch("src.gui.workers.batch_worker.ChatAgent") as MockAgent, \
             patch("src.gui.workers.batch_worker.BatchProcessor") as MockProcessor:
            MockAgent.return_value.resolve_params.return_value = (parsed, None)
            MockAgent.return_value.format_start.return_value = "시작"
            MockProcessor.return_value.scan_directory.return_value = [img]
            MockProcessor.return_value.create_batch_jobs.return_value = [MagicMock()]
            MockProcessor.return_value.run_batch = fake_run_batch
            await worker._run_batch()

        assert completed == []

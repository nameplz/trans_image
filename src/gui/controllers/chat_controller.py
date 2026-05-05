"""GUI chat orchestration controller."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from PySide6.QtCore import QObject, Signal

from src.chat.conversation import ConversationSession, ParsedMessage
from src.chat.message_parser import MessageParser
from src.core.config_manager import ConfigManager
from src.core.pipeline import Pipeline


class ChatController(QObject):
    system_message = Signal(str)
    agent_message = Signal(str)
    agent_stream_chunk = Signal(str)
    agent_stream_finished = Signal()
    batch_running_changed = Signal(bool)
    batch_progress = Signal(int, int)
    batch_completed = Signal(object)

    def __init__(
        self,
        config: ConfigManager,
        pipeline: Pipeline,
        *,
        message_parser: MessageParser | None = None,
        conversation_session: ConversationSession | None = None,
        batch_worker_factory: Callable[..., Any],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._pipeline = pipeline
        self._msg_parser = message_parser or MessageParser()
        self._chat_session = conversation_session or ConversationSession()
        self._batch_worker: Any | None = None
        self._chat_stream_active = False
        self._batch_worker_factory = batch_worker_factory

    @property
    def batch_worker(self) -> Any | None:
        return self._batch_worker

    @batch_worker.setter
    def batch_worker(self, value: Any | None) -> None:
        self._batch_worker = value

    @property
    def chat_session(self) -> ConversationSession:
        return self._chat_session

    @chat_session.setter
    def chat_session(self, value: ConversationSession) -> None:
        self._chat_session = value

    @property
    def chat_stream_active(self) -> bool:
        return self._chat_stream_active

    @chat_stream_active.setter
    def chat_stream_active(self, value: bool) -> None:
        self._chat_stream_active = value

    def submit_message(self, text: str, *, cwd: Path | None = None, parent: QObject | None = None) -> bool:
        parsed = self._msg_parser.parse(text, cwd or Path.cwd())
        return self._start_batch_worker(parsed, parent=parent)

    def submit_directory_batch(
        self,
        directory: Path,
        settings: Mapping[str, Any],
        *,
        parent: QObject | None = None,
    ) -> bool:
        parsed = ParsedMessage(
            raw_text=f"@{directory}",
            directory_path=directory,
            source_lang=settings["source_lang"],
            target_lang=settings["target_lang"],
            ocr_plugin_id=settings["ocr_plugin"],
            translator_id=settings["translator_plugin"],
            agent_id=settings["agent_plugin"],
            output_dir=None,
            use_agent=settings["use_agent"],
            intent="translate",
        )
        return self._start_batch_worker(parsed, parent=parent)

    def _start_batch_worker(
        self,
        parsed: ParsedMessage,
        *,
        parent: QObject | None = None,
    ) -> bool:
        if self._batch_worker is not None and self._batch_worker.isRunning():
            self.system_message.emit("이전 배치가 실행 중입니다. 완료 후 다시 시도해 주세요.")
            return False

        chat_settings = self._config.chat_settings
        chat_config = {
            "llm_provider": chat_settings.llm_provider,
            "llm_model": chat_settings.llm_model,
            "api_key": self._config.get_api_key("ANTHROPIC_API_KEY"),
        }
        worker = self._batch_worker_factory(
            parsed=parsed,
            session=self._chat_session,
            pipeline=self._pipeline,
            chat_config=chat_config,
            parent=parent,
        )
        self._batch_worker = worker
        worker.agent_message.connect(self.agent_message.emit)
        worker.agent_stream_chunk.connect(self.agent_stream_chunk.emit)
        worker.agent_stream_finished.connect(self.agent_stream_finished.emit)
        worker.job_progress.connect(lambda _name, cur, total: self.batch_progress.emit(cur, total))
        worker.batch_completed.connect(self._on_batch_completed)
        worker.finished.connect(self._on_worker_finished)
        self.batch_running_changed.emit(True)
        worker.start()
        return True

    def finish_stream_for_message(self) -> bool:
        if not self._chat_stream_active:
            return False
        self._chat_stream_active = False
        return True

    def start_stream(self) -> bool:
        if self._chat_stream_active:
            return False
        self._chat_stream_active = True
        return True

    def cancel_batch(self) -> None:
        if self._batch_worker and self._batch_worker.isRunning():
            self._batch_worker.cancel()
            self.agent_stream_finished.emit()
            self.system_message.emit("배치 취소 요청됨")

    def _on_batch_completed(self, result: object) -> None:
        if hasattr(result, "output_dir"):
            self._chat_session = self._chat_session.add_message("system", "batch_complete")
            self._chat_session.last_directory = result.output_dir
        self._batch_worker = None
        self.batch_completed.emit(result)

    def _on_worker_finished(self) -> None:
        self.batch_running_changed.emit(False)

"""배치 처리 QThread 워커 — QThread↔asyncio 브릿지."""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from src.chat.batch_processor import BatchProcessor, BatchResult
from src.chat.chat_agent import ChatAgent
from src.chat.conversation import ConversationSession, ParsedMessage
from src.utils.logger import get_logger

logger = get_logger("trans_image.gui.batch_worker")


class BatchWorker(QThread):
    """채팅 명령으로 시작된 배치 번역 작업을 비동기로 실행.

    PipelineWorker와 동일한 QThread+asyncio 패턴 사용.
    메인 스레드에서 asyncio.run() 호출 금지.
    """

    # 시그널
    job_progress = Signal(str, int, int)     # (image_name, current, total)
    job_completed = Signal(str)              # image_name
    job_failed = Signal(str, str)            # (image_name, error)
    batch_completed = Signal(object)         # BatchResult
    agent_message = Signal(str)              # 채팅 에이전트 메시지
    error_occurred = Signal(str)             # 배치 수준 에러

    def __init__(
        self,
        parsed: ParsedMessage,
        session: ConversationSession,
        pipeline: Any,
        chat_config: dict[str, Any],
        parent: Any = None,
    ) -> None:
        super().__init__(parent)
        self._parsed = parsed
        self._session = session
        self._pipeline = pipeline
        self._chat_config = chat_config
        self._cancelled = False

    def cancel(self) -> None:
        """실행 중인 배치를 취소 요청."""
        self._cancelled = True

    def run(self) -> None:
        """QThread 진입점 — 새 asyncio 루프에서 배치 실행."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_batch())
        except Exception as exc:
            logger.error("배치 워커 예외: %s", exc)
            self.error_occurred.emit(str(exc))
        finally:
            loop.close()

    async def _run_batch(self) -> None:
        agent = ChatAgent(self._chat_config)
        processor = BatchProcessor()

        # 파라미터 보완
        resolved, question = agent.resolve_params(self._parsed, self._session)
        if question:
            self.agent_message.emit(question)
            return

        # 디렉토리 스캔
        try:
            images = processor.scan_directory(resolved.directory_path)
        except FileNotFoundError as exc:
            self.agent_message.emit(f"경로를 찾을 수 없습니다: `{resolved.directory_path}`")
            return

        if not images:
            self.agent_message.emit(
                "지원하는 이미지 파일이 없습니다. (지원: png, jpg, jpeg, webp, bmp, tiff)"
            )
            return

        # 시작 메시지
        self.agent_message.emit(
            agent.format_start(len(images), resolved.directory_path, resolved.target_lang)
        )

        # 잡 생성
        jobs = processor.create_batch_jobs(images, resolved)

        # 배치 실행
        def on_progress(name: str, current: int, total: int) -> None:
            if not self._cancelled:
                self.job_progress.emit(name, current, total)
                self.agent_message.emit(agent.format_progress(name, current, total))

        result = await processor.run_batch(
            jobs,
            self._pipeline,
            on_progress=on_progress,
        )

        # 완료 요약
        self.agent_message.emit(agent.format_result(result))
        self.batch_completed.emit(result)

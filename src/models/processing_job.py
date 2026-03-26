"""이미지 처리 작업 데이터 모델."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class JobStatus(Enum):
    QUEUED = "queued"
    OCR_RUNNING = "ocr_running"
    AGENT_ANALYZING = "agent_analyzing"
    DETECTING_LANGUAGE = "detecting_language"
    GENERATING_CONTEXT = "generating_context"
    TRANSLATING = "translating"
    AGENT_VALIDATING = "agent_validating"
    INPAINTING = "inpainting"
    RENDERING = "rendering"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL_STATUSES = frozenset({
    JobStatus.COMPLETE,
    JobStatus.FAILED,
    JobStatus.CANCELLED,
})


@dataclass
class ProcessingJob:
    """단일 이미지 처리 작업.

    설정 필드는 생성자에서 한 번에 전달한다.
    처리 진행 중 변경되는 런타임 필드(status, progress 등)만 이후에 수정한다.
    """

    # ── 설정 필드 (생성 시 전달, 이후 변경 없음) ──────────────────────────
    input_path: Optional[Path] = None
    output_path: Optional[Path] = None
    target_lang: str = "ko"
    source_lang: str = "auto"
    translator_plugin_id: str = "deepl"
    ocr_plugin_id: str = "easyocr"
    agent_plugin_id: str = "openai"
    use_agent: bool = True

    # ── 식별자 ──────────────────────────────────────────────────────────────
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ── 런타임 상태 (파이프라인이 처리 중 갱신) ───────────────────────────
    status: JobStatus = field(default=JobStatus.QUEUED)
    progress: float = 0.0
    error_message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # ── 처리 결과 (파이프라인이 설정) ─────────────────────────────────────
    original_image: Any = field(default=None, repr=False)
    inpainted_image: Any = field(default=None, repr=False)
    final_image: Any = field(default=None, repr=False)
    regions: list = field(default_factory=list, repr=False)
    total_regions: int = 0
    translated_regions: int = 0
    failed_regions: int = 0

    # ── 생명주기 메서드 ───────────────────────────────────────────────────

    def start(self) -> None:
        """처리 시작 — 상태를 OCR_RUNNING 으로 전환."""
        self.status = JobStatus.OCR_RUNNING
        self.started_at = datetime.now()

    def complete(self) -> None:
        """처리 완료 — 상태를 COMPLETE 로 전환."""
        self.status = JobStatus.COMPLETE
        self.progress = 1.0
        self.completed_at = datetime.now()

    def fail(self, message: str) -> None:
        """처리 실패 — 상태를 FAILED 로 전환."""
        self.status = JobStatus.FAILED
        self.error_message = message
        self.completed_at = datetime.now()

    def cancel(self) -> None:
        """처리 취소 — 상태를 CANCELLED 로 전환."""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.now()

    @property
    def is_done(self) -> bool:
        return self.status in _TERMINAL_STATUSES

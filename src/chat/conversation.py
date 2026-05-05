"""대화 세션 데이터 모델."""
from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class ChatMessage:
    """불변 채팅 메시지."""
    role: str                # "user" | "assistant" | "system"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __post_init__(self) -> None:
        if isinstance(self.metadata, dict):
            object.__setattr__(self, "metadata", MappingProxyType(self.metadata))


@dataclass(frozen=True)
class ParsedMessage:
    """@경로 멘션 및 파라미터가 파싱된 사용자 메시지."""
    raw_text: str
    directory_path: Path | None
    source_lang: str | None
    target_lang: str | None
    ocr_plugin_id: str | None
    translator_id: str | None
    agent_id: str | None
    output_dir: Path | None
    use_agent: bool | None
    intent: str | None         # ChatAgent가 LLM으로 해석한 사용자 의도


@dataclass
class ConversationSession:
    """대화 세션 상태 관리."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[ChatMessage] = field(default_factory=list)
    last_directory: Path | None = None
    pending_jobs: list = field(default_factory=list)   # list[ProcessingJob]
    default_params: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> "ConversationSession":
        """새 메시지를 추가한 새 세션 반환 (불변 패턴)."""
        from dataclasses import replace
        new_msg = ChatMessage(role=role, content=content)
        return replace(self, messages=[*self.messages, new_msg])

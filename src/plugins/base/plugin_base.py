"""PluginBase ABC — 모든 플러그인의 공통 라이프사이클 인터페이스."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PluginBase(ABC):
    """모든 플러그인이 상속해야 하는 추상 기반 클래스."""

    # 서브클래스에서 반드시 선언
    PLUGIN_NAME: str = ""
    PLUGIN_VERSION: str = "0.1.0"
    PLUGIN_DESCRIPTION: str = ""
    PLUGIN_TYPE: str = ""  # 'ocr' | 'translator' | 'agent'

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config: dict[str, Any] = config or {}
        self._loaded: bool = False

    # --- 라이프사이클 ---

    @abstractmethod
    async def load(self) -> None:
        """플러그인 초기화 (모델 로드, API 클라이언트 생성 등)."""

    @abstractmethod
    async def unload(self) -> None:
        """플러그인 리소스 해제."""

    @abstractmethod
    def validate_config(self) -> list[str]:
        """설정 유효성 검사.
        반환값: 오류 메시지 목록. 빈 목록이면 유효.
        """

    @abstractmethod
    def get_capabilities(self) -> dict[str, Any]:
        """플러그인 기능 정보 반환.
        예: {'languages': ['en', 'ko'], 'batch_size': 50}
        """

    # --- 상태 조회 ---

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def plugin_id(self) -> str:
        return self.PLUGIN_NAME

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "unloaded"
        return f"<{self.__class__.__name__} name={self.PLUGIN_NAME!r} {status}>"

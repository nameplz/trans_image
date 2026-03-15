"""구조화 로깅 유틸리티."""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Any


_loggers: dict[str, logging.Logger] = {}


def get_logger(name: str) -> logging.Logger:
    """이름으로 로거 반환. 최초 요청 시 생성."""
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    _loggers[name] = logger
    return logger


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """앱 시작 시 한 번 호출하여 로깅 설정."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger("trans_image")
    root.setLevel(numeric_level)

    # 콘솔 핸들러
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 파일 핸들러 (옵션)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)


class LogContext:
    """with 문으로 사용하는 구조화 로그 컨텍스트."""

    def __init__(self, logger: logging.Logger, operation: str, **kwargs: Any) -> None:
        self._logger = logger
        self._operation = operation
        self._extra = kwargs

    def __enter__(self) -> "LogContext":
        self._logger.debug("시작: %s %s", self._operation, self._extra)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if exc_type is not None:
            self._logger.error("실패: %s — %s", self._operation, exc_val)
        else:
            self._logger.debug("완료: %s", self._operation)
        return False  # 예외 전파

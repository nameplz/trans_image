"""logger 유틸 테스트."""
from __future__ import annotations

import logging
from pathlib import Path

from src.utils.logger import LogContext, get_logger, setup_logging


class TestLoggerUtils:
    def test_get_logger_returns_cached_instance(self):
        logger_a = get_logger("trans_image.test.logger")
        logger_b = get_logger("trans_image.test.logger")

        assert logger_a is logger_b

    def test_setup_logging_adds_console_and_file_handlers(self, tmp_path):
        root = logging.getLogger("trans_image")
        root.handlers.clear()
        log_path = tmp_path / "logs" / "app.log"

        setup_logging(level="DEBUG", log_file=str(log_path), max_bytes=256, backup_count=1)

        assert root.level == logging.DEBUG
        assert len(root.handlers) == 2
        root.info("hello")
        for handler in root.handlers:
            handler.flush()
        assert log_path.exists()

        root.handlers.clear()

    def test_log_context_logs_start_and_finish(self, caplog):
        logger = logging.getLogger("trans_image.context")
        logger.setLevel(logging.DEBUG)

        with caplog.at_level(logging.DEBUG, logger="trans_image.context"):
            with LogContext(logger, "demo", key="value"):
                pass

        messages = [record.message for record in caplog.records]
        assert any("시작: demo" in message for message in messages)
        assert any("완료: demo" in message for message in messages)

    def test_log_context_logs_failure(self, caplog):
        logger = logging.getLogger("trans_image.context.error")
        logger.setLevel(logging.DEBUG)

        with caplog.at_level(logging.DEBUG, logger="trans_image.context.error"):
            try:
                with LogContext(logger, "explode"):
                    raise ValueError("boom")
            except ValueError:
                pass

        assert any("실패: explode" in record.message for record in caplog.records)

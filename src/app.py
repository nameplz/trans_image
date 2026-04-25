"""QApplication 래퍼 — 앱 초기화."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from src.core.config_manager import ConfigManager
from src.core.pipeline import Pipeline
from src.core.plugin_manager import PluginManager
from src.core.session import Session
from src.gui.main_window import MainWindow
from src.gui.theme import apply_theme
from src.utils.logger import get_logger, setup_logging

logger = get_logger("trans_image.app")


def create_app(argv: list[str] | None = None) -> tuple[QApplication, MainWindow]:
    """QApplication 및 MainWindow 생성."""
    app = QApplication(argv or sys.argv)
    app.setApplicationName("trans_image")
    app.setApplicationVersion("0.1.0")

    # 설정 로드
    config = ConfigManager()
    config.load()

    # QSS 스타일 적용
    apply_theme(app, config.get("app", "theme", default="dark"))

    # 로깅 설정
    setup_logging(
        level=config.get("logging", "level") or "INFO",
        log_file=config.get("logging", "file"),
    )

    plugin_manager = PluginManager(config)
    session = Session()
    pipeline = Pipeline(config, plugin_manager)

    window = MainWindow(config, plugin_manager, pipeline, session)
    return app, window


def run_gui(argv: list[str] | None = None) -> int:
    app, window = create_app(argv)
    window.show()
    return app.exec()

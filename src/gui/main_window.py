"""QMainWindow 루트 — 메인 윈도우."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QKeySequence, QAction
from PySide6.QtWidgets import (
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QWidget,
    QVBoxLayout,
)

from src.core.config_manager import ConfigManager
from src.core.pipeline import Pipeline
from src.core.plugin_manager import PluginManager
from src.core.session import Session
from src.gui.dialogs.export_dialog import ExportDialog
from src.gui.dialogs.settings_dialog import SettingsDialog
from src.chat.conversation import ConversationSession
from src.chat.message_parser import MessageParser
from src.gui.widgets.chat_panel import ChatPanel
from src.gui.widgets.comparison_view import ComparisonView
from src.gui.widgets.image_viewer import ImageViewer
from src.gui.widgets.job_queue_panel import JobQueuePanel
from src.gui.widgets.progress_panel import ProgressPanel
from src.gui.widgets.region_editor import RegionEditorPanel
from src.gui.widgets.region_overlay import RegionOverlayManager
from src.gui.workers.batch_worker import BatchWorker
from src.gui.workers.pipeline_worker import WorkerPool
from src.models.processing_job import ProcessingJob
from src.utils.logger import get_logger

logger = get_logger("trans_image.main_window")


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: ConfigManager,
        plugin_manager: PluginManager,
        pipeline: Pipeline,
        session: Session,
    ) -> None:
        super().__init__()
        self._config = config
        self._plugin_manager = plugin_manager
        self._pipeline = pipeline
        self._session = session
        self._worker_pool = WorkerPool(pipeline, max_concurrent=2)
        self._current_job: ProcessingJob | None = None
        self._batch_worker: BatchWorker | None = None
        self._chat_session = ConversationSession()
        self._msg_parser = MessageParser()

        self.setWindowTitle("trans_image — AI 이미지 텍스트 번역")
        self.setMinimumSize(1200, 700)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # 메인 스플리터: 이미지 뷰 | 오른쪽 패널
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # 왼쪽: 탭 (원본 뷰 / 비교 뷰)
        self._tabs = QTabWidget()
        self._image_viewer = ImageViewer()
        self._overlay_manager = RegionOverlayManager(self._image_viewer.scene_ref)
        self._tabs.addTab(self._image_viewer, "이미지")

        self._comparison_view = ComparisonView()
        self._tabs.addTab(self._comparison_view, "비교")

        main_splitter.addWidget(self._tabs)

        # 오른쪽 패널
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self._region_editor = RegionEditorPanel()
        self._region_editor.translation_changed.connect(self._on_translation_edited)
        right_splitter.addWidget(self._region_editor)

        self._job_queue = JobQueuePanel()
        self._job_queue.job_selected.connect(self._on_job_selected)
        right_splitter.addWidget(self._job_queue)

        self._progress_panel = ProgressPanel()
        right_splitter.addWidget(self._progress_panel)

        self._chat_panel = ChatPanel()
        self._chat_panel.message_sent.connect(self._on_chat_message)
        self._chat_panel.cancel_requested.connect(self._cancel_batch)
        right_splitter.addWidget(self._chat_panel)

        right_splitter.setSizes([300, 150, 80, 250])
        main_splitter.addWidget(right_splitter)
        main_splitter.setSizes([850, 350])
        main_layout.addWidget(main_splitter)

    def _setup_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("파일(&F)")
        open_action = QAction("열기(&O)", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        export_action = QAction("내보내기(&E)", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self._export)
        file_menu.addAction(export_action)

        file_menu.addSeparator()
        quit_action = QAction("종료(&Q)", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        settings_menu = menubar.addMenu("설정(&S)")
        settings_action = QAction("설정 열기", self)
        settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(settings_action)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("도구 모음")
        self.addToolBar(toolbar)

        self._process_action = QAction("▶ 처리 시작", self)
        self._process_action.triggered.connect(self._start_processing)
        toolbar.addAction(self._process_action)

        cancel_action = QAction("■ 취소", self)
        cancel_action.triggered.connect(self._cancel_processing)
        toolbar.addAction(cancel_action)

    def _setup_statusbar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("준비")

    # --- 드래그 앤 드롭 ---

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"):
                self._load_image(path)

    # --- 파일 로드 ---

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 열기",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All files (*)",
        )
        if path:
            self._load_image(Path(path))

    def _load_image(self, path: Path) -> None:
        try:
            import cv2
            img = cv2.imread(str(path))
            if img is None:
                raise ValueError(f"이미지 로드 실패: {path}")
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self._image_viewer.set_image(rgb)
            self._overlay_manager.clear()
            self._status_bar.showMessage(f"로드: {path.name}")
            logger.info("이미지 로드: %s", path)
        except Exception as e:
            QMessageBox.critical(self, "오류", f"이미지 로드 실패:\n{e}")

    # --- 처리 ---

    def _start_processing(self) -> None:
        settings_dlg = SettingsDialog(self._config, self._plugin_manager, self)
        if settings_dlg.exec() == SettingsDialog.DialogCode.Rejected:
            return

        settings = settings_dlg.get_settings()
        path_str = self._status_bar.currentMessage().replace("로드: ", "")
        # 현재 로드된 이미지로 작업 생성
        path = Path(path_str) if "로드:" not in path_str else None
        if not path or not path.exists():
            QMessageBox.warning(self, "경고", "먼저 이미지를 로드하세요.")
            return

        job = self._session.create_job_for_file(
            input_path=path,
            target_lang=settings["target_lang"],
            source_lang=settings["source_lang"],
            ocr_plugin_id=settings["ocr_plugin"],
            translator_plugin_id=settings["translator_plugin"],
            agent_plugin_id=settings["agent_plugin"],
            use_agent=settings["use_agent"],
        )
        self._current_job = job
        self._job_queue.add_job(job)

        worker = self._worker_pool.submit(job, parent=self)
        worker.progress_updated.connect(self._on_progress)
        worker.job_completed.connect(self._on_job_done)
        worker.job_failed.connect(self._on_job_failed)
        worker.status_changed.connect(self._on_status_changed)

    def _cancel_processing(self) -> None:
        if self._current_job:
            self._worker_pool.cancel(self._current_job.job_id)

    # --- 내보내기 ---

    def _export(self) -> None:
        if not self._current_job or self._current_job.final_image is None:
            QMessageBox.warning(self, "경고", "내보낼 번역 이미지가 없습니다.")
            return

        default = self._current_job.input_path.with_stem(
            self._current_job.input_path.stem + "_translated"
        )
        dlg = ExportDialog(default, self)
        if dlg.exec() != ExportDialog.DialogCode.Accepted:
            return

        out_path = dlg.get_output_path()
        if not out_path:
            return

        try:
            import cv2
            bgr = cv2.cvtColor(self._current_job.final_image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(str(out_path), bgr)
            self._status_bar.showMessage(f"저장 완료: {out_path}")
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 실패:\n{e}")

    # --- 설정 ---

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._config, self._plugin_manager, self)
        dlg.exec()

    # --- 슬롯 ---

    @Slot(str, float, str)
    def _on_progress(self, job_id: str, progress: float, message: str) -> None:
        self._progress_panel.update_progress(progress, message)
        self._job_queue.update_job(job_id)
        self._status_bar.showMessage(message)

    @Slot(str, str)
    def _on_status_changed(self, job_id: str, status_label: str) -> None:
        self._progress_panel.set_status(status_label)

    @Slot(str)
    def _on_job_done(self, job_id: str) -> None:
        job = self._session.get_job(job_id)
        if job and job.final_image is not None:
            self._image_viewer.set_image(job.final_image)
            self._overlay_manager.set_regions(job.regions)
            self._comparison_view.set_images(
                job.original_image,
                job.final_image,
            )
        self._job_queue.update_job(job_id)
        self._status_bar.showMessage(f"완료: {job_id[:8]}")

    @Slot(str, str)
    def _on_job_failed(self, job_id: str, error: str) -> None:
        self._job_queue.update_job(job_id)
        self._status_bar.showMessage(f"실패: {error}")
        QMessageBox.critical(self, "처리 실패", f"오류:\n{error}")

    @Slot(str)
    def _on_job_selected(self, job_id: str) -> None:
        job = self._session.get_job(job_id)
        if job:
            self._current_job = job

    @Slot(str, str)
    def _on_translation_edited(self, region_id: str, new_text: str) -> None:
        if self._current_job:
            for r in self._current_job.regions:
                if r.region_id == region_id:
                    r.translated_text = new_text
                    self._overlay_manager.update_region(r)
                    break

    # --- 채팅 패널 슬롯 ---

    @Slot(str)
    def _on_chat_message(self, text: str) -> None:
        if self._batch_worker is not None and self._batch_worker.isRunning():
            self._chat_panel.add_message("system", "이전 배치가 실행 중입니다. 완료 후 다시 시도해 주세요.")
            return

        cwd = Path.cwd()
        parsed = self._msg_parser.parse(text, cwd)
        chat_config = {
            "llm_provider": self._config.get("chat", "llm_provider", default="anthropic"),
            "llm_model": self._config.get("chat", "llm_model", default="claude-haiku-4-5-20251001"),
            "api_key": self._config.get_api_key("ANTHROPIC_API_KEY"),
        }
        self._batch_worker = BatchWorker(
            parsed=parsed,
            session=self._chat_session,
            pipeline=self._pipeline,
            chat_config=chat_config,
            parent=self,
        )
        self._batch_worker.agent_message.connect(self._on_agent_message)
        self._batch_worker.job_progress.connect(
            lambda name, cur, total: self._chat_panel.update_progress(cur, total)
        )
        self._batch_worker.batch_completed.connect(self._on_batch_completed)
        self._batch_worker.finished.connect(lambda: self._chat_panel.set_batch_running(False))
        self._chat_panel.set_batch_running(True)
        self._batch_worker.start()

    @Slot(str)
    def _on_agent_message(self, message: str) -> None:
        self._chat_panel.add_message("assistant", message)

    @Slot(object)
    def _on_batch_completed(self, result: object) -> None:
        # last_directory 업데이트
        if hasattr(result, "output_dir"):
            self._chat_session = self._chat_session.add_message("system", "batch_complete")
        self._batch_worker = None

    def _cancel_batch(self) -> None:
        if self._batch_worker and self._batch_worker.isRunning():
            self._batch_worker.cancel()
            self._chat_panel.add_message("system", "배치 취소 요청됨")

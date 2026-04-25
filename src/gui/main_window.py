"""QMainWindow 루트 — 메인 윈도우."""
from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtGui import QAction, QActionGroup, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
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
from src.gui.theme import apply_theme, normalize_theme_name
from src.gui.workers.batch_worker import BatchWorker
from src.gui.workers.pipeline_worker import (
    RegionPreviewWorker,
    RegionReprocessWorker,
    WorkerPool,
)
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
        self._reprocess_workers: dict[str, RegionReprocessWorker] = {}
        self._preview_worker: RegionPreviewWorker | None = None
        self._preview_debounce = QTimer(self)
        self._preview_debounce.setSingleShot(True)
        self._preview_debounce.setInterval(350)
        self._preview_debounce.timeout.connect(self._start_preview_worker)
        self._pending_preview_region_id: str | None = None
        self._pending_preview_text = ""
        self._preview_request_id = 0
        self._latest_preview_request_id = -1
        self._latest_preview_region_id: str | None = None
        self._latest_preview_text: str | None = None
        self._latest_preview_image: np.ndarray | None = None
        self._chat_stream_active = False
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
        self._overlay_manager.region_selected.connect(self._on_region_selected)
        self._tabs.addTab(self._image_viewer, "이미지")

        self._comparison_view = ComparisonView()
        self._tabs.addTab(self._comparison_view, "비교")

        main_splitter.addWidget(self._tabs)

        # 오른쪽 패널
        right_splitter = QSplitter(Qt.Orientation.Vertical)

        self._region_editor = RegionEditorPanel()
        self._region_editor.translation_changed.connect(self._on_translation_edited)
        self._region_editor.translation_preview_requested.connect(
            self._on_translation_preview_requested
        )
        self._region_editor.reprocess_requested.connect(self._on_reprocess_requested)
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

        view_menu = menubar.addMenu("보기(&V)")
        self._theme_action_group = QActionGroup(self)
        self._theme_action_group.setExclusive(True)
        self._dark_theme_action = QAction("다크 테마", self, checkable=True)
        self._light_theme_action = QAction("라이트 테마", self, checkable=True)
        self._theme_action_group.addAction(self._dark_theme_action)
        self._theme_action_group.addAction(self._light_theme_action)
        self._dark_theme_action.triggered.connect(lambda checked: checked and self._set_theme("dark"))
        self._light_theme_action.triggered.connect(lambda checked: checked and self._set_theme("light"))
        view_menu.addAction(self._dark_theme_action)
        view_menu.addAction(self._light_theme_action)
        self._sync_theme_actions()

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
        dlg = ExportDialog(default, self._config, self)
        if dlg.exec() != ExportDialog.DialogCode.Accepted:
            return

        out_path = dlg.get_output_path()
        if not out_path:
            return

        try:
            saved_path = self._pipeline._export_service.save_image(
                self._current_job.final_image,
                out_path,
                dlg.get_export_options(),
            )
            self._status_bar.showMessage(f"저장 완료: {saved_path}")
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
            self._tabs.setCurrentIndex(1)
        self._job_queue.update_job(job_id)
        self._status_bar.showMessage(f"완료: {job_id[:8]}")
        QTimer.singleShot(3000, self._do_reset_progress_if_idle)

    @Slot(str, str)
    def _on_job_failed(self, job_id: str, error: str) -> None:
        self._job_queue.update_job(job_id)
        self._status_bar.showMessage(f"실패: {error}")
        QMessageBox.critical(self, "처리 실패", f"오류:\n{error}")
        QTimer.singleShot(3000, self._do_reset_progress_if_idle)

    def _do_reset_progress_if_idle(self) -> None:
        """진행 중인 job이 없을 때만 ProgressPanel을 리셋한다."""
        if self._current_job is not None and self._current_job.is_running:
            return
        self._progress_panel.reset()

    def _sync_theme_actions(self) -> None:
        current_theme = normalize_theme_name(self._config.get("app", "theme", default="dark"))
        self._dark_theme_action.setChecked(current_theme == "dark")
        self._light_theme_action.setChecked(current_theme == "light")

    def _set_theme(self, theme_name: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        normalized = apply_theme(app, theme_name)
        self._config.set("app", "theme", value=normalized)
        self._config.save()
        self._sync_theme_actions()

    @Slot(str)
    def _on_job_selected(self, job_id: str) -> None:
        job = self._session.get_job(job_id)
        if job:
            self._current_job = job

    @Slot(str)
    def _on_region_selected(self, region_id: str) -> None:
        """오버레이 아이템 클릭 시 RegionEditorPanel에 영역 로드."""
        if self._current_job is None:
            return
        target = next(
            (r for r in self._current_job.regions if r.region_id == region_id),
            None,
        )
        if target is None:
            return
        self._overlay_manager.select(region_id)
        self._region_editor.load_region(target)

    @Slot(str)
    def _on_reprocess_requested(self, region_id: str) -> None:
        """단일 영역 재처리 요청 처리 — RegionReprocessWorker 시작."""
        if self._current_job is None:
            return
        target = next(
            (r for r in self._current_job.regions if r.region_id == region_id),
            None,
        )
        if target is None:
            return
        worker = RegionReprocessWorker(
            self._pipeline, self._current_job, region_id, parent=self
        )
        self._reprocess_workers[region_id] = worker
        worker.progress_updated.connect(self._on_progress)
        worker.region_done.connect(self._on_region_reprocess_done)
        worker.region_failed.connect(self._on_region_reprocess_failed)
        worker.finished.connect(lambda rid=region_id: self._reprocess_workers.pop(rid, None))
        worker.start()

    @Slot(str, str)
    def _on_region_reprocess_done(self, job_id: str, region_id: str) -> None:
        job = self._session.get_job(job_id)
        if job and job.final_image is not None:
            self._image_viewer.set_image(job.final_image)
            self._comparison_view.set_images(job.original_image, job.final_image)
        self._status_bar.showMessage(f"재처리 완료: {region_id[:8]}…")

    @Slot(str, str, str)
    def _on_region_reprocess_failed(self, job_id: str, region_id: str, error: str) -> None:
        self._status_bar.showMessage(f"재처리 실패: {error}")
        logger.error("영역 재처리 실패 [%s]: %s", region_id[:8], error)

    @Slot(str, str)
    def _on_translation_edited(self, region_id: str, new_text: str) -> None:
        if self._current_job:
            for r in self._current_job.regions:
                if r.region_id == region_id:
                    r.translated_text = new_text
                    self._overlay_manager.update_region(r)
                    self._promote_preview_or_render(region_id, new_text)
                    break

    @Slot(str, str)
    def _on_translation_preview_requested(self, region_id: str, draft_text: str) -> None:
        if self._current_job is None:
            return
        if self._current_job.is_running or self._reprocess_workers:
            return
        image_base = (
            self._current_job.inpainted_image
            if self._current_job.inpainted_image is not None
            else self._current_job.original_image
        )
        if image_base is None:
            return
        self._pending_preview_region_id = region_id
        self._pending_preview_text = draft_text
        self._preview_request_id += 1
        self._preview_debounce.start()

    def _start_preview_worker(self) -> None:
        if self._current_job is None or self._pending_preview_region_id is None:
            return
        request_id = self._preview_request_id
        worker = RegionPreviewWorker(
            self._pipeline,
            self._current_job,
            self._pending_preview_region_id,
            self._pending_preview_text,
            request_id,
            parent=self,
        )
        self._preview_worker = worker
        worker.preview_ready.connect(self._on_preview_ready)
        worker.preview_failed.connect(self._on_preview_failed)
        worker.finished.connect(self._on_preview_worker_finished)
        worker.start()

    @Slot(str, str, int, object)
    def _on_preview_ready(
        self,
        job_id: str,
        region_id: str,
        request_id: int,
        image: object,
    ) -> None:
        if self._current_job is None or self._current_job.job_id != job_id:
            return
        if request_id != self._preview_request_id:
            return
        preview_image = image if isinstance(image, np.ndarray) else None
        if preview_image is None:
            return
        self._latest_preview_request_id = request_id
        self._latest_preview_region_id = region_id
        self._latest_preview_text = self._pending_preview_text
        self._latest_preview_image = preview_image
        self._image_viewer.set_image(preview_image)
        self._comparison_view.set_translated(preview_image)

    @Slot(str, str, int, str)
    def _on_preview_failed(
        self,
        job_id: str,
        region_id: str,
        request_id: int,
        error: str,
    ) -> None:
        if request_id != self._preview_request_id:
            return
        logger.error("영역 프리뷰 실패 [%s]: %s", region_id[:8], error)

    @Slot()
    def _on_preview_worker_finished(self) -> None:
        self._preview_worker = None

    def _promote_preview_or_render(self, region_id: str, new_text: str) -> None:
        if self._current_job is None:
            return
        if (
            self._latest_preview_image is not None
            and self._latest_preview_region_id == region_id
            and self._latest_preview_text == new_text
            and self._latest_preview_request_id == self._preview_request_id
        ):
            self._current_job.final_image = self._latest_preview_image
        else:
            self._current_job.final_image = asyncio.run(
                self._pipeline.preview_region_translation(self._current_job, region_id, new_text)
            )
            self._latest_preview_image = self._current_job.final_image
            self._latest_preview_region_id = region_id
            self._latest_preview_text = new_text
            self._latest_preview_request_id = self._preview_request_id
        self._image_viewer.set_image(self._current_job.final_image)
        self._comparison_view.set_translated(self._current_job.final_image)

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
        self._batch_worker.agent_stream_chunk.connect(self._on_agent_stream_chunk)
        self._batch_worker.agent_stream_finished.connect(self._on_agent_stream_finished)
        self._batch_worker.job_progress.connect(
            lambda name, cur, total: self._chat_panel.update_progress(cur, total)
        )
        self._batch_worker.batch_completed.connect(self._on_batch_completed)
        self._batch_worker.finished.connect(lambda: self._chat_panel.set_batch_running(False))
        self._chat_panel.set_batch_running(True)
        self._batch_worker.start()

    @Slot(str)
    def _on_agent_message(self, message: str) -> None:
        if self._chat_stream_active:
            self._chat_panel.finish_stream()
            self._chat_stream_active = False
        self._chat_panel.add_message("assistant", message)

    @Slot(str)
    def _on_agent_stream_chunk(self, chunk: str) -> None:
        if not self._chat_stream_active:
            self._chat_panel.start_stream("assistant")
            self._chat_stream_active = True
        self._chat_panel.append_stream_chunk(chunk)

    @Slot()
    def _on_agent_stream_finished(self) -> None:
        if self._chat_stream_active:
            self._chat_panel.finish_stream()
            self._chat_stream_active = False

    @Slot(object)
    def _on_batch_completed(self, result: object) -> None:
        # last_directory 업데이트
        if hasattr(result, "output_dir"):
            self._chat_session = self._chat_session.add_message("system", "batch_complete")
            self._chat_session.last_directory = result.output_dir
        self._batch_worker = None

    def _cancel_batch(self) -> None:
        if self._batch_worker and self._batch_worker.isRunning():
            self._batch_worker.cancel()
            self._on_agent_stream_finished()
            self._chat_panel.add_message("system", "배치 취소 요청됨")

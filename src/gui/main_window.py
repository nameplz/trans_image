"""QMainWindow 루트 — 메인 윈도우."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

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
    QVBoxLayout,
    QWidget,
)

from src.chat.conversation import ConversationSession
from src.chat.batch_processor import BatchProcessor
from src.chat.message_parser import MessageParser
from src.core.config_manager import ConfigManager
from src.core.exceptions import ConcurrencyLimitError
from src.core.pipeline import Pipeline
from src.core.plugin_manager import PluginManager
from src.core.session import Session
from src.gui.controllers.chat_controller import ChatController
from src.gui.controllers.job_controller import JobController
from src.gui.dialogs.export_dialog import ExportDialog
from src.gui.dialogs.settings_dialog import SettingsDialog
from src.gui.theme import apply_theme, normalize_theme_name
from src.gui.widgets.chat_panel import ChatPanel
from src.gui.widgets.comparison_view import ComparisonView
from src.gui.widgets.image_viewer import ImageViewer
from src.gui.widgets.job_queue_panel import JobQueuePanel
from src.gui.widgets.progress_panel import ProgressPanel
from src.gui.widgets.region_editor import RegionEditorPanel
from src.gui.widgets.region_overlay import RegionOverlayManager
from src.gui.workers.batch_worker import BatchWorker
from src.gui.workers.pipeline_worker import RegionPreviewWorker, RegionReprocessWorker, WorkerPool
from src.models.processing_job import ProcessingJob
from src.utils.logger import get_logger

logger = get_logger("trans_image.main_window")
_SUPPORTED_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"})


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
        self._job_controller = JobController(
            pipeline,
            session,
            self._worker_pool,
            reprocess_worker_factory=RegionReprocessWorker,
            preview_worker_factory=RegionPreviewWorker,
            parent=self,
        )
        self._chat_controller = ChatController(
            config,
            pipeline,
            message_parser=MessageParser(),
            conversation_session=ConversationSession(),
            batch_worker_factory=BatchWorker,
            parent=self,
        )
        self._loaded_image_path: Path | None = None
        self._loaded_folder_path: Path | None = None
        self._loaded_folder_images: tuple[Path, ...] = ()
        self._batch_processor = BatchProcessor()

        self.setWindowTitle("trans_image — AI 이미지 텍스트 번역")
        self.setMinimumSize(1200, 700)
        self.setAcceptDrops(True)

        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_controllers()

    @property
    def _current_job(self) -> ProcessingJob | None:
        return self._job_controller.current_job

    @_current_job.setter
    def _current_job(self, value: ProcessingJob | None) -> None:
        self._job_controller.current_job = value

    @property
    def _batch_worker(self):
        return self._chat_controller.batch_worker

    @_batch_worker.setter
    def _batch_worker(self, value) -> None:
        self._chat_controller.batch_worker = value

    @property
    def _reprocess_workers(self):
        return self._job_controller.reprocess_workers

    @property
    def _preview_worker(self):
        return self._job_controller.preview_worker

    @_preview_worker.setter
    def _preview_worker(self, value) -> None:
        self._job_controller._preview_worker = value

    @property
    def _preview_request_id(self) -> int:
        return self._job_controller.preview_request_id

    @_preview_request_id.setter
    def _preview_request_id(self, value: int) -> None:
        self._job_controller.preview_request_id = value

    @property
    def _pending_preview_text(self) -> str:
        return self._job_controller.pending_preview_text

    @_pending_preview_text.setter
    def _pending_preview_text(self, value: str) -> None:
        self._job_controller.pending_preview_text = value

    @property
    def _latest_preview_request_id(self) -> int:
        return self._job_controller.latest_preview_request_id

    @_latest_preview_request_id.setter
    def _latest_preview_request_id(self, value: int) -> None:
        self._job_controller.latest_preview_request_id = value

    @property
    def _latest_preview_region_id(self) -> str | None:
        return self._job_controller.latest_preview_region_id

    @_latest_preview_region_id.setter
    def _latest_preview_region_id(self, value: str | None) -> None:
        self._job_controller.latest_preview_region_id = value

    @property
    def _latest_preview_text(self) -> str | None:
        return self._job_controller.latest_preview_text

    @_latest_preview_text.setter
    def _latest_preview_text(self, value: str | None) -> None:
        self._job_controller.latest_preview_text = value

    @property
    def _latest_preview_image(self) -> np.ndarray | None:
        return self._job_controller.latest_preview_image

    @_latest_preview_image.setter
    def _latest_preview_image(self, value: np.ndarray | None) -> None:
        self._job_controller.latest_preview_image = value

    @property
    def _chat_session(self) -> ConversationSession:
        return self._chat_controller.chat_session

    @_chat_session.setter
    def _chat_session(self, value: ConversationSession) -> None:
        self._chat_controller.chat_session = value

    @property
    def _chat_stream_active(self) -> bool:
        return self._chat_controller.chat_stream_active

    @_chat_stream_active.setter
    def _chat_stream_active(self, value: bool) -> None:
        self._chat_controller.chat_stream_active = value

    def _connect_controllers(self) -> None:
        self._job_controller.progress_updated.connect(self._on_progress)
        self._job_controller.status_changed.connect(self._on_status_changed)
        self._job_controller.job_completed.connect(self._on_job_done)
        self._job_controller.job_failed.connect(self._on_job_failed)
        self._job_controller.region_reprocess_done.connect(self._on_region_reprocess_done)
        self._job_controller.region_reprocess_failed.connect(self._on_region_reprocess_failed)
        self._job_controller.preview_display_ready.connect(self._display_preview_image)
        self._job_controller.rendered_image_ready.connect(self._display_final_image)

        self._chat_controller.system_message.connect(
            lambda message: self._chat_panel.add_message("system", message)
        )
        self._chat_controller.agent_message.connect(self._on_agent_message)
        self._chat_controller.agent_stream_chunk.connect(self._on_agent_stream_chunk)
        self._chat_controller.agent_stream_finished.connect(self._on_agent_stream_finished)
        self._chat_controller.batch_running_changed.connect(self._chat_panel.set_batch_running)
        self._chat_controller.batch_progress.connect(self._chat_panel.update_progress)

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        self._tabs = QTabWidget()
        self._image_viewer = ImageViewer()
        self._overlay_manager = RegionOverlayManager(self._image_viewer.scene_ref)
        self._overlay_manager.region_selected.connect(self._on_region_selected)
        self._tabs.addTab(self._image_viewer, "이미지")

        self._comparison_view = ComparisonView()
        self._tabs.addTab(self._comparison_view, "비교")
        main_splitter.addWidget(self._tabs)

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
        menubar.setNativeMenuBar(False)

        self._file_menu = menubar.addMenu("파일(&F)")
        self._open_action = QAction("열기(&O)", self)
        self._open_action.setShortcuts([QKeySequence("Ctrl+O"), QKeySequence("Meta+O")])
        self._open_action.triggered.connect(self._open_file)
        self._file_menu.addAction(self._open_action)

        self._open_folder_action = QAction("폴더 열기(&D)", self)
        self._open_folder_action.setShortcuts(
            [QKeySequence("Ctrl+Shift+O"), QKeySequence("Meta+Shift+O")]
        )
        self._open_folder_action.triggered.connect(lambda: self._open_folder())
        self._file_menu.addAction(self._open_folder_action)

        self._recent_files_menu = self._file_menu.addMenu("최근 파일(&R)")
        self._recent_files_menu.aboutToShow.connect(self._refresh_recent_files_menu)

        self._export_action = QAction("내보내기(&E)", self)
        self._export_action.setShortcuts([QKeySequence("Ctrl+S"), QKeySequence("Ctrl+E")])
        self._export_action.triggered.connect(self._export)
        self._file_menu.addAction(self._export_action)

        self._file_menu.addSeparator()
        self._quit_action = QAction("종료(&Q)", self)
        self._quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self._quit_action.triggered.connect(self.close)
        self._file_menu.addAction(self._quit_action)

        settings_menu = menubar.addMenu("설정(&S)")
        self._settings_action = QAction("설정 열기", self)
        self._settings_action.setShortcut(QKeySequence("Ctrl+,"))
        self._settings_action.triggered.connect(self._open_settings)
        settings_menu.addAction(self._settings_action)

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
        self._refresh_recent_files_menu()

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("도구 모음")
        self.addToolBar(toolbar)

        toolbar.addAction(self._open_action)
        toolbar.addAction(self._open_folder_action)
        toolbar.addSeparator()

        self._process_action = QAction("▶ 처리 시작", self)
        self._process_action.setShortcut(QKeySequence("F5"))
        self._process_action.triggered.connect(self._start_processing)
        toolbar.addAction(self._process_action)

        self._cancel_action = QAction("■ 취소", self)
        self._cancel_action.setShortcut(QKeySequence("Escape"))
        self._cancel_action.triggered.connect(self._cancel_active_work)
        toolbar.addAction(self._cancel_action)

    def _setup_statusbar(self) -> None:
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        self._status_bar.showMessage("준비")

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._has_supported_drop_paths(self._iter_local_paths(event.mimeData().urls())):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        dropped_paths = list(self._iter_local_paths(event.mimeData().urls()))
        directory = next((path for path in dropped_paths if path.is_dir()), None)
        if directory is not None:
            self._open_folder(directory)
            return
        for path in dropped_paths:
            if self._is_supported_image_path(path):
                self._load_image(path)

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "이미지 열기",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp);;All files (*)",
        )
        if path:
            self._load_image(Path(path))

    def _open_folder(self, folder: Path | None = None) -> None:
        if folder is None:
            selected = QFileDialog.getExistingDirectory(self, "폴더 열기", "")
            if not selected:
                return
            folder = Path(selected)

        folder = folder.expanduser().resolve(strict=False)
        if not folder.exists() or not folder.is_dir():
            QMessageBox.warning(self, "경고", f"유효한 폴더가 아닙니다:\n{folder}")
            return

        try:
            images = tuple(self._batch_processor.scan_directory(folder))
        except Exception as exc:
            QMessageBox.critical(self, "오류", f"폴더 스캔 실패:\n{exc}")
            return

        if not images:
            QMessageBox.warning(self, "경고", "지원하는 이미지 파일이 없습니다.")
            return

        self._loaded_folder_path = folder
        self._loaded_folder_images = images
        self._load_image(images[0], record_recent=False, clear_folder_context=False)
        self._config.add_recent_file(folder, save=True)
        self._refresh_recent_files_menu()
        self._status_bar.showMessage(f"폴더 로드: {folder.name} ({len(images)}개 이미지)")

    def _load_image(
        self,
        path: Path,
        *,
        record_recent: bool = True,
        clear_folder_context: bool = True,
    ) -> None:
        try:
            import cv2

            img = cv2.imread(str(path))
            if img is None:
                raise ValueError(f"이미지 로드 실패: {path}")
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            self._image_viewer.set_image(rgb)
            self._overlay_manager.clear()
            self._loaded_image_path = path
            if clear_folder_context:
                self._loaded_folder_path = None
                self._loaded_folder_images = ()
            if record_recent:
                self._config.add_recent_file(path, save=True)
                self._refresh_recent_files_menu()
            self._status_bar.showMessage(f"로드: {path.name}")
            logger.info("이미지 로드: %s", path)
        except Exception as exc:
            QMessageBox.critical(self, "오류", f"이미지 로드 실패:\n{exc}")

    def _start_processing(self) -> None:
        folder_path = self._loaded_folder_path
        image_path = self._loaded_image_path
        if folder_path is None and (not image_path or not image_path.exists()):
            QMessageBox.warning(self, "경고", "먼저 이미지 또는 폴더를 로드하세요.")
            return

        settings_dlg = SettingsDialog(self._config, self._plugin_manager, self)
        if settings_dlg.exec() == SettingsDialog.DialogCode.Rejected:
            return

        settings = settings_dlg.get_settings()
        if folder_path is not None:
            accepted = self._chat_controller.submit_directory_batch(
                folder_path,
                settings,
                parent=self,
            )
            if accepted:
                self._status_bar.showMessage(f"배치 시작: {folder_path.name}")
            return

        path = image_path
        if not path or not path.exists():
            QMessageBox.warning(self, "경고", "먼저 이미지를 로드하세요.")
            return
        try:
            job = self._job_controller.start_processing(path, settings, parent=self)
        except ConcurrencyLimitError as exc:
            QMessageBox.warning(self, "경고", str(exc))
            return
        self._job_queue.add_job(job)

    def _cancel_processing(self) -> None:
        self._job_controller.cancel_processing()

    def _cancel_active_work(self) -> None:
        self._cancel_processing()
        self._cancel_batch()

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
            saved_path = self._job_controller.export_current_image(
                out_path,
                dlg.get_export_options(),
            )
            self._status_bar.showMessage(f"저장 완료: {saved_path}")
        except Exception as exc:
            QMessageBox.critical(self, "오류", f"저장 실패:\n{exc}")

    def _open_settings(self) -> None:
        dlg = SettingsDialog(self._config, self._plugin_manager, self)
        dlg.exec()

    def _refresh_recent_files_menu(self) -> None:
        self._recent_files_menu.clear()
        recent_files = self._config.app_settings.recent_files
        if not recent_files:
            empty_action = self._recent_files_menu.addAction("최근 파일 없음")
            empty_action.setEnabled(False)
            return

        for path_str in recent_files:
            path = Path(path_str)
            action = self._recent_files_menu.addAction(path_str)
            action.triggered.connect(
                lambda checked=False, target=path: self._open_recent_path(target)
            )

        self._recent_files_menu.addSeparator()
        clear_action = self._recent_files_menu.addAction("최근 목록 지우기")
        clear_action.triggered.connect(self._clear_recent_files)

    def _open_recent_path(self, path: Path) -> None:
        if not path.exists():
            QMessageBox.warning(self, "경고", f"최근 항목을 찾을 수 없습니다:\n{path}")
            self._config.remove_recent_file(path, save=True)
            self._refresh_recent_files_menu()
            return
        if path.is_dir():
            self._open_folder(path)
            return
        self._load_image(path)

    def _clear_recent_files(self) -> None:
        self._config.clear_recent_files(save=True)
        self._refresh_recent_files_menu()

    def _iter_local_paths(self, urls) -> Iterable[Path]:
        for url in urls:
            local_file = url.toLocalFile()
            if local_file:
                yield Path(local_file)

    def _has_supported_drop_paths(self, paths: Iterable[Path]) -> bool:
        return any(path.is_dir() or self._is_supported_image_path(path) for path in paths)

    def _is_supported_image_path(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in _SUPPORTED_IMAGE_SUFFIXES

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
            self._comparison_view.set_images(job.original_image, job.final_image)
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
        self._job_controller.select_job(job_id)

    @Slot(str)
    def _on_region_selected(self, region_id: str) -> None:
        region = self._job_controller.get_region(region_id)
        if region is None:
            return
        self._overlay_manager.select(region_id)
        self._region_editor.load_region(region)

    @Slot(str)
    def _on_reprocess_requested(self, region_id: str) -> None:
        self._job_controller._reprocess_worker_factory = RegionReprocessWorker
        self._job_controller.request_reprocess(region_id, parent=self)

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
        region = self._job_controller.apply_translation_edit(region_id, new_text)
        if region is not None:
            self._overlay_manager.update_region(region)

    @Slot(str, str)
    def _on_translation_preview_requested(self, region_id: str, draft_text: str) -> None:
        self._job_controller._preview_worker_factory = RegionPreviewWorker
        self._job_controller.request_translation_preview(region_id, draft_text)

    @Slot(str, str, int, object)
    def _on_preview_ready(self, job_id: str, region_id: str, request_id: int, image: object) -> None:
        self._job_controller._on_preview_ready(job_id, region_id, request_id, image)

    def _display_preview_image(self, image: object) -> None:
        preview_image = image if isinstance(image, np.ndarray) else None
        if preview_image is None:
            return
        self._image_viewer.set_image(preview_image)
        self._comparison_view.set_translated(preview_image)

    def _display_final_image(self, image: object) -> None:
        final_image = image if isinstance(image, np.ndarray) else None
        if final_image is None:
            return
        self._image_viewer.set_image(final_image)
        self._comparison_view.set_translated(final_image)

    @Slot(str)
    def _on_chat_message(self, text: str) -> None:
        self._chat_controller._batch_worker_factory = BatchWorker
        self._chat_controller.submit_message(text, parent=self)

    @Slot(str)
    def _on_agent_message(self, message: str) -> None:
        if self._chat_controller.finish_stream_for_message():
            self._chat_panel.finish_stream()
        self._chat_panel.add_message("assistant", message)

    @Slot(str)
    def _on_agent_stream_chunk(self, chunk: str) -> None:
        if self._chat_controller.start_stream():
            self._chat_panel.start_stream("assistant")
        self._chat_panel.append_stream_chunk(chunk)

    @Slot()
    def _on_agent_stream_finished(self) -> None:
        if self._chat_controller.finish_stream_for_message():
            self._chat_panel.finish_stream()

    @Slot(object)
    def _on_batch_completed(self, result: object) -> None:
        self._chat_controller._on_batch_completed(result)

    def _cancel_batch(self) -> None:
        self._chat_controller.cancel_batch()

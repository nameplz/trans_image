"""MainWindow 단위 테스트 — H-4 이전 BatchWorker 미정리."""
from __future__ import annotations

import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt

from src.core.exceptions import ConcurrencyLimitError
from src.core.settings_models import AppSettings, ProcessingSettings
from src.gui.main_window import MainWindow


def make_main_window(qtbot):
    """테스트용 MainWindow 생성 — 모든 의존성 Mock 처리."""
    config = MagicMock()
    config.get.side_effect = lambda *keys, default=None: {
        ("chat", "llm_provider"): "anthropic",
        ("chat", "llm_model"): "claude-haiku-4-5-20251001",
        ("app", "theme"): "dark",
    }.get(keys, default)
    config.get_api_key.return_value = ""
    config.app_settings = AppSettings(recent_files=())
    config.processing_settings = ProcessingSettings(
        default_source_lang="auto",
        default_target_lang="ko",
        default_ocr_plugin="easyocr",
        default_translator_plugin="deepl",
        default_agent_plugin="claude",
        use_agent=True,
    )

    plugin_manager = MagicMock()
    pipeline = MagicMock()
    session = MagicMock()

    with patch("src.gui.main_window.WorkerPool"):
        window = MainWindow(
            config=config,
            plugin_manager=plugin_manager,
            pipeline=pipeline,
            session=session,
        )
    qtbot.addWidget(window)
    return window


class TestOnChatMessageEarlyReturn:
    def test_ignores_message_while_running(self, qtbot):
        """이전 배치가 실행 중일 때 새 메시지를 무시하고 안내 메시지를 발행해야 한다."""
        window = make_main_window(qtbot)

        # 이전 워커가 실행 중인 상태 모킹
        mock_worker = MagicMock()
        mock_worker.isRunning.return_value = True
        window._batch_worker = mock_worker

        # 채팅 패널의 add_message 추적
        window._chat_panel.add_message = MagicMock()

        with patch("src.gui.main_window.BatchWorker") as MockBatchWorker:
            window._on_chat_message("@./images 한국어로 번역해줘")

        # 새 워커가 생성되지 않아야 함
        MockBatchWorker.assert_not_called()
        # 안내 메시지가 발행되어야 함
        window._chat_panel.add_message.assert_called_once()
        args = window._chat_panel.add_message.call_args[0]
        assert args[0] == "system"
        assert "실행 중" in args[1]

    def test_accepts_message_when_not_running(self, qtbot):
        """이전 배치가 없거나 완료된 상태이면 새 워커를 정상 생성해야 한다."""
        window = make_main_window(qtbot)

        # 워커 없는 상태 (초기)
        assert window._batch_worker is None

        mock_worker = MagicMock()
        with patch("src.gui.main_window.BatchWorker", return_value=mock_worker) as MockBatchWorker:
            window._on_chat_message("@./images 한국어로 번역해줘")

        MockBatchWorker.assert_called_once()
        mock_worker.start.assert_called_once()

    def test_accepts_message_after_previous_finished(self, qtbot):
        """이전 워커가 완료(isRunning=False)된 상태이면 새 워커를 생성해야 한다."""
        window = make_main_window(qtbot)

        # 이전 워커가 완료된 상태
        mock_old_worker = MagicMock()
        mock_old_worker.isRunning.return_value = False
        window._batch_worker = mock_old_worker

        mock_new_worker = MagicMock()
        with patch("src.gui.main_window.BatchWorker", return_value=mock_new_worker) as MockBatchWorker:
            window._on_chat_message("@./images 한국어로 번역해줘")

        MockBatchWorker.assert_called_once()
        mock_new_worker.start.assert_called_once()


class TestOnBatchCompleted:
    def test_clears_batch_worker_after_completion(self, qtbot):
        """배치 완료 후 _batch_worker 필드가 None으로 초기화되어야 한다."""
        window = make_main_window(qtbot)

        mock_worker = MagicMock()
        window._batch_worker = mock_worker

        result = MagicMock()
        result.output_dir = MagicMock()

        window._on_batch_completed(result)

        assert window._batch_worker is None

    def test_updates_last_directory_after_completion(self, qtbot):
        """배치 완료 후 _chat_session.last_directory가 result.output_dir로 갱신되어야 한다."""
        from pathlib import Path
        window = make_main_window(qtbot)

        output_dir = Path("/tmp/images_translated")
        result = MagicMock()
        result.output_dir = output_dir

        window._on_batch_completed(result)

        assert window._chat_session.last_directory == output_dir

    def test_does_not_set_last_directory_without_output_dir(self, qtbot):
        """result에 output_dir이 없으면 last_directory를 갱신하지 않아야 한다."""
        window = make_main_window(qtbot)

        result = object()  # output_dir 속성 없음

        window._on_batch_completed(result)

        assert window._chat_session.last_directory is None


class TestStreamingAndTheme:
    def test_agent_stream_relays_to_chat_panel(self, qtbot):
        window = make_main_window(qtbot)
        window._chat_panel.start_stream = MagicMock()
        window._chat_panel.append_stream_chunk = MagicMock()
        window._chat_panel.finish_stream = MagicMock()

        window._on_agent_stream_chunk("abc")
        window._on_agent_stream_chunk("def")
        window._on_agent_stream_finished()

        window._chat_panel.start_stream.assert_called_once_with("assistant")
        assert window._chat_panel.append_stream_chunk.call_count == 2
        window._chat_panel.finish_stream.assert_called_once()

    def test_set_theme_persists_config(self, qtbot):
        window = make_main_window(qtbot)

        with patch("src.gui.main_window.apply_theme", return_value="light") as mock_apply:
            window._set_theme("light")

        mock_apply.assert_called_once()
        window._config.set.assert_called_once_with("app", "theme", value="light")
        window._config.save.assert_called_once()


class TestStartProcessing:
    def test_start_processing_warns_when_pool_is_full(self, qtbot):
        window = make_main_window(qtbot)
        window._loaded_image_path = Path("/tmp/input.png")

        with patch("src.gui.main_window.SettingsDialog") as MockDialog, \
             patch("src.gui.main_window.QMessageBox.warning") as mock_warning:
            dialog = MockDialog.return_value
            dialog.exec.return_value = MockDialog.DialogCode.Accepted
            dialog.get_settings.return_value = {
                "target_lang": "ko",
                "source_lang": "auto",
                "ocr_plugin": "easyocr",
                "translator_plugin": "deepl",
                "agent_plugin": "claude",
                "use_agent": True,
            }
            window._job_controller.start_processing = MagicMock(
                side_effect=ConcurrencyLimitError(
                    "현재 단일 이미지 작업이 최대 동시 실행 수에 도달했습니다."
                )
            )

            window._start_processing()

        mock_warning.assert_called_once()

    def test_start_processing_warns_when_nothing_loaded(self, qtbot):
        window = make_main_window(qtbot)

        with patch("src.gui.main_window.QMessageBox.warning") as mock_warning:
            window._start_processing()

        mock_warning.assert_called_once()

    def test_start_processing_folder_uses_batch_controller(self, qtbot):
        window = make_main_window(qtbot)
        window._loaded_folder_path = Path("/tmp/images")
        window._chat_controller.submit_directory_batch = MagicMock(return_value=True)

        with patch("src.gui.main_window.SettingsDialog") as MockDialog:
            dialog = MockDialog.return_value
            dialog.exec.return_value = MockDialog.DialogCode.Accepted
            dialog.get_settings.return_value = {
                "target_lang": "ko",
                "source_lang": "auto",
                "ocr_plugin": "easyocr",
                "translator_plugin": "deepl",
                "agent_plugin": "claude",
                "use_agent": True,
            }

            window._start_processing()

        window._chat_controller.submit_directory_batch.assert_called_once_with(
            Path("/tmp/images"),
            dialog.get_settings.return_value,
            parent=window,
        )
        assert "배치 시작" in window._status_bar.currentMessage()


class TestPreviewApply:
    def test_preview_ready_updates_view_only(self, qtbot):
        window = make_main_window(qtbot)
        job = MagicMock()
        job.job_id = "job-1"
        job.final_image = None
        window._current_job = job
        preview = np.ones((10, 10, 3), dtype=np.uint8)
        window._pending_preview_text = "draft"
        window._preview_request_id = 3
        window._image_viewer.set_image = MagicMock()
        window._comparison_view.set_translated = MagicMock()

        window._on_preview_ready("job-1", "region-1", 3, preview)

        assert job.final_image is None
        window._image_viewer.set_image.assert_called_once_with(preview)
        window._comparison_view.set_translated.assert_called_once_with(preview)

    def test_translation_apply_promotes_latest_preview(self, qtbot):
        window = make_main_window(qtbot)
        region = MagicMock()
        region.region_id = "region-1"
        region.translated_text = ""
        job = MagicMock()
        job.regions = [region]
        preview = np.ones((10, 10, 3), dtype=np.uint8)
        job.final_image = None
        window._current_job = job
        window._latest_preview_image = preview
        window._latest_preview_region_id = "region-1"
        window._latest_preview_text = "draft"
        window._latest_preview_request_id = 7
        window._preview_request_id = 7
        window._image_viewer.set_image = MagicMock()
        window._comparison_view.set_translated = MagicMock()

        window._on_translation_edited("region-1", "draft")

        assert region.translated_text == "draft"
        assert job.final_image is preview


class TestExportFlow:
    def test_export_delegates_to_job_controller(self, qtbot):
        window = make_main_window(qtbot)
        final_image = np.ones((10, 10, 3), dtype=np.uint8)
        window._current_job = MagicMock()
        window._current_job.final_image = final_image
        window._current_job.input_path = Path("/tmp/input.png")
        expected_path = Path("/tmp/out.png")

        with patch("src.gui.main_window.ExportDialog") as MockDialog:
            dialog = MockDialog.return_value
            dialog.exec.return_value = MockDialog.DialogCode.Accepted
            dialog.get_output_path.return_value = expected_path
            dialog.get_export_options.return_value = MagicMock()
            window._job_controller.export_current_image = MagicMock(return_value=expected_path)

            window._export()

        window._job_controller.export_current_image.assert_called_once_with(
            expected_path,
            dialog.get_export_options.return_value,
        )
        assert window._status_bar.currentMessage() == f"저장 완료: {expected_path}"

    def test_export_error_shows_message_box(self, qtbot):
        window = make_main_window(qtbot)
        window._current_job = MagicMock()
        window._current_job.final_image = np.ones((10, 10, 3), dtype=np.uint8)
        window._current_job.input_path = Path("/tmp/input.png")

        with patch("src.gui.main_window.ExportDialog") as MockDialog, \
             patch("src.gui.main_window.QMessageBox.critical") as mock_critical:
            dialog = MockDialog.return_value
            dialog.exec.return_value = MockDialog.DialogCode.Accepted
            dialog.get_output_path.return_value = Path("/tmp/out.png")
            dialog.get_export_options.return_value = MagicMock()
            window._job_controller.export_current_image = MagicMock(side_effect=RuntimeError("save failed"))

            window._export()

        mock_critical.assert_called_once()


class TestPhase6Actions:
    def test_actions_expose_expected_shortcuts(self, qtbot):
        window = make_main_window(qtbot)

        open_shortcuts = [shortcut.toString() for shortcut in window._open_action.shortcuts()]
        open_folder_shortcuts = [
            shortcut.toString() for shortcut in window._open_folder_action.shortcuts()
        ]
        assert "Ctrl+O" in open_shortcuts
        assert "Meta+O" in open_shortcuts
        assert "Ctrl+Shift+O" in open_folder_shortcuts
        assert "Meta+Shift+O" in open_folder_shortcuts
        assert window._process_action.shortcut().toString() == "F5"
        assert window._cancel_action.shortcut().toString() == "Esc"
        assert "Ctrl+S" in [shortcut.toString() for shortcut in window._export_action.shortcuts()]
        assert window._settings_action.shortcut().toString() == "Ctrl+,"

    def test_menu_bar_is_forced_in_window(self, qtbot):
        window = make_main_window(qtbot)
        assert window.menuBar().isNativeMenuBar() is False

    def test_cancel_active_work_calls_both_cancellations(self, qtbot):
        window = make_main_window(qtbot)
        window._cancel_processing = MagicMock()
        window._cancel_batch = MagicMock()

        window._cancel_active_work()

        window._cancel_processing.assert_called_once()
        window._cancel_batch.assert_called_once()


class TestOpenFolder:
    def test_open_folder_loads_preview_and_records_folder(self, qtbot, tmp_path):
        window = make_main_window(qtbot)
        folder = tmp_path / "images"
        folder.mkdir()
        first = folder / "a.png"
        second = folder / "b.png"
        first.touch()
        second.touch()
        window._load_image = MagicMock()

        window._open_folder(folder)

        window._load_image.assert_called_once_with(
            first,
            record_recent=False,
            clear_folder_context=False,
        )
        window._config.add_recent_file.assert_called_once_with(folder, save=True)
        assert window._loaded_folder_path == folder.resolve()
        assert window._loaded_folder_images == (first, second)

    def test_open_folder_warns_when_empty(self, qtbot, tmp_path):
        window = make_main_window(qtbot)
        folder = tmp_path / "images"
        folder.mkdir()

        with patch("src.gui.main_window.QMessageBox.warning") as mock_warning:
            window._open_folder(folder)

        mock_warning.assert_called_once()

    def test_open_folder_dialog_cancel_does_nothing(self, qtbot):
        window = make_main_window(qtbot)

        with patch("src.gui.main_window.QFileDialog.getExistingDirectory", return_value=""), \
             patch.object(window, "_load_image") as mock_load:
            window._open_folder()

        mock_load.assert_not_called()


class TestRecentFiles:
    def test_refresh_recent_files_menu_shows_empty_state(self, qtbot):
        window = make_main_window(qtbot)
        window._config.app_settings = AppSettings(recent_files=())

        window._refresh_recent_files_menu()

        actions = window._recent_files_menu.actions()
        assert len(actions) == 1
        assert actions[0].text() == "최근 파일 없음"
        assert actions[0].isEnabled() is False

    def test_refresh_recent_files_menu_shows_items_and_clear(self, qtbot):
        window = make_main_window(qtbot)
        window._config.app_settings = AppSettings(recent_files=("/tmp/a.png", "/tmp/images"))

        window._refresh_recent_files_menu()

        texts = [action.text() for action in window._recent_files_menu.actions() if action.text()]
        assert "/tmp/a.png" in texts
        assert "/tmp/images" in texts
        assert "최근 목록 지우기" in texts

    def test_open_recent_path_routes_directory_to_open_folder(self, qtbot, tmp_path):
        window = make_main_window(qtbot)
        folder = tmp_path / "images"
        folder.mkdir()
        window._open_folder = MagicMock()
        window._load_image = MagicMock()

        window._open_recent_path(folder)

        window._open_folder.assert_called_once_with(folder)
        window._load_image.assert_not_called()

    def test_open_recent_path_routes_file_to_load_image(self, qtbot, tmp_path):
        window = make_main_window(qtbot)
        image = tmp_path / "a.png"
        image.touch()
        window._open_folder = MagicMock()
        window._load_image = MagicMock()

        window._open_recent_path(image)

        window._load_image.assert_called_once_with(image)
        window._open_folder.assert_not_called()

    def test_open_recent_path_removes_missing_entry(self, qtbot):
        window = make_main_window(qtbot)
        missing = Path("/tmp/does-not-exist.png")

        with patch("src.gui.main_window.QMessageBox.warning") as mock_warning:
            window._open_recent_path(missing)

        mock_warning.assert_called_once()
        window._config.remove_recent_file.assert_called_once_with(missing, save=True)

    def test_clear_recent_files_delegates_to_config(self, qtbot):
        window = make_main_window(qtbot)

        window._clear_recent_files()

        window._config.clear_recent_files.assert_called_once_with(save=True)


class TestPhase6LoadAndDrop:
    def test_load_image_skips_recent_when_requested(self, qtbot, tmp_path):
        window = make_main_window(qtbot)
        image = tmp_path / "a.png"
        image.touch()

        with patch("cv2.imread", return_value=np.ones((5, 5, 3), dtype=np.uint8)), \
             patch("cv2.cvtColor", return_value=np.ones((5, 5, 3), dtype=np.uint8)):
            window._load_image(image, record_recent=False)

        window._config.add_recent_file.assert_not_called()

    def test_drop_event_routes_directory_to_open_folder(self, qtbot, tmp_path):
        from PySide6.QtCore import QMimeData, QUrl
        from PySide6.QtGui import QDropEvent

        window = make_main_window(qtbot)
        folder = tmp_path / "images"
        folder.mkdir()
        window._open_folder = MagicMock()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(folder))])
        event = QDropEvent(
            window.rect().center(),
            Qt.CopyAction,
            mime,
            Qt.LeftButton,
            Qt.NoModifier,
        )

        window.dropEvent(event)

        window._open_folder.assert_called_once_with(folder)

    def test_drop_event_routes_image_to_load_image(self, qtbot, tmp_path):
        from PySide6.QtCore import QMimeData, QUrl
        from PySide6.QtGui import QDropEvent

        window = make_main_window(qtbot)
        image = tmp_path / "a.png"
        image.touch()
        window._load_image = MagicMock()
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(image))])
        event = QDropEvent(
            window.rect().center(),
            Qt.CopyAction,
            mime,
            Qt.LeftButton,
            Qt.NoModifier,
        )

        window.dropEvent(event)

        window._load_image.assert_called_once_with(image)

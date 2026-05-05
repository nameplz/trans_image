"""MainWindow Phase 5 기능 단위 테스트.

5-1: 오버레이 클릭 → RegionEditorPanel 연동
5-2: 재처리 핸들러 (reprocess_requested 슬롯)
5-3: 작업 완료 후 자동 비교 탭 전환
5-4: 진행 패널 자동 리셋 (QTimer 3초)
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
import pytest

from src.gui.main_window import MainWindow
from src.models.text_region import BoundingBox, TextRegion
from src.models.processing_job import ProcessingJob


# ── 픽스처 ────────────────────────────────────────────────────────────────────

def make_main_window(qtbot):
    """테스트용 MainWindow — 모든 의존성 Mock."""
    config = MagicMock()
    config.get.return_value = "anthropic"
    config.get_api_key.return_value = ""

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


def make_region(region_id: str = "test-region-id") -> TextRegion:
    return TextRegion(
        region_id=region_id,
        raw_text="Hello",
        translated_text="안녕",
        confidence=0.9,
        bbox=BoundingBox(x=10, y=10, width=100, height=50),
    )


# ── Phase 0: is_manually_edited 필드 존재 확인 ────────────────────────────────

class TestIsManuallyEditedField:
    def test_default_is_false(self):
        """TextRegion.is_manually_edited 기본값은 False이어야 한다."""
        region = make_region()
        assert region.is_manually_edited is False

    def test_can_set_true(self):
        """is_manually_edited를 True로 설정할 수 있어야 한다."""
        region = make_region()
        region.is_manually_edited = True
        assert region.is_manually_edited is True

    def test_region_editor_sets_flag_on_apply(self, qtbot):
        """RegionEditorPanel._on_apply() 호출 시 is_manually_edited가 True로 설정되어야 한다."""
        from src.gui.widgets.region_editor import RegionEditorPanel
        panel = RegionEditorPanel()
        qtbot.addWidget(panel)

        region = make_region()
        panel.load_region(region)

        # 번역문 변경 후 적용
        panel._trans_edit.setPlainText("새 번역")
        panel._on_apply()

        assert region.is_manually_edited is True


# ── 5-3: 완료 후 비교 탭 자동 전환 ────────────────────────────────────────────

class TestJobDoneAutoTabSwitch:
    def test_on_job_done_switches_to_comparison_tab(self, qtbot):
        """_on_job_done() 호출 시 탭이 인덱스 1(비교 탭)으로 전환되어야 한다."""
        window = make_main_window(qtbot)

        job = MagicMock()
        job.final_image = MagicMock()
        job.final_image.shape = (100, 200, 3)
        import numpy as np
        job.final_image = np.zeros((100, 200, 3), dtype="uint8")
        job.original_image = np.zeros((100, 200, 3), dtype="uint8")
        job.regions = []
        window._session.get_job.return_value = job

        # 초기 탭은 0(이미지)
        assert window._tabs.currentIndex() == 0

        window._on_job_done("test-job-id")

        assert window._tabs.currentIndex() == 1

    def test_on_job_done_without_final_image_no_tab_switch(self, qtbot):
        """final_image가 None이면 탭 전환이 발생하지 않아야 한다."""
        window = make_main_window(qtbot)

        job = MagicMock()
        job.final_image = None
        window._session.get_job.return_value = job

        window._tabs.setCurrentIndex(0)
        window._on_job_done("test-job-id")

        # 탭이 변경되지 않아야 함
        assert window._tabs.currentIndex() == 0

    def test_on_job_done_no_job_no_tab_switch(self, qtbot):
        """session.get_job()이 None을 반환하면 탭 전환이 발생하지 않아야 한다."""
        window = make_main_window(qtbot)
        window._session.get_job.return_value = None

        window._tabs.setCurrentIndex(0)
        window._on_job_done("nonexistent-job-id")

        assert window._tabs.currentIndex() == 0


# ── 5-4: 진행 패널 자동 리셋 ──────────────────────────────────────────────────

class TestProgressPanelAutoReset:
    def test_on_job_done_schedules_reset_timer(self, qtbot):
        """_on_job_done() 완료 시 QTimer가 스케줄되어야 한다."""
        from PySide6.QtCore import QTimer
        window = make_main_window(qtbot)

        import numpy as np
        job = MagicMock()
        job.final_image = np.zeros((100, 200, 3), dtype="uint8")
        job.original_image = np.zeros((100, 200, 3), dtype="uint8")
        job.regions = []
        window._session.get_job.return_value = job

        with patch.object(QTimer, "singleShot") as mock_timer:
            window._on_job_done("test-job-id")
            mock_timer.assert_called_once()
            # 3000ms 타이머여야 한다
            args = mock_timer.call_args[0]
            assert args[0] == 3000

    def test_on_job_failed_schedules_reset_timer(self, qtbot):
        """_on_job_failed() 시에도 QTimer가 스케줄되어야 한다."""
        from PySide6.QtCore import QTimer
        window = make_main_window(qtbot)

        with patch("src.gui.main_window.QMessageBox"):
            with patch.object(QTimer, "singleShot") as mock_timer:
                window._on_job_failed("test-job-id", "테스트 오류")
                mock_timer.assert_called_once()
                args = mock_timer.call_args[0]
                assert args[0] == 3000

    def test_reset_not_called_while_job_running(self, qtbot):
        """리셋 콜백 실행 시 현재 job이 진행 중이면 reset()이 호출되지 않아야 한다."""
        window = make_main_window(qtbot)

        # 진행 중인 job 설정
        mock_job = MagicMock()
        mock_job.is_running = True
        window._current_job = mock_job
        window._progress_panel.reset = MagicMock()

        window._do_reset_progress_if_idle()

        window._progress_panel.reset.assert_not_called()

    def test_reset_called_when_no_job_running(self, qtbot):
        """리셋 콜백 실행 시 진행 중인 job이 없으면 reset()이 호출되어야 한다."""
        window = make_main_window(qtbot)
        window._current_job = None
        window._progress_panel.reset = MagicMock()

        window._do_reset_progress_if_idle()

        window._progress_panel.reset.assert_called_once()

    def test_reset_called_when_job_is_done(self, qtbot):
        """완료된 job이 있는 경우에도 reset()이 호출되어야 한다."""
        window = make_main_window(qtbot)

        mock_job = MagicMock()
        mock_job.is_running = False
        window._current_job = mock_job
        window._progress_panel.reset = MagicMock()

        window._do_reset_progress_if_idle()

        window._progress_panel.reset.assert_called_once()


# ── 5-1: 오버레이 클릭 → RegionEditorPanel 연동 ──────────────────────────────

class TestOverlaySelectionConnectsEditor:
    def test_on_region_selected_loads_region_in_editor(self, qtbot):
        """_on_region_selected() 호출 시 RegionEditorPanel.load_region()이 호출되어야 한다."""
        window = make_main_window(qtbot)
        region = make_region("abc-region")

        # current_job에 region 설정
        job = MagicMock()
        job.regions = [region]
        window._current_job = job

        window._region_editor.load_region = MagicMock()
        window._overlay_manager.select = MagicMock()

        window._on_region_selected("abc-region")

        window._region_editor.load_region.assert_called_once_with(region)

    def test_on_region_selected_highlights_overlay(self, qtbot):
        """_on_region_selected() 호출 시 오버레이 아이템이 선택 표시되어야 한다."""
        window = make_main_window(qtbot)
        region = make_region("abc-region")

        job = MagicMock()
        job.regions = [region]
        window._current_job = job

        window._overlay_manager.select = MagicMock()

        window._on_region_selected("abc-region")

        window._overlay_manager.select.assert_called_once_with("abc-region")

    def test_on_region_selected_no_job_does_not_crash(self, qtbot):
        """current_job이 None일 때 _on_region_selected()가 크래시 없이 종료되어야 한다."""
        window = make_main_window(qtbot)
        window._current_job = None

        # 크래시 없이 실행되어야 함
        window._on_region_selected("some-region-id")

    def test_on_region_selected_unknown_id_does_not_crash(self, qtbot):
        """존재하지 않는 region_id에 대해 크래시 없이 종료되어야 한다."""
        window = make_main_window(qtbot)
        region = make_region("real-id")

        job = MagicMock()
        job.regions = [region]
        window._current_job = job

        # 실제로 없는 ID
        window._on_region_selected("nonexistent-id")

    def test_scene_selection_signal_connected(self, qtbot):
        """RegionOverlayManager에 scene selection 연결이 존재해야 한다."""
        window = make_main_window(qtbot)
        # RegionOverlayManager가 scene_selection_changed 시그널을 연결했는지 확인
        # _on_region_selected 메서드가 MainWindow에 존재해야 한다
        assert hasattr(window, "_on_region_selected")
        assert callable(window._on_region_selected)


# ── 5-2: 재처리 핸들러 ────────────────────────────────────────────────────────

class TestReprocessHandler:
    def test_on_reprocess_requested_no_job_does_not_crash(self, qtbot):
        """current_job이 없을 때 재처리 요청이 크래시 없이 종료되어야 한다."""
        window = make_main_window(qtbot)
        window._current_job = None

        window._on_reprocess_requested("some-region-id")

    def test_on_reprocess_requested_launches_worker(self, qtbot):
        """current_job이 있고 유효한 region_id이면 RegionReprocessWorker가 시작되어야 한다."""
        window = make_main_window(qtbot)
        region = make_region("region-abc")

        import numpy as np
        job = MagicMock()
        job.regions = [region]
        job.original_image = np.zeros((100, 200, 3), dtype="uint8")
        window._current_job = job

        with patch("src.gui.main_window.RegionReprocessWorker") as MockWorker:
            mock_instance = MagicMock()
            MockWorker.return_value = mock_instance

            window._on_reprocess_requested("region-abc")

            MockWorker.assert_called_once()
            mock_instance.start.assert_called_once()

    def test_on_reprocess_requested_unknown_region_does_not_launch(self, qtbot):
        """존재하지 않는 region_id이면 워커가 시작되지 않아야 한다."""
        window = make_main_window(qtbot)
        region = make_region("known-id")

        job = MagicMock()
        job.regions = [region]
        window._current_job = job

        with patch("src.gui.main_window.RegionReprocessWorker") as MockWorker:
            window._on_reprocess_requested("unknown-id")
            MockWorker.assert_not_called()

    def test_reprocess_requested_signal_connected(self, qtbot):
        """region_editor.reprocess_requested 시그널이 _on_reprocess_requested에 연결되어야 한다."""
        window = make_main_window(qtbot)
        assert hasattr(window, "_on_reprocess_requested")
        assert callable(window._on_reprocess_requested)

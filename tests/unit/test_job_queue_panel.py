"""JobQueuePanel 단위 테스트."""
from __future__ import annotations

from src.gui.widgets.job_queue_panel import JobQueuePanel
from src.models.processing_job import JobStatus, ProcessingJob


class TestJobQueuePanel:
    def test_add_and_update_job(self, qtbot, tmp_path):
        panel = JobQueuePanel()
        qtbot.addWidget(panel)
        job = ProcessingJob(input_path=tmp_path / "img.png", target_lang="ko")

        panel.add_job(job)
        assert panel._list.count() == 1
        assert "queued" in panel._list.item(0).text()

        job.status = JobStatus.TRANSLATING
        job.progress = 0.42
        panel.update_job(job.job_id)

        assert "translating" in panel._list.item(0).text()
        assert "42%" in panel._list.item(0).text()

    def test_click_emits_selected_job_id(self, qtbot, tmp_path):
        panel = JobQueuePanel()
        qtbot.addWidget(panel)
        job = ProcessingJob(input_path=tmp_path / "img.png", target_lang="ko")
        panel.add_job(job)

        selected: list[str] = []
        panel.job_selected.connect(selected.append)

        panel._on_item_clicked(panel._list.item(0))

        assert selected == [job.job_id]

    def test_clear_done_removes_only_terminal_jobs(self, qtbot, tmp_path):
        panel = JobQueuePanel()
        qtbot.addWidget(panel)
        active = ProcessingJob(input_path=tmp_path / "active.png", target_lang="ko")
        done = ProcessingJob(input_path=tmp_path / "done.png", target_lang="ko")
        failed = ProcessingJob(input_path=tmp_path / "failed.png", target_lang="ko")
        done.complete()
        failed.fail("oops")

        panel.add_job(active)
        panel.add_job(done)
        panel.add_job(failed)

        panel._clear_done()

        assert panel._list.count() == 1
        assert "active.png" in panel._list.item(0).text()

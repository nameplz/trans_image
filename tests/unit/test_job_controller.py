from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from src.core.exceptions import ConcurrencyLimitError
from src.gui.controllers.job_controller import JobController
from src.models.export_options import ExportOptions
from src.models.processing_job import ProcessingJob
from src.models.text_region import BoundingBox, TextRegion


def make_controller(qtbot):
    pipeline = MagicMock()
    session = MagicMock()
    worker_pool = MagicMock()
    worker_pool.is_at_capacity = False
    controller = JobController(
        pipeline,
        session,
        worker_pool,
        reprocess_worker_factory=MagicMock(),
        preview_worker_factory=MagicMock(),
    )
    return controller, pipeline, session, worker_pool


def make_job() -> ProcessingJob:
    job = ProcessingJob(target_lang="ko")
    job.job_id = "job-1"
    job.original_image = np.zeros((20, 20, 3), dtype=np.uint8)
    job.inpainted_image = np.zeros((20, 20, 3), dtype=np.uint8)
    job.regions = [
        TextRegion(
            region_id="region-1",
            raw_text="Hello",
            bbox=BoundingBox(x=0, y=0, width=10, height=10),
        )
    ]
    return job


class TestJobController:
    def test_start_processing_creates_job_and_connects_worker(self, qtbot):
        controller, _pipeline, session, worker_pool = make_controller(qtbot)
        job = make_job()
        session.create_job_for_file.return_value = job
        worker = MagicMock()
        worker_pool.submit.return_value = worker

        result = controller.start_processing(
            "test.png",
            {
                "target_lang": "ko",
                "source_lang": "auto",
                "ocr_plugin": "easyocr",
                "translator_plugin": "deepl",
                "agent_plugin": "claude",
                "use_agent": True,
            },
        )

        assert result is job
        assert controller.current_job is job
        worker_pool.submit.assert_called_once()

    def test_apply_translation_edit_promotes_cached_preview(self, qtbot):
        controller, _pipeline, _session, _worker_pool = make_controller(qtbot)
        job = make_job()
        preview = np.ones((20, 20, 3), dtype=np.uint8)
        controller.current_job = job
        controller.latest_preview_image = preview
        controller.latest_preview_region_id = "region-1"
        controller.latest_preview_text = "draft"
        controller.latest_preview_request_id = 3
        controller.preview_request_id = 3

        controller.apply_translation_edit("region-1", "draft")

        assert job.regions[0].translated_text == "draft"
        assert job.final_image is preview

    def test_apply_translation_edit_falls_back_to_pipeline_preview(self, qtbot):
        controller, pipeline, _session, _worker_pool = make_controller(qtbot)
        job = make_job()
        rendered = np.ones((20, 20, 3), dtype=np.uint8)
        controller.current_job = job
        pipeline.preview_region_translation = AsyncMock(return_value=rendered)

        controller.apply_translation_edit("region-1", "updated")

        assert job.final_image is rendered

    def test_preview_ready_updates_cached_state(self, qtbot):
        controller, _pipeline, _session, _worker_pool = make_controller(qtbot)
        job = make_job()
        image = np.ones((20, 20, 3), dtype=np.uint8)
        controller.current_job = job
        controller.preview_request_id = 5
        controller.pending_preview_text = "draft"

        controller._on_preview_ready("job-1", "region-1", 5, image)

        assert controller.latest_preview_image is image
        assert controller.latest_preview_text == "draft"

    def test_request_reprocess_starts_worker_for_known_region(self, qtbot):
        controller, _pipeline, _session, _worker_pool = make_controller(qtbot)
        job = make_job()
        controller.current_job = job
        worker = MagicMock()
        controller._reprocess_worker_factory = MagicMock(return_value=worker)

        controller.request_reprocess("region-1")

        worker.start.assert_called_once()

    def test_start_processing_rejects_when_pool_is_at_capacity(self, qtbot):
        controller, _pipeline, session, worker_pool = make_controller(qtbot)
        worker_pool.is_at_capacity = True

        with pytest.raises(ConcurrencyLimitError):
            controller.start_processing(
                "test.png",
                {
                    "target_lang": "ko",
                    "source_lang": "auto",
                    "ocr_plugin": "easyocr",
                    "translator_plugin": "deepl",
                    "agent_plugin": "claude",
                    "use_agent": True,
                },
            )

        session.create_job_for_file.assert_not_called()

    def test_export_current_image_delegates_to_pipeline(self, qtbot):
        controller, pipeline, _session, _worker_pool = make_controller(qtbot)
        job = make_job()
        job.final_image = np.ones((20, 20, 3), dtype=np.uint8)
        controller.current_job = job
        output_path = Path("/tmp/out.png")
        options = ExportOptions()
        pipeline.export_image.return_value = output_path

        saved_path = controller.export_current_image(output_path, options)

        pipeline.export_image.assert_called_once_with(job.final_image, output_path, options)
        assert saved_path == output_path

    def test_export_current_image_requires_rendered_image(self, qtbot):
        controller, _pipeline, _session, _worker_pool = make_controller(qtbot)
        controller.current_job = make_job()

        with pytest.raises(ValueError, match="내보낼 번역 이미지가 없습니다"):
            controller.export_current_image(make_job().input_path, ExportOptions())

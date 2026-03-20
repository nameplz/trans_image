"""BatchProcessor 단위 테스트 — TDD RED 단계."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.chat.batch_processor import BatchProcessor, BatchResult
from src.chat.conversation import ParsedMessage
from src.models.processing_job import ProcessingJob, JobStatus


def make_parsed(
    tmp_path: Path,
    target_lang: str = "ko",
    translator_id: str | None = None,
    agent_id: str | None = None,
    output_dir: Path | None = None,
    use_agent: bool | None = None,
) -> ParsedMessage:
    return ParsedMessage(
        raw_text="test",
        directory_path=tmp_path,
        target_lang=target_lang,
        translator_id=translator_id,
        agent_id=agent_id,
        output_dir=output_dir,
        use_agent=use_agent,
        intent=None,
    )


# ─── default_output_dir ──────────────────────────────────────────────────────

class TestDefaultOutputDir:
    def test_appends_translated_suffix(self):
        processor = BatchProcessor()
        result = processor.default_output_dir(Path("/home/user/manhwa"))
        assert result == Path("/home/user/manhwa_translated")

    def test_nested_path(self):
        processor = BatchProcessor()
        result = processor.default_output_dir(Path("/a/b/c/images"))
        assert result == Path("/a/b/c/images_translated")

    def test_relative_path(self):
        processor = BatchProcessor()
        result = processor.default_output_dir(Path("./screenshots"))
        assert result == Path("screenshots_translated")


# ─── scan_directory ───────────────────────────────────────────────────────────

class TestScanDirectory:
    def test_returns_image_files(self, tmp_path):
        for name in ["a.png", "b.jpg", "c.jpeg", "d.webp"]:
            (tmp_path / name).touch()
        result = BatchProcessor().scan_directory(tmp_path)
        assert len(result) == 4

    def test_filters_non_image_files(self, tmp_path):
        (tmp_path / "image.png").touch()
        (tmp_path / "doc.pdf").touch()
        (tmp_path / "data.json").touch()
        result = BatchProcessor().scan_directory(tmp_path)
        assert len(result) == 1
        assert result[0].name == "image.png"

    def test_sorted_alphabetically(self, tmp_path):
        for name in ["c.png", "a.png", "b.png"]:
            (tmp_path / name).touch()
        names = [p.name for p in BatchProcessor().scan_directory(tmp_path)]
        assert names == sorted(names)

    def test_supports_all_extensions(self, tmp_path):
        for ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
            (tmp_path / f"img{ext}").touch()
        result = BatchProcessor().scan_directory(tmp_path)
        assert len(result) == 6

    def test_empty_directory(self, tmp_path):
        result = BatchProcessor().scan_directory(tmp_path)
        assert result == []

    def test_nonexistent_path_raises(self):
        with pytest.raises(FileNotFoundError):
            BatchProcessor().scan_directory(Path("/nonexistent/xyz"))

    def test_non_recursive_by_default(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "top.png").touch()
        (subdir / "nested.png").touch()
        result = BatchProcessor().scan_directory(tmp_path)
        assert len(result) == 1
        assert result[0].name == "top.png"

    def test_case_insensitive_extensions(self, tmp_path):
        (tmp_path / "A.PNG").touch()
        (tmp_path / "B.JPG").touch()
        result = BatchProcessor().scan_directory(tmp_path)
        assert len(result) == 2


# ─── create_batch_jobs ────────────────────────────────────────────────────────

class TestCreateBatchJobs:
    def test_job_count_matches_image_count(self, tmp_path):
        images = [tmp_path / f"img{i:03d}.png" for i in range(5)]
        for img in images:
            img.touch()
        jobs = BatchProcessor().create_batch_jobs(images, make_parsed(tmp_path))
        assert len(jobs) == 5

    def test_sets_target_lang(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path, target_lang="ja"))
        assert jobs[0].target_lang == "ja"

    def test_sets_translator_id(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs(
            [img], make_parsed(tmp_path, translator_id="gemini")
        )
        assert jobs[0].translator_plugin_id == "gemini"

    def test_sets_agent_id(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs(
            [img], make_parsed(tmp_path, agent_id="openai")
        )
        assert jobs[0].agent_plugin_id == "openai"

    def test_disables_agent(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs(
            [img], make_parsed(tmp_path, use_agent=False)
        )
        assert jobs[0].use_agent is False

    def test_default_output_path(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path))
        expected = tmp_path.parent / f"{tmp_path.name}_translated" / "img.png"
        assert jobs[0].output_path == expected

    def test_custom_output_dir(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        custom = tmp_path / "my_output"
        jobs = BatchProcessor().create_batch_jobs(
            [img], make_parsed(tmp_path, output_dir=custom)
        )
        assert jobs[0].output_path == custom / "img.png"

    def test_sets_input_path(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path))
        assert jobs[0].input_path == img

    def test_default_translator_when_none(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path))
        # translator_id=None → keeps ProcessingJob default ("deepl")
        assert jobs[0].translator_plugin_id == "deepl"

    def test_empty_image_list(self, tmp_path):
        jobs = BatchProcessor().create_batch_jobs([], make_parsed(tmp_path))
        assert jobs == []


# ─── run_batch ────────────────────────────────────────────────────────────────

class TestRunBatch:
    @pytest.mark.asyncio
    async def test_all_success(self, tmp_path):
        images = [tmp_path / f"img{i}.png" for i in range(3)]
        for img in images:
            img.touch()
        jobs = BatchProcessor().create_batch_jobs(images, make_parsed(tmp_path))

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=lambda job, **kw: job.complete())

        result = await BatchProcessor().run_batch(
            jobs, mock_pipeline, on_progress=lambda *_: None
        )
        assert result.total == 3
        assert result.completed == 3
        assert result.failed == 0
        assert isinstance(result, BatchResult)

    @pytest.mark.asyncio
    async def test_continues_on_individual_failure(self, tmp_path):
        images = [tmp_path / f"img{i}.png" for i in range(3)]
        for img in images:
            img.touch()
        jobs = BatchProcessor().create_batch_jobs(images, make_parsed(tmp_path))

        call_count = 0

        async def run_side(job, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                job.fail("Test error")
            else:
                job.complete()

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=run_side)

        result = await BatchProcessor().run_batch(
            jobs, mock_pipeline, on_progress=lambda *_: None
        )
        assert result.total == 3
        assert result.completed == 2
        assert result.failed == 1
        assert len(result.failed_files) == 1

    @pytest.mark.asyncio
    async def test_handles_pipeline_exception(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path))

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=RuntimeError("unexpected"))

        result = await BatchProcessor().run_batch(
            jobs, mock_pipeline, on_progress=lambda *_: None
        )
        assert result.failed == 1
        assert result.completed == 0

    @pytest.mark.asyncio
    async def test_progress_callback_called(self, tmp_path):
        images = [tmp_path / f"img{i}.png" for i in range(3)]
        for img in images:
            img.touch()
        jobs = BatchProcessor().create_batch_jobs(images, make_parsed(tmp_path))

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=lambda job, **kw: job.complete())

        calls: list[tuple] = []
        await BatchProcessor().run_batch(
            jobs, mock_pipeline, on_progress=lambda name, idx, total: calls.append((name, idx, total))
        )
        assert len(calls) == 3
        assert calls[0][1] == 1
        assert calls[2][1] == 3
        assert calls[0][2] == 3

    @pytest.mark.asyncio
    async def test_result_output_dir(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path))

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=lambda job, **kw: job.complete())

        result = await BatchProcessor().run_batch(
            jobs, mock_pipeline, on_progress=lambda *_: None
        )
        expected_output = tmp_path.parent / f"{tmp_path.name}_translated"
        assert result.output_dir == expected_output

    @pytest.mark.asyncio
    async def test_duration_is_positive(self, tmp_path):
        img = tmp_path / "img.png"
        img.touch()
        jobs = BatchProcessor().create_batch_jobs([img], make_parsed(tmp_path))

        mock_pipeline = AsyncMock()
        mock_pipeline.run = AsyncMock(side_effect=lambda job, **kw: job.complete())

        result = await BatchProcessor().run_batch(
            jobs, mock_pipeline, on_progress=lambda *_: None
        )
        assert result.duration_seconds >= 0.0

    @pytest.mark.asyncio
    async def test_empty_jobs(self, tmp_path):
        mock_pipeline = AsyncMock()
        result = await BatchProcessor().run_batch(
            [], mock_pipeline, on_progress=lambda *_: None
        )
        assert result.total == 0
        assert result.completed == 0
        assert result.failed == 0

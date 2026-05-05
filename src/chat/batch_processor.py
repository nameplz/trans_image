"""디렉토리 이미지 배치 처리 오케스트레이터."""
from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.chat.conversation import ParsedMessage
from src.models.processing_job import ProcessingJob, JobStatus
from src.utils.logger import get_logger

logger = get_logger("trans_image.chat.batch")

_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
)

ProgressCallback = Callable[[str, int, int], "bool | None"]  # (image_name, current, total) → False면 루프 중단


@dataclass(frozen=True)
class BatchResult:
    """배치 처리 결과 요약 (불변)."""
    total: int
    completed: int
    failed: int
    failed_files: tuple[tuple[Path, str], ...]  # (path, error_message)
    output_dir: Path
    duration_seconds: float


class BatchProcessor:
    """디렉토리 스캔 → ProcessingJob 생성 → 파이프라인 순차 실행."""

    def default_output_dir(self, input_dir: Path) -> Path:
        """입력 디렉토리 옆에 `{name}_translated` 디렉토리 경로 반환."""
        return input_dir.parent / f"{input_dir.name}_translated"

    def scan_directory(self, path: Path) -> list[Path]:
        """디렉토리에서 지원하는 이미지 파일 목록을 알파벳 순으로 반환.

        현재 디렉토리(depth=1)의 파일만 스캔합니다. 하위 폴더는 포함되지 않습니다.

        Args:
            path: 스캔할 디렉토리 경로

        Returns:
            정렬된 이미지 파일 경로 목록 (하위 폴더 미포함)

        Raises:
            FileNotFoundError: 경로가 존재하지 않을 때
        """
        if not path.exists():
            raise FileNotFoundError(f"경로를 찾을 수 없습니다: {path}")

        if not path.is_dir():
            raise NotADirectoryError(f"디렉토리가 아닙니다: {path}")

        images = [
            f for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
        ]
        return sorted(images, key=lambda p: p.name)

    def create_batch_jobs(
        self,
        image_paths: list[Path],
        parsed: ParsedMessage,
    ) -> list[ProcessingJob]:
        """이미지 목록에서 ProcessingJob 목록 생성.

        출력 경로: parsed.output_dir 또는 default_output_dir(parsed.directory_path)
        """
        if not image_paths:
            return []

        base_out = parsed.output_dir or (
            self.default_output_dir(parsed.directory_path)
            if parsed.directory_path
            else Path("output_translated")
        )

        jobs = []
        for img_path in image_paths:
            extra: dict = {}
            if parsed.source_lang is not None:
                extra["source_lang"] = parsed.source_lang
            if parsed.ocr_plugin_id is not None:
                extra["ocr_plugin_id"] = parsed.ocr_plugin_id
            if parsed.translator_id is not None:
                extra["translator_plugin_id"] = parsed.translator_id
            if parsed.agent_id is not None:
                extra["agent_plugin_id"] = parsed.agent_id
            if parsed.use_agent is not None:
                extra["use_agent"] = parsed.use_agent
            job = ProcessingJob(
                input_path=img_path,
                output_path=base_out / img_path.name,
                target_lang=parsed.target_lang or "ko",
                **extra,
            )
            jobs.append(job)
        return jobs

    async def run_batch(
        self,
        jobs: list[ProcessingJob],
        pipeline: Any,
        on_progress: ProgressCallback,
    ) -> BatchResult:
        """작업 목록을 순차 실행. 개별 실패 시 나머지 계속 진행.

        Args:
            jobs: ProcessingJob 목록
            pipeline: Pipeline 인스턴스 (pipeline.run(job) 호출)
            on_progress: 각 작업 완료/실패 후 호출 (name, current, total)

        Returns:
            BatchResult
        """
        if not jobs:
            output_dir = Path("output_translated")
            return BatchResult(
                total=0, completed=0, failed=0,
                failed_files=(), output_dir=output_dir, duration_seconds=0.0,
            )

        total = len(jobs)
        completed = 0
        failed_files: list[tuple[Path, str]] = []
        t0 = time.monotonic()

        # 출력 디렉토리는 첫 번째 잡의 output_path 부모
        output_dir = jobs[0].output_path.parent if jobs[0].output_path else Path("output_translated")

        for idx, job in enumerate(jobs, start=1):
            try:
                await pipeline.run(job)
                if job.status == JobStatus.FAILED:
                    failed_files.append((job.input_path, job.error_message))
                    logger.warning("[%d/%d] 실패: %s — %s", idx, total, job.input_path.name, job.error_message)
                else:
                    completed += 1
                    logger.info("[%d/%d] 완료: %s", idx, total, job.input_path.name)
            except Exception as exc:
                job.fail(str(exc))
                failed_files.append((job.input_path, str(exc)))
                logger.error("[%d/%d] 예외: %s — %s", idx, total, job.input_path.name, exc)

            if on_progress(job.input_path.name, idx, total) is False:
                break

        return BatchResult(
            total=total,
            completed=completed,
            failed=len(failed_files),
            failed_files=tuple(failed_files),
            output_dir=output_dir,
            duration_seconds=time.monotonic() - t0,
        )

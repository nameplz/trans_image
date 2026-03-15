"""배치 작업 목록 패널."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
)

from src.models.processing_job import ProcessingJob, JobStatus


class JobQueuePanel(QWidget):
    """처리 대기 중인 작업 목록 표시."""

    job_selected = Signal(str)   # job_id
    job_cancelled = Signal(str)  # job_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._jobs: dict[str, ProcessingJob] = {}
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addWidget(QLabel("작업 목록"))
        self._clear_btn = QPushButton("완료 항목 삭제")
        self._clear_btn.clicked.connect(self._clear_done)
        header.addWidget(self._clear_btn)
        layout.addLayout(header)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

    def add_job(self, job: ProcessingJob) -> None:
        self._jobs[job.job_id] = job
        item = QListWidgetItem(self._format_job(job))
        item.setData(Qt.ItemDataRole.UserRole, job.job_id)
        self._list.addItem(item)

    def update_job(self, job_id: str) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        for i in range(self._list.count()):
            item = self._list.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == job_id:
                item.setText(self._format_job(job))
                break

    def _format_job(self, job: ProcessingJob) -> str:
        name = job.input_path.name if job.input_path else "—"
        pct = int(job.progress * 100)
        return f"{name}  [{job.status_label}] {pct}%"

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        job_id = item.data(Qt.ItemDataRole.UserRole)
        if job_id:
            self.job_selected.emit(job_id)

    def _clear_done(self) -> None:
        done_statuses = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}
        to_remove = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            if not item:
                continue
            job_id = item.data(Qt.ItemDataRole.UserRole)
            job = self._jobs.get(job_id)
            if job and job.status in done_statuses:
                to_remove.append(i)
        for i in reversed(to_remove):
            self._list.takeItem(i)

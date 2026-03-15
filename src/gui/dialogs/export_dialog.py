"""내보내기 다이얼로그."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    def __init__(self, default_path: Path | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("내보내기")
        self.setMinimumWidth(420)
        self._setup_ui(default_path)

    def _setup_ui(self, default_path: Path | None) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 출력 경로
        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setText(str(default_path) if default_path else "")
        self._path_edit.setPlaceholderText("저장 경로 선택…")
        path_row.addWidget(self._path_edit)
        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        form.addRow("저장 경로:", path_row)

        # 포맷
        self._format_combo = QComboBox()
        self._format_combo.addItems(["PNG", "JPEG", "WebP"])
        form.addRow("파일 형식:", self._format_combo)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "저장 위치 선택",
            self._path_edit.text(),
            "Images (*.png *.jpg *.webp);;All files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def get_output_path(self) -> Path | None:
        text = self._path_edit.text().strip()
        return Path(text) if text else None

    def get_format(self) -> str:
        return self._format_combo.currentText().lower()

"""내보내기 다이얼로그."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.core.config_manager import ConfigManager
from src.models.export_options import ExportOptions, ImageFormat, ResizeMode


class ExportDialog(QDialog):
    def __init__(
        self,
        default_path: Path | None = None,
        config: ConfigManager | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("내보내기")
        self.setMinimumWidth(460)
        self._config = config
        self._setup_ui(default_path)
        self._sync_format_controls()
        self._sync_resize_controls()

    def _setup_ui(self, default_path: Path | None) -> None:
        layout = QVBoxLayout(self)
        form = QFormLayout()

        path_row = QHBoxLayout()
        self._path_edit = QLineEdit()
        self._path_edit.setText(str(default_path) if default_path else "")
        self._path_edit.setPlaceholderText("저장 경로 선택…")
        path_row.addWidget(self._path_edit)
        browse_btn = QPushButton("찾아보기")
        browse_btn.clicked.connect(self._browse)
        path_row.addWidget(browse_btn)
        form.addRow("저장 경로:", path_row)

        self._format_combo = QComboBox()
        self._format_combo.addItem("PNG", ImageFormat.PNG)
        self._format_combo.addItem("JPEG", ImageFormat.JPEG)
        self._format_combo.addItem("WebP", ImageFormat.WEBP)
        default_format = str(self._get_export_default("default_format", "png")).lower()
        if default_format == "jpg":
            default_format = "jpeg"
        try:
            format_value = ImageFormat(default_format)
        except ValueError:
            format_value = ImageFormat.PNG
        current_index = max(0, self._format_combo.findData(format_value))
        self._format_combo.setCurrentIndex(current_index)
        self._format_combo.currentIndexChanged.connect(self._sync_format_controls)
        form.addRow("파일 형식:", self._format_combo)

        self._format_stack = QStackedWidget()
        self._png_compression = QSpinBox()
        self._png_compression.setRange(0, 9)
        self._png_compression.setValue(int(self._get_export_default("png_compression", 3)))

        self._jpeg_quality = QSpinBox()
        self._jpeg_quality.setRange(1, 100)
        self._jpeg_quality.setValue(int(self._get_export_default("jpg_quality", 95)))

        self._webp_quality = QSpinBox()
        self._webp_quality.setRange(1, 100)
        self._webp_quality.setValue(int(self._get_export_default("webp_quality", 90)))

        self._format_stack.addWidget(self._build_single_spin_page("PNG 압축:", self._png_compression))
        self._format_stack.addWidget(self._build_single_spin_page("JPEG 품질:", self._jpeg_quality))
        self._format_stack.addWidget(self._build_single_spin_page("WebP 품질:", self._webp_quality))
        form.addRow("포맷 옵션:", self._format_stack)

        self._resize_mode_combo = QComboBox()
        self._resize_mode_combo.addItem("원본 유지", ResizeMode.ORIGINAL)
        self._resize_mode_combo.addItem("배율(%)", ResizeMode.SCALE_PERCENT)
        self._resize_mode_combo.addItem("긴 변(px)", ResizeMode.LONG_EDGE)
        self._resize_mode_combo.currentIndexChanged.connect(self._sync_resize_controls)
        form.addRow("리사이즈:", self._resize_mode_combo)

        self._resize_value = QSpinBox()
        self._resize_value.setRange(1, 10000)
        self._resize_value.setValue(100)
        form.addRow("리사이즈 값:", self._resize_value)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_single_spin_page(self, label_text: str, spinbox: QSpinBox) -> QWidget:
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addRow(label_text, spinbox)
        return page

    def _browse(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            "저장 위치 선택",
            self._path_edit.text(),
            "Images (*.png *.jpg *.webp);;All files (*)",
        )
        if path:
            self._path_edit.setText(path)

    def _get_export_default(self, key: str, fallback):
        if self._config is None:
            return fallback
        return self._config.get("export", key, default=fallback)

    def _sync_format_controls(self) -> None:
        image_format = self.get_format()
        index_map = {
            ImageFormat.PNG: 0,
            ImageFormat.JPEG: 1,
            ImageFormat.WEBP: 2,
        }
        self._format_stack.setCurrentIndex(index_map[image_format])

    def _sync_resize_controls(self) -> None:
        resize_mode = self.get_resize_mode()
        enabled = resize_mode != ResizeMode.ORIGINAL
        self._resize_value.setEnabled(enabled)
        if resize_mode == ResizeMode.SCALE_PERCENT:
            self._resize_value.setSuffix("%")
            self._resize_value.setRange(1, 1000)
            if self._resize_value.value() > 1000:
                self._resize_value.setValue(100)
        elif resize_mode == ResizeMode.LONG_EDGE:
            self._resize_value.setSuffix(" px")
            self._resize_value.setRange(1, 10000)
        else:
            self._resize_value.setSuffix("")

    def get_output_path(self) -> Path | None:
        text = self._path_edit.text().strip()
        return Path(text) if text else None

    def get_format(self) -> ImageFormat:
        return self._format_combo.currentData(Qt.ItemDataRole.UserRole)

    def get_resize_mode(self) -> ResizeMode:
        return self._resize_mode_combo.currentData(Qt.ItemDataRole.UserRole)

    def get_export_options(self) -> ExportOptions:
        resize_mode = self.get_resize_mode()
        resize_value = self._resize_value.value() if resize_mode != ResizeMode.ORIGINAL else 100
        return ExportOptions(
            format=self.get_format(),
            jpeg_quality=self._jpeg_quality.value(),
            webp_quality=self._webp_quality.value(),
            png_compression=self._png_compression.value(),
            resize_mode=resize_mode,
            resize_value=resize_value,
        )

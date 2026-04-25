"""영역별 텍스트/번역 편집 패널."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QFrame,
    QHBoxLayout,
)

from src.models.text_region import TextRegion


class RegionEditorPanel(QWidget):
    """선택된 TextRegion의 원문/번역문 편집 UI."""

    text_changed = Signal(str, str)        # region_id, new_raw_text
    translation_changed = Signal(str, str) # region_id, new_translated_text
    translation_preview_requested = Signal(str, str)  # region_id, draft_text
    reprocess_requested = Signal(str)      # region_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._current_region: TextRegion | None = None
        self._loading_region = False
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # 헤더
        self._header = QLabel("영역을 선택하세요")
        self._header.setObjectName("regionEditorHeader")
        layout.addWidget(self._header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # 원문
        layout.addWidget(QLabel("원문 (OCR):"))
        self._raw_edit = QPlainTextEdit()
        self._raw_edit.setMaximumHeight(80)
        self._raw_edit.setPlaceholderText("OCR 인식 텍스트")
        layout.addWidget(self._raw_edit)

        # 번역문
        layout.addWidget(QLabel("번역문:"))
        self._trans_edit = QPlainTextEdit()
        self._trans_edit.setMaximumHeight(80)
        self._trans_edit.setPlaceholderText("번역 텍스트")
        self._trans_edit.textChanged.connect(self._on_translation_text_edited)
        layout.addWidget(self._trans_edit)

        # 신뢰도 표시
        self._conf_label = QLabel("신뢰도: —")
        self._conf_label.setProperty("mutedText", True)
        layout.addWidget(self._conf_label)

        # 버튼
        btn_row = QHBoxLayout()
        self._apply_btn = QPushButton("적용")
        self._apply_btn.clicked.connect(self._on_apply)
        self._reprocess_btn = QPushButton("재처리")
        self._reprocess_btn.clicked.connect(self._on_reprocess)
        btn_row.addWidget(self._apply_btn)
        btn_row.addWidget(self._reprocess_btn)
        layout.addLayout(btn_row)

        layout.addStretch()
        self._set_enabled(False)

    def load_region(self, region: TextRegion) -> None:
        self._current_region = region
        self._loading_region = True
        self._header.setText(f"영역 ID: {region.region_id[:8]}…")
        self._raw_edit.setPlainText(region.raw_text)
        self._trans_edit.setPlainText(region.translated_text)
        conf_pct = int(region.confidence * 100)
        self._conf_label.setText(f"신뢰도: {conf_pct}%")
        self._set_enabled(True)
        self._loading_region = False

    def clear(self) -> None:
        self._current_region = None
        self._loading_region = True
        self._header.setText("영역을 선택하세요")
        self._raw_edit.clear()
        self._trans_edit.clear()
        self._conf_label.setText("신뢰도: —")
        self._set_enabled(False)
        self._loading_region = False

    def _set_enabled(self, enabled: bool) -> None:
        self._raw_edit.setEnabled(enabled)
        self._trans_edit.setEnabled(enabled)
        self._apply_btn.setEnabled(enabled)
        self._reprocess_btn.setEnabled(enabled)

    def _on_apply(self) -> None:
        if not self._current_region:
            return
        rid = self._current_region.region_id
        new_raw = self._raw_edit.toPlainText()
        new_trans = self._trans_edit.toPlainText()
        if new_raw != self._current_region.raw_text:
            self._current_region.raw_text = new_raw
            self._current_region.is_manually_edited = True
            self.text_changed.emit(rid, new_raw)
        if new_trans != self._current_region.translated_text:
            self._current_region.translated_text = new_trans
            self._current_region.is_manually_edited = True
            self.translation_changed.emit(rid, new_trans)

    def _on_reprocess(self) -> None:
        if self._current_region:
            self.reprocess_requested.emit(self._current_region.region_id)

    def _on_translation_text_edited(self) -> None:
        if self._loading_region or self._current_region is None:
            return
        self.translation_preview_requested.emit(
            self._current_region.region_id,
            self._trans_edit.toPlainText(),
        )

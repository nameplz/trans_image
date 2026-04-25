"""RegionEditorPanel 단위 테스트 — 필드 반영, 컨트롤 활성화, 시그널 emit."""
from __future__ import annotations

import pytest
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

from src.gui.widgets.region_editor import RegionEditorPanel
from src.models.text_region import BoundingBox, TextRegion


# ---------------------------------------------------------------------------
# 로컬 fixture (conftest.py의 sample_text_region 과 동일하지만 명시적으로 선언)
# ---------------------------------------------------------------------------

@pytest.fixture
def region() -> TextRegion:
    """기본 TextRegion 샘플 — raw_text / translated_text 둘 다 채워진 상태."""
    return TextRegion(
        raw_text="Hello",
        translated_text="안녕",
        confidence=0.9,
        bbox=BoundingBox(x=10, y=10, width=100, height=50),
    )


@pytest.fixture
def panel(qtbot) -> RegionEditorPanel:
    """테스트용 RegionEditorPanel 인스턴스."""
    w = RegionEditorPanel()
    qtbot.addWidget(w)
    return w


# ---------------------------------------------------------------------------
# TestRegionEditorPanel
# ---------------------------------------------------------------------------

class TestRegionEditorPanel:

    # ------------------------------------------------------------------
    # 1. load_region → 텍스트 필드 반영
    # ------------------------------------------------------------------

    def test_load_region_populates_fields(self, panel, region):
        """load_region 호출 후 raw_text / translated_text 가 편집창에 반영된다."""
        panel.load_region(region)

        assert panel._raw_edit.toPlainText() == region.raw_text
        assert panel._trans_edit.toPlainText() == region.translated_text

    def test_load_region_sets_confidence_label(self, panel, region):
        """load_region 호출 후 신뢰도 레이블이 올바른 퍼센트를 표시한다."""
        panel.load_region(region)

        assert "90%" in panel._conf_label.text()

    # ------------------------------------------------------------------
    # 2. load_region → 편집 컨트롤 활성화
    # ------------------------------------------------------------------

    def test_load_region_enables_controls(self, panel, region):
        """load_region 호출 후 편집창 및 버튼이 모두 활성화된다."""
        # 초기 상태: 비활성화
        assert not panel._raw_edit.isEnabled()
        assert not panel._trans_edit.isEnabled()
        assert not panel._apply_btn.isEnabled()
        assert not panel._reprocess_btn.isEnabled()

        panel.load_region(region)

        assert panel._raw_edit.isEnabled()
        assert panel._trans_edit.isEnabled()
        assert panel._apply_btn.isEnabled()
        assert panel._reprocess_btn.isEnabled()

    # ------------------------------------------------------------------
    # 3. apply 버튼 클릭 → text_changed 시그널 emit
    # ------------------------------------------------------------------

    def test_apply_emits_text_changed_signal(self, panel, region):
        """원문을 수정하고 적용 버튼 클릭 시 text_changed 시그널이 emit된다."""
        panel.load_region(region)

        emitted: list[tuple[str, str]] = []
        panel.text_changed.connect(lambda rid, text: emitted.append((rid, text)))

        panel._raw_edit.setPlainText("Modified")
        QTest.mouseClick(panel._apply_btn, Qt.LeftButton)

        assert len(emitted) == 1
        assert emitted[0][0] == region.region_id
        assert emitted[0][1] == "Modified"

    def test_apply_no_signal_when_text_unchanged(self, panel, region):
        """텍스트 변경 없이 적용 버튼을 클릭해도 시그널이 emit되지 않는다."""
        panel.load_region(region)

        emitted: list[tuple] = []
        panel.text_changed.connect(lambda rid, text: emitted.append((rid, text)))
        panel.translation_changed.connect(lambda rid, text: emitted.append((rid, text)))

        QTest.mouseClick(panel._apply_btn, Qt.LeftButton)

        assert emitted == []

    # ------------------------------------------------------------------
    # 4. clear → 초기 상태 복원
    # ------------------------------------------------------------------

    def test_clear_resets_fields(self, panel, region):
        """clear() 호출 후 편집창이 비워지고 신뢰도 레이블이 초기값으로 돌아온다."""
        panel.load_region(region)
        panel.clear()

        assert panel._raw_edit.toPlainText() == ""
        assert panel._trans_edit.toPlainText() == ""
        assert panel._conf_label.text() == "신뢰도: —"

    def test_clear_disables_controls(self, panel, region):
        """clear() 호출 후 편집창 및 버튼이 비활성화된다."""
        panel.load_region(region)
        panel.clear()

        assert not panel._raw_edit.isEnabled()
        assert not panel._trans_edit.isEnabled()
        assert not panel._apply_btn.isEnabled()
        assert not panel._reprocess_btn.isEnabled()

    def test_clear_resets_current_region(self, panel, region):
        """clear() 후 내부 _current_region 이 None 으로 초기화된다."""
        panel.load_region(region)
        panel.clear()

        assert panel._current_region is None

    # ------------------------------------------------------------------
    # 5. translation_changed 시그널
    # ------------------------------------------------------------------

    def test_translation_changed_signal(self, panel, region):
        """번역문 수정 후 적용 버튼 클릭 시 translation_changed 시그널이 emit된다."""
        panel.load_region(region)

        emitted: list[tuple[str, str]] = []
        panel.translation_changed.connect(lambda rid, text: emitted.append((rid, text)))

        panel._trans_edit.setPlainText("수정된 번역")
        QTest.mouseClick(panel._apply_btn, Qt.LeftButton)

        assert len(emitted) == 1
        assert emitted[0][0] == region.region_id
        assert emitted[0][1] == "수정된 번역"

    def test_translation_preview_requested_on_typing(self, panel, region):
        """번역 입력 중 textChanged가 preview 시그널을 emit한다."""
        panel.load_region(region)

        emitted: list[tuple[str, str]] = []
        panel.translation_preview_requested.connect(
            lambda rid, text: emitted.append((rid, text))
        )

        panel._trans_edit.setPlainText("실시간 프리뷰")

        assert emitted[-1] == (region.region_id, "실시간 프리뷰")

    # ------------------------------------------------------------------
    # 6. reprocess 버튼 → reprocess_requested 시그널
    # ------------------------------------------------------------------

    def test_reprocess_button_emits_signal(self, panel, region):
        """재처리 버튼 클릭 시 reprocess_requested 시그널이 region_id 와 함께 emit된다."""
        panel.load_region(region)

        emitted: list[str] = []
        panel.reprocess_requested.connect(emitted.append)

        QTest.mouseClick(panel._reprocess_btn, Qt.LeftButton)

        assert emitted == [region.region_id]

    def test_reprocess_button_no_signal_without_region(self, panel):
        """region 없이 재처리 버튼을 클릭해도 시그널이 emit되지 않는다 (방어 동작)."""
        # clear 상태 — _reprocess_btn 은 disabled 이므로 QTest.mouseClick 으로는 실제 클릭이 발생하지 않음.
        # _on_reprocess 를 직접 호출해 방어 로직 확인
        emitted: list[str] = []
        panel.reprocess_requested.connect(emitted.append)

        panel._on_reprocess()  # _current_region is None

        assert emitted == []

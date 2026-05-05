"""ExportDialog 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock

from src.gui.dialogs.export_dialog import ExportDialog
from src.models.export_options import ImageFormat, ResizeMode


def make_config():
    config = MagicMock()
    config.get.side_effect = lambda *keys, default=None: {
        ("export", "default_format"): "png",
        ("export", "jpg_quality"): 95,
        ("export", "webp_quality"): 90,
        ("export", "png_compression"): 3,
    }.get(keys, default)
    return config


class TestExportDialog:
    def test_format_controls_switch_by_selected_format(self, qtbot):
        dialog = ExportDialog(config=make_config())
        qtbot.addWidget(dialog)

        dialog._format_combo.setCurrentIndex(1)
        assert dialog.get_format() == ImageFormat.JPEG
        assert dialog._format_stack.currentIndex() == 1

        dialog._format_combo.setCurrentIndex(2)
        assert dialog.get_format() == ImageFormat.WEBP
        assert dialog._format_stack.currentIndex() == 2

    def test_resize_mode_toggles_value_widget(self, qtbot):
        dialog = ExportDialog(config=make_config())
        qtbot.addWidget(dialog)

        dialog._resize_mode_combo.setCurrentIndex(0)
        assert not dialog._resize_value.isEnabled()

        dialog._resize_mode_combo.setCurrentIndex(1)
        assert dialog.get_resize_mode() == ResizeMode.SCALE_PERCENT
        assert dialog._resize_value.isEnabled()

    def test_get_export_options_reads_current_values(self, qtbot):
        dialog = ExportDialog(config=make_config())
        qtbot.addWidget(dialog)

        dialog._format_combo.setCurrentIndex(2)
        dialog._webp_quality.setValue(77)
        dialog._resize_mode_combo.setCurrentIndex(2)
        dialog._resize_value.setValue(1440)

        options = dialog.get_export_options()

        assert options.format == ImageFormat.WEBP
        assert options.webp_quality == 77
        assert options.resize_mode == ResizeMode.LONG_EDGE
        assert options.resize_value == 1440

"""공유 테스트 픽스처 — 전체 테스트 스위트용."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.core.config_manager import ConfigManager
from src.models.processing_job import ProcessingJob
from src.models.text_region import BoundingBox, TextRegion, TextStyle


@pytest.fixture
def mock_config():
    """ConfigManager mock — get() 호출에 기본값 반환."""
    config = MagicMock(spec=ConfigManager)

    def _get(*args, default=None):
        # 2개 positional args: (section, key)
        if len(args) == 2:
            section, key = args
            defaults = {
                ("rendering", "min_font_size"): 8,
                ("rendering", "max_font_size"): 72,
                ("rendering", "auto_font_size"): True,
                ("rendering", "line_spacing"): 1.2,
                ("rendering", "font_fallback"): "NotoSansCJK",
                ("inpainting", "method"): "opencv_ns",
                ("inpainting", "mask_dilation"): 5,
                ("processing", "agent_analyze"): True,
                ("processing", "agent_validate"): True,
            }
            return defaults.get((section, key), default)
        return default

    config.get.side_effect = _get
    config.get_api_key.return_value = ""
    config.get_plugin_config.return_value = None
    config.get_plugin_configs.return_value = []
    return config


@pytest.fixture
def sample_image():
    """100x200 검은색 RGB 이미지."""
    return np.zeros((100, 200, 3), dtype=np.uint8)


@pytest.fixture
def sample_text_region():
    """기본 TextRegion 샘플."""
    return TextRegion(
        raw_text="Hello",
        translated_text="안녕",
        confidence=0.9,
        bbox=BoundingBox(x=10, y=10, width=100, height=50),
    )


@pytest.fixture
def sample_regions():
    """TextRegion 3개 목록."""
    return [
        TextRegion(
            raw_text=f"Text {i}",
            translated_text=f"텍스트 {i}",
            confidence=0.9,
            bbox=BoundingBox(x=10 * i, y=10 * i, width=80, height=30),
        )
        for i in range(1, 4)
    ]


@pytest.fixture
def sample_job(tmp_path):
    """기본 ProcessingJob 샘플 (실제 파일 경로 포함)."""
    img_path = tmp_path / "test.png"
    img_path.write_bytes(b"")
    return ProcessingJob(input_path=img_path, target_lang="ko")

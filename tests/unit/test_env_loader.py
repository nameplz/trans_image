"""Project `.env` loader unit tests."""
from __future__ import annotations

import logging
import os
from unittest.mock import patch

from src.utils.env_loader import load_project_env


def test_load_project_env_skips_missing_dotenv(tmp_path) -> None:
    with patch("src.utils.env_loader._get_project_root", return_value=tmp_path):
        load_project_env()


def test_load_project_env_does_not_override_existing_environment(tmp_path) -> None:
    (tmp_path / ".env").write_text("DEEPL_API_KEY=from-dotenv\n", encoding="utf-8")

    with patch("src.utils.env_loader._get_project_root", return_value=tmp_path):
        with patch.dict(os.environ, {"DEEPL_API_KEY": "from-env"}, clear=True):
            load_project_env()
            assert os.environ["DEEPL_API_KEY"] == "from-env"


def test_load_project_env_populates_missing_environment_value(tmp_path) -> None:
    (tmp_path / ".env").write_text("DEEPL_API_KEY=from-dotenv\n", encoding="utf-8")

    with patch("src.utils.env_loader._get_project_root", return_value=tmp_path):
        with patch.dict(os.environ, {}, clear=True):
            load_project_env()
            assert os.environ["DEEPL_API_KEY"] == "from-dotenv"


def test_load_project_env_logs_warning_on_loader_failure(tmp_path, caplog) -> None:
    (tmp_path / ".env").write_text("DEEPL_API_KEY=from-dotenv\n", encoding="utf-8")

    with patch("src.utils.env_loader._get_project_root", return_value=tmp_path):
        with patch("src.utils.env_loader.load_dotenv", side_effect=RuntimeError("boom")):
            with caplog.at_level(logging.WARNING, logger="trans_image.env"):
                load_project_env()

    assert any("프로젝트 .env 로드 실패" in record.message for record in caplog.records)

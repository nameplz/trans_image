"""Public GUI/CLI entrypoint contract tests."""
from __future__ import annotations

import argparse
import importlib
import sys
import tomllib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.app import create_app, main as gui_main, run_gui
from src.models.processing_job import ProcessingJob


class TestCreateApp:
    def test_create_app_wires_dependencies(self):
        fake_app = MagicMock()
        fake_window = MagicMock()
        fake_config = MagicMock()
        fake_config.get.side_effect = lambda *keys, default=None: {
            ("app", "theme"): "light",
            ("logging", "level"): "DEBUG",
            ("logging", "file"): "logs/app.log",
        }.get(keys, default)

        with patch("src.app.QApplication", return_value=fake_app), \
             patch("src.app.ConfigManager", return_value=fake_config), \
             patch("src.app.apply_theme") as mock_apply_theme, \
             patch("src.app.setup_logging") as mock_setup_logging, \
             patch("src.app.PluginManager") as MockPluginManager, \
             patch("src.app.Session") as MockSession, \
             patch("src.app.Pipeline") as MockPipeline, \
             patch("src.app.MainWindow", return_value=fake_window):
            app, window = create_app(["prog"])

        assert app is fake_app
        assert window is fake_window
        fake_config.load.assert_called_once()
        mock_apply_theme.assert_called_once_with(fake_app, "light")
        mock_setup_logging.assert_called_once_with(level="DEBUG", log_file="logs/app.log")
        MockPluginManager.assert_called_once_with(fake_config)
        MockSession.assert_called_once()
        MockPipeline.assert_called_once()
        fake_app.setApplicationName.assert_called_once_with("trans_image")

    def test_run_gui_shows_window_and_returns_exec_code(self):
        app = MagicMock()
        app.exec.return_value = 123
        window = MagicMock()

        with patch("src.app.create_app", return_value=(app, window)):
            result = run_gui(["prog"])

        window.show.assert_called_once()
        assert result == 123

    def test_gui_main_delegates_to_run_gui(self):
        with patch("src.app.run_gui", return_value=7) as mock_run_gui:
            result = gui_main(["trans-image"])

        mock_run_gui.assert_called_once_with(["trans-image"])
        assert result == 7


class TestRootGuiLauncher:
    def test_root_main_delegates_to_src_app_main(self):
        module = importlib.import_module("main")

        with patch("src.app.main", return_value=11) as mock_gui_main:
            result = module.main()

        mock_gui_main.assert_called_once_with(sys.argv)
        assert result == 11


class TestPackagingContract:
    def test_console_script_targets_gui_entrypoint(self):
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        config = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))

        assert config["project"]["scripts"]["trans-image"] == "src.app:main"


class TestCliEntrypoint:
    def test_parse_args_uses_defaults(self):
        from src.__main__ import parse_args

        with patch("sys.argv", ["trans_image", "-i", "input.png"]):
            args = parse_args()

        assert args.input == "input.png"
        assert args.target_lang == "ko"
        assert args.source_lang == "auto"
        assert args.translator == "deepl"
        assert args.no_agent is False

    def test_cli_main_parses_args_and_returns_async_result(self):
        from src.__main__ import main

        args = argparse.Namespace(input="input.png")

        with patch("src.__main__.parse_args", return_value=args), \
             patch("src.__main__.asyncio.run", return_value=5) as mock_asyncio_run, \
             patch("src.__main__.run_cli", new_callable=MagicMock) as mock_run_cli:
            result = main()

        mock_asyncio_run.assert_called_once_with(mock_run_cli.return_value)
        assert result == 5

    @pytest.mark.asyncio
    async def test_run_cli_returns_error_for_missing_input(self, tmp_path):
        from src.__main__ import run_cli

        args = argparse.Namespace(
            input=str(tmp_path / "missing.png"),
            output=None,
            target_lang="ko",
            source_lang="auto",
            translator="deepl",
            agent="openai",
            ocr="easyocr",
            no_agent=False,
            verbose=False,
        )

        with patch("src.utils.logger.setup_logging"), \
             patch("src.core.config_manager.ConfigManager") as MockConfig, \
             patch("src.core.plugin_manager.PluginManager"), \
             patch("src.core.session.Session"), \
             patch("src.core.pipeline.Pipeline"):
            result = await run_cli(args)

        MockConfig.return_value.load.assert_called_once()
        assert result == 1

    @pytest.mark.asyncio
    async def test_run_cli_runs_pipeline_and_returns_zero(self, tmp_path):
        from src.__main__ import run_cli

        input_path = tmp_path / "input.png"
        input_path.write_bytes(b"")
        fake_session = MagicMock()
        fake_job = ProcessingJob(input_path=input_path, target_lang="ko")
        fake_session.create_job_for_file.return_value = fake_job
        fake_pipeline = MagicMock()
        fake_pipeline.run = AsyncMock()

        args = argparse.Namespace(
            input=str(input_path),
            output=None,
            target_lang="ko",
            source_lang="auto",
            translator="deepl",
            agent="openai",
            ocr="easyocr",
            no_agent=True,
            verbose=True,
        )

        with patch("src.utils.logger.setup_logging") as mock_setup_logging, \
             patch("src.core.config_manager.ConfigManager") as MockConfig, \
             patch("src.core.plugin_manager.PluginManager"), \
             patch("src.core.session.Session", return_value=fake_session), \
             patch("src.core.pipeline.Pipeline", return_value=fake_pipeline):
            result = await run_cli(args)

        mock_setup_logging.assert_called_once_with("DEBUG")
        MockConfig.return_value.load.assert_called_once()
        fake_session.create_job_for_file.assert_called_once()
        fake_pipeline.run.assert_awaited_once()
        assert result == 0

    @pytest.mark.asyncio
    async def test_run_cli_returns_error_on_pipeline_exception(self, tmp_path):
        from src.__main__ import run_cli

        input_path = tmp_path / "input.png"
        input_path.write_bytes(b"")
        fake_session = MagicMock()
        fake_session.create_job_for_file.return_value = ProcessingJob(
            input_path=input_path,
            target_lang="ko",
        )
        fake_pipeline = MagicMock()
        fake_pipeline.run = AsyncMock(side_effect=RuntimeError("failed"))

        args = argparse.Namespace(
            input=str(input_path),
            output=str(tmp_path / "out.png"),
            target_lang="ko",
            source_lang="auto",
            translator="deepl",
            agent="openai",
            ocr="easyocr",
            no_agent=False,
            verbose=False,
        )

        with patch("src.utils.logger.setup_logging"), \
             patch("src.core.config_manager.ConfigManager"), \
             patch("src.core.plugin_manager.PluginManager"), \
             patch("src.core.session.Session", return_value=fake_session), \
             patch("src.core.pipeline.Pipeline", return_value=fake_pipeline):
            result = await run_cli(args)

        assert result == 1

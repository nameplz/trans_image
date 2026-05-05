from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.chat.conversation import ConversationSession
from src.core.config_manager import ConfigManager
from src.core.settings_models import ChatSettings
from src.gui.controllers.chat_controller import ChatController


def make_controller(qtbot):
    config = MagicMock(spec=ConfigManager)
    config.chat_settings = ChatSettings(
        llm_provider="anthropic",
        llm_model="claude-haiku-4-5-20251001",
    )
    config.get_api_key.return_value = ""
    pipeline = MagicMock()
    parser = MagicMock()
    parser.parse.return_value = MagicMock()
    controller = ChatController(
        config,
        pipeline,
        message_parser=parser,
        conversation_session=ConversationSession(),
        batch_worker_factory=MagicMock(),
    )
    return controller, parser


class TestChatController:
    def test_submit_message_blocks_while_previous_worker_running(self, qtbot):
        controller, _parser = make_controller(qtbot)
        running_worker = MagicMock()
        running_worker.isRunning.return_value = True
        controller.batch_worker = running_worker
        messages: list[str] = []
        controller.system_message.connect(messages.append)

        accepted = controller.submit_message("@./images")

        assert accepted is False
        assert messages

    def test_submit_message_creates_worker(self, qtbot):
        controller, parser = make_controller(qtbot)
        worker = MagicMock()
        controller._batch_worker_factory = MagicMock(return_value=worker)

        accepted = controller.submit_message("@./images", cwd=Path.cwd())

        assert accepted is True
        parser.parse.assert_called_once()
        worker.start.assert_called_once()

    def test_submit_directory_batch_creates_worker_without_parser(self, qtbot):
        controller, parser = make_controller(qtbot)
        worker = MagicMock()
        controller._batch_worker_factory = MagicMock(return_value=worker)
        settings = {
            "source_lang": "en",
            "target_lang": "ko",
            "ocr_plugin": "easyocr",
            "translator_plugin": "deepl",
            "agent_plugin": "claude",
            "use_agent": True,
        }

        accepted = controller.submit_directory_batch(Path("/tmp/images"), settings)

        assert accepted is True
        parser.parse.assert_not_called()
        worker.start.assert_called_once()
        parsed = controller._batch_worker_factory.call_args.kwargs["parsed"]
        assert parsed.directory_path == Path("/tmp/images")
        assert parsed.source_lang == "en"
        assert parsed.target_lang == "ko"
        assert parsed.ocr_plugin_id == "easyocr"
        assert parsed.translator_id == "deepl"
        assert parsed.agent_id == "claude"
        assert parsed.use_agent is True

    def test_submit_directory_batch_blocks_while_running(self, qtbot):
        controller, parser = make_controller(qtbot)
        running_worker = MagicMock()
        running_worker.isRunning.return_value = True
        controller.batch_worker = running_worker
        messages: list[str] = []
        controller.system_message.connect(messages.append)
        settings = {
            "source_lang": "auto",
            "target_lang": "ko",
            "ocr_plugin": "easyocr",
            "translator_plugin": "deepl",
            "agent_plugin": "claude",
            "use_agent": True,
        }

        accepted = controller.submit_directory_batch(Path("/tmp/images"), settings)

        assert accepted is False
        parser.parse.assert_not_called()
        assert messages

    def test_batch_completed_updates_last_directory(self, qtbot, tmp_path):
        controller, _parser = make_controller(qtbot)
        result = MagicMock()
        result.output_dir = tmp_path

        controller._on_batch_completed(result)

        assert controller.chat_session.last_directory == tmp_path
        assert controller.batch_worker is None

"""ChatAgent.resolve_params 단위 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.chat.chat_agent import ChatAgent
from src.chat.conversation import ConversationSession, ParsedMessage


def _make_parsed(
    directory_path: Path | None = None,
    target_lang: str | None = None,
) -> ParsedMessage:
    return ParsedMessage(
        raw_text="",
        directory_path=directory_path,
        target_lang=target_lang,
        translator_id=None,
        agent_id=None,
        output_dir=None,
        use_agent=None,
        intent=None,
    )


@pytest.fixture
def agent() -> ChatAgent:
    return ChatAgent(config={})


class TestResolveParams:
    def test_no_directory_returns_question(self, agent):
        """directory_path=None, last_directory=None → 경로 clarification 반환."""
        session = ConversationSession()
        parsed = _make_parsed(directory_path=None, target_lang="ko")

        result, question = agent.resolve_params(parsed, session)

        assert question is not None
        assert "경로" in question
        assert result is parsed  # 원본 그대로 반환

    def test_uses_session_last_directory(self, agent, tmp_path):
        """parsed.directory_path=None이어도 session.last_directory로 보완."""
        session = ConversationSession(last_directory=tmp_path)
        parsed = _make_parsed(directory_path=None, target_lang="ko")

        result, question = agent.resolve_params(parsed, session)

        assert question is None
        assert result.directory_path == tmp_path

    def test_no_target_lang_returns_question(self, agent, tmp_path):
        """directory_path 있고 target_lang=None, default_params 없음 → 언어 clarification."""
        session = ConversationSession()
        parsed = _make_parsed(directory_path=tmp_path, target_lang=None)

        result, question = agent.resolve_params(parsed, session)

        assert question is not None
        assert "언어" in question

    def test_uses_session_default_target_lang(self, agent, tmp_path):
        """target_lang=None이어도 session.default_params의 target_lang으로 보완."""
        session = ConversationSession(default_params={"target_lang": "en"})
        parsed = _make_parsed(directory_path=tmp_path, target_lang=None)

        result, question = agent.resolve_params(parsed, session)

        assert question is None
        assert result.target_lang == "en"

    def test_success_path(self, agent, tmp_path):
        """directory_path·target_lang 모두 있으면 (updated_parsed, None) 반환."""
        session = ConversationSession()
        parsed = _make_parsed(directory_path=tmp_path, target_lang="ja")

        result, question = agent.resolve_params(parsed, session)

        assert question is None
        assert result.directory_path == tmp_path
        assert result.target_lang == "ja"

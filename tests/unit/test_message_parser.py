"""MessageParser 단위 테스트 — TDD RED 단계."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.chat.conversation import ParsedMessage
from src.chat.message_parser import MessageParser


@pytest.fixture
def parser() -> MessageParser:
    return MessageParser()


@pytest.fixture
def cwd() -> Path:
    return Path("/home/user/project")


# ─── @경로 파싱 ──────────────────────────────────────────────────────────────

class TestPathParsing:
    def test_absolute_path(self, parser, cwd):
        result = parser.parse("@/home/user/images 번역해줘", cwd)
        assert result.directory_path == Path("/home/user/images")

    def test_relative_path(self, parser, cwd):
        result = parser.parse("@./images 번역해줘", cwd)
        assert result.directory_path == cwd / "images"

    def test_relative_parent_path(self, parser, cwd):
        result = parser.parse("@../other 번역해줘", cwd)
        assert result.directory_path == cwd / "../other"

    def test_double_quoted_path_with_spaces(self, parser, cwd):
        result = parser.parse('@"./my images folder" 번역해줘', cwd)
        assert result.directory_path == cwd / "my images folder"

    def test_single_quoted_path_with_spaces(self, parser, cwd):
        result = parser.parse("@'./my images' 번역해줘", cwd)
        assert result.directory_path == cwd / "my images"

    def test_no_path_returns_none(self, parser, cwd):
        result = parser.parse("번역해줘", cwd)
        assert result.directory_path is None

    def test_windows_forward_slash_path(self, parser, cwd):
        result = parser.parse("@C:/Users/YH/images 번역해줘", cwd)
        assert result.directory_path == Path("C:/Users/YH/images")

    def test_windows_backslash_path(self, parser, cwd):
        result = parser.parse(r"@C:\Users\YH\images 번역해줘", cwd)
        assert result.directory_path == Path(r"C:\Users\YH\images")

    def test_korean_directory_name(self, parser, cwd):
        result = parser.parse("@./만화 번역해줘", cwd)
        assert result.directory_path == cwd / "만화"

    def test_uses_first_path_when_multiple(self, parser, cwd):
        result = parser.parse("@./images @./other 번역해줘", cwd)
        assert result.directory_path == cwd / "images"

    def test_path_without_leading_dot_or_slash(self, parser, cwd):
        result = parser.parse("@images 번역해줘", cwd)
        assert result.directory_path == cwd / "images"


# ─── 목표 언어 파싱 ──────────────────────────────────────────────────────────

class TestTargetLangParsing:
    def test_explicit_lang_flag(self, parser, cwd):
        result = parser.parse("@./images --lang ko", cwd)
        assert result.target_lang == "ko"

    def test_explicit_lang_flag_english(self, parser, cwd):
        result = parser.parse("@./images --lang en", cwd)
        assert result.target_lang == "en"

    def test_natural_korean(self, parser, cwd):
        result = parser.parse("@./images 한국어로 번역해줘", cwd)
        assert result.target_lang == "ko"

    def test_natural_english(self, parser, cwd):
        result = parser.parse("@./images 영어로 번역해줘", cwd)
        assert result.target_lang == "en"

    def test_natural_japanese(self, parser, cwd):
        result = parser.parse("@./images 일본어로 번역해줘", cwd)
        assert result.target_lang == "ja"

    def test_natural_chinese(self, parser, cwd):
        result = parser.parse("@./images 중국어로 번역해줘", cwd)
        assert result.target_lang == "zh"

    def test_natural_french(self, parser, cwd):
        result = parser.parse("@./images 프랑스어로 번역해줘", cwd)
        assert result.target_lang == "fr"

    def test_no_lang_returns_none(self, parser, cwd):
        result = parser.parse("@./images 번역해줘", cwd)
        assert result.target_lang is None

    def test_explicit_flag_overrides_natural(self, parser, cwd):
        result = parser.parse("@./images 영어로 --lang ko", cwd)
        assert result.target_lang == "ko"


# ─── 번역기 파싱 ─────────────────────────────────────────────────────────────

class TestTranslatorParsing:
    def test_explicit_translator_flag(self, parser, cwd):
        result = parser.parse("@./images --translator deepl --lang ko", cwd)
        assert result.translator_id == "deepl"

    def test_natural_deepl(self, parser, cwd):
        result = parser.parse("@./images deepl로 한국어 번역", cwd)
        assert result.translator_id == "deepl"

    def test_natural_gemini(self, parser, cwd):
        result = parser.parse("@./images gemini 써줘", cwd)
        assert result.translator_id == "gemini"

    def test_natural_grok_translator(self, parser, cwd):
        result = parser.parse("@./images grok으로 번역", cwd)
        assert result.translator_id == "grok"

    def test_natural_papago(self, parser, cwd):
        result = parser.parse("@./images papago로 번역해줘", cwd)
        assert result.translator_id == "papago"

    def test_natural_ollama_translator(self, parser, cwd):
        result = parser.parse("@./images ollama로 번역해줘", cwd)
        assert result.translator_id == "ollama"

    def test_no_translator_returns_none(self, parser, cwd):
        result = parser.parse("@./images 한국어로 번역해줘", cwd)
        assert result.translator_id is None


# ─── 에이전트 파싱 ───────────────────────────────────────────────────────────

class TestAgentParsing:
    def test_explicit_agent_flag_claude(self, parser, cwd):
        result = parser.parse("@./images --agent claude --lang ko", cwd)
        assert result.agent_id == "claude"

    def test_explicit_agent_flag_openai(self, parser, cwd):
        result = parser.parse("@./images --agent openai --lang ko", cwd)
        assert result.agent_id == "openai"

    def test_explicit_no_agent_flag(self, parser, cwd):
        result = parser.parse("@./images --no-agent --lang ko", cwd)
        assert result.use_agent is False

    def test_natural_no_agent_korean(self, parser, cwd):
        result = parser.parse("@./images 에이전트 없이 번역해줘", cwd)
        assert result.use_agent is False

    def test_natural_openai_agent(self, parser, cwd):
        result = parser.parse("@./images openai 에이전트 사용해줘", cwd)
        assert result.agent_id == "openai"

    def test_natural_grok_agent(self, parser, cwd):
        result = parser.parse("@./images grok 에이전트로 해줘", cwd)
        assert result.agent_id == "grok"

    def test_natural_claude_agent(self, parser, cwd):
        result = parser.parse("@./images claude 에이전트 써줘", cwd)
        assert result.agent_id == "claude"

    def test_no_agent_flag_returns_none(self, parser, cwd):
        result = parser.parse("@./images 한국어로 번역해줘", cwd)
        assert result.use_agent is None
        assert result.agent_id is None


# ─── 출력 경로 파싱 ──────────────────────────────────────────────────────────

class TestOutputDirParsing:
    def test_explicit_output_flag(self, parser, cwd):
        result = parser.parse("@./images --output ./results --lang ko", cwd)
        assert result.output_dir == cwd / "results"

    def test_absolute_output_flag(self, parser, cwd):
        result = parser.parse("@./images --output /tmp/out --lang ko", cwd)
        assert result.output_dir == Path("/tmp/out")

    def test_no_output_returns_none(self, parser, cwd):
        result = parser.parse("@./images 한국어로 번역해줘", cwd)
        assert result.output_dir is None


# ─── ParsedMessage 기본 필드 ─────────────────────────────────────────────────

class TestParsedMessageFields:
    def test_preserves_raw_text(self, parser, cwd):
        msg = "@./images 한국어로 번역해줘"
        result = parser.parse(msg, cwd)
        assert result.raw_text == msg

    def test_intent_defaults_to_none(self, parser, cwd):
        result = parser.parse("@./images 한국어로 번역해줘", cwd)
        assert result.intent is None

    def test_returns_parsed_message_instance(self, parser, cwd):
        result = parser.parse("@./images 번역해줘", cwd)
        assert isinstance(result, ParsedMessage)


# ─── 복합 명령 ───────────────────────────────────────────────────────────────

class TestComplexCommands:
    def test_all_explicit_flags(self, parser, cwd):
        result = parser.parse(
            "@./manhwa --lang ko --translator deepl --agent claude --output ./out",
            cwd,
        )
        assert result.directory_path == cwd / "manhwa"
        assert result.target_lang == "ko"
        assert result.translator_id == "deepl"
        assert result.agent_id == "claude"
        assert result.output_dir == cwd / "out"

    def test_mixed_natural_and_flags(self, parser, cwd):
        result = parser.parse(
            "@./manhwa 한국어로 --translator gemini",
            cwd,
        )
        assert result.target_lang == "ko"
        assert result.translator_id == "gemini"

    def test_empty_message(self, parser, cwd):
        result = parser.parse("", cwd)
        assert result.directory_path is None
        assert result.target_lang is None

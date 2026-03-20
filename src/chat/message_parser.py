"""@경로 멘션 및 파라미터 파싱."""
from __future__ import annotations

import re
from pathlib import Path

from src.chat.conversation import ParsedMessage

# @"path" | @'path' | @token
_MENTION_RE = re.compile(r'@(?:"([^"]+)"|\'([^\']+)\'|(\S+))')

# 명시적 플래그
_FLAG_LANG = re.compile(r'--lang\s+(\S+)')
_FLAG_TRANSLATOR = re.compile(r'--translator\s+(\S+)')
_FLAG_AGENT = re.compile(r'--agent\s+(\S+)')
_FLAG_OUTPUT = re.compile(r'--output\s+(\S+)')
_FLAG_NO_AGENT = re.compile(r'--no-agent')

# 자연어 → BCP-47 언어 코드
_NATURAL_LANG: dict[str, str] = {
    "한국어": "ko",
    "영어": "en",
    "일본어": "ja",
    "중국어": "zh",
    "프랑스어": "fr",
    "독일어": "de",
    "스페인어": "es",
    "이탈리아어": "it",
    "러시아어": "ru",
    "포르투갈어": "pt",
    "베트남어": "vi",
    "태국어": "th",
    "인도네시아어": "id",
}

# 자연어 → 번역기 플러그인 ID
_TRANSLATOR_KEYWORDS: list[str] = ["deepl", "gemini", "grok", "papago", "ollama"]

# 에이전트 플러그인 ID
_AGENT_KEYWORDS: list[str] = ["claude", "openai", "gpt", "ollama", "grok"]
_AGENT_TRIGGER_KW = re.compile(r'에이전트\s*없이|에이전트\s*끄|no.?agent', re.IGNORECASE)
_AGENT_PROVIDER_RE = re.compile(
    r'(claude|openai|gpt|ollama|grok)\s+에이전트', re.IGNORECASE
)


def _normalize_path(token: str, cwd: Path) -> Path:
    """경로 토큰을 Path로 변환. 상대 경로는 cwd 기준으로 결합."""
    p = Path(token)
    if p.is_absolute():
        return p
    return cwd / p


class MessageParser:
    """채팅 메시지에서 @경로 멘션과 파라미터를 파싱하는 상태 없는 파서."""

    def parse(self, text: str, cwd: Path) -> ParsedMessage:
        """메시지를 파싱하여 ParsedMessage 반환.

        Args:
            text: 사용자 입력 메시지
            cwd: 상대 경로 기준 디렉토리

        Returns:
            파싱된 ParsedMessage (intent=None, LLM이 나중에 설정)
        """
        directory_path = self._parse_path(text, cwd)
        target_lang = self._parse_lang(text)
        translator_id = self._parse_translator(text)
        agent_id, use_agent = self._parse_agent(text)
        output_dir = self._parse_output(text, cwd)

        return ParsedMessage(
            raw_text=text,
            directory_path=directory_path,
            target_lang=target_lang,
            translator_id=translator_id,
            agent_id=agent_id,
            output_dir=output_dir,
            use_agent=use_agent,
            intent=None,
        )

    def _parse_path(self, text: str, cwd: Path) -> Path | None:
        m = _MENTION_RE.search(text)
        if not m:
            return None
        token = m.group(1) or m.group(2) or m.group(3)
        return _normalize_path(token, cwd)

    def _parse_lang(self, text: str) -> str | None:
        # 명시적 플래그 우선
        m = _FLAG_LANG.search(text)
        if m:
            return m.group(1)
        # 자연어 매핑
        for keyword, code in _NATURAL_LANG.items():
            if keyword in text:
                return code
        return None

    def _parse_translator(self, text: str) -> str | None:
        m = _FLAG_TRANSLATOR.search(text)
        if m:
            return m.group(1).lower()
        text_lower = text.lower()
        for kw in _TRANSLATOR_KEYWORDS:
            if kw in text_lower:
                # "grok 에이전트" 패턴이면 에이전트로 처리
                agent_pattern = re.search(rf'{kw}\s+에이전트', text, re.IGNORECASE)
                if agent_pattern:
                    continue
                return kw
        return None

    def _parse_agent(self, text: str) -> tuple[str | None, bool | None]:
        # --no-agent 플래그
        if _FLAG_NO_AGENT.search(text):
            return None, False
        # "에이전트 없이" 자연어
        if _AGENT_TRIGGER_KW.search(text):
            return None, False
        # --agent 플래그
        m = _FLAG_AGENT.search(text)
        if m:
            return m.group(1).lower(), None
        # 자연어: "{provider} 에이전트" 패턴
        m = _AGENT_PROVIDER_RE.search(text)
        if m:
            provider = m.group(1).lower()
            if provider == "gpt":
                provider = "openai"
            return provider, None
        return None, None

    def _parse_output(self, text: str, cwd: Path) -> Path | None:
        m = _FLAG_OUTPUT.search(text)
        if not m:
            return None
        return _normalize_path(m.group(1), cwd)

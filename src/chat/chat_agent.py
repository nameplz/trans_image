"""대화형 에이전트 — 사용자 명령 해석, 배치 처리 지시, 진행 보고."""
from __future__ import annotations

import dataclasses
import json
import re
from typing import Any

from src.chat.batch_processor import BatchResult
from src.chat.conversation import ConversationSession, ParsedMessage
from src.utils.logger import get_logger

logger = get_logger("trans_image.chat.agent")

_LANG_NAMES = {
    "ko": "한국어", "en": "영어", "ja": "일본어", "zh": "중국어",
    "fr": "프랑스어", "de": "독일어", "es": "스페인어",
}

_INTENT_SYSTEM = """You are a command interpreter for an image translation application.
Extract intent and parameters from the user message. Respond ONLY with JSON:
{
  "intent": "translate" | "status" | "cancel" | "help" | "unknown",
  "target_lang": "<BCP-47 code or null>",
  "translator_id": "deepl|gemini|grok|papago|ollama|null",
  "agent_id": "claude|openai|ollama|grok|gemini|null",
  "use_agent": true | false | null
}
Rules: If user mentions a language name (e.g. Korean, 한국어, Japanese), set target_lang.
If provider name appears near 에이전트/agent, set agent_id; otherwise set translator_id."""


class ChatAgent:
    """사용자 채팅 메시지를 해석하고 배치 처리를 조율하는 대화형 에이전트.

    이 클래스는 번역 보조 에이전트(AbstractAgentPlugin 구현체)와 완전히 다른 역할.
    - 파이프라인 내부에서 호출되지 않음
    - 사용자 인터페이스 레이어에서 명령 해석만 담당
    - 번역 API 직접 호출 금지
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self._provider = config.get("llm_provider", "anthropic")
        self._model = config.get("llm_model", "claude-haiku-4-5-20251001")
        self._api_key = config.get("api_key", "")
        self._client: Any = None

    # ── 공개 메서드 ──────────────────────────────────────────────────────────

    def resolve_params(
        self,
        parsed: ParsedMessage,
        session: ConversationSession,
    ) -> tuple[ParsedMessage, str | None]:
        """파싱된 메시지의 누락 파라미터를 세션 컨텍스트로 보완.

        Returns:
            (보완된 ParsedMessage, clarification_question | None)
            - clarification_question이 있으면 실행하지 않고 사용자에게 질문
        """
        # 경로 없음 → 세션의 last_directory 재사용
        directory_path = parsed.directory_path or session.last_directory

        if directory_path is None:
            return parsed, "번역할 이미지 경로를 알려주세요. (예: @./images)"

        # 목표 언어 없음 → 세션 기본값 또는 질문
        target_lang = (
            parsed.target_lang
            or session.default_params.get("target_lang")
        )
        if target_lang is None:
            return parsed, "목표 언어를 지정해주세요. (예: 한국어, 영어, 일본어)"

        updated = dataclasses.replace(
            parsed,
            directory_path=directory_path,
            target_lang=target_lang,
        )
        return updated, None

    def format_start(self, image_count: int, directory_path: Any, target_lang: str) -> str:
        """배치 시작 메시지."""
        lang_name = _LANG_NAMES.get(target_lang, target_lang)
        return (
            f"`{directory_path}`에서 이미지 {image_count}개를 찾았습니다. "
            f"{lang_name} 번역을 시작합니다."
        )

    def format_progress(self, image_name: str, current: int, total: int) -> str:
        """개별 이미지 완료 메시지."""
        return f"[{current}/{total}] {image_name} 완료"

    def format_failure(self, image_name: str, current: int, total: int, error: str) -> str:
        """개별 이미지 실패 메시지."""
        return f"[{current}/{total}] {image_name} 실패: {error}. 나머지는 계속 진행합니다."

    def format_result(self, result: BatchResult) -> str:
        """배치 완료 요약 메시지."""
        lines = [
            f"{result.total}개 중 {result.completed}개 번역 완료.",
        ]
        if result.failed:
            fail_names = ", ".join(p.name for p, _ in result.failed_files[:5])
            suffix = f" 외 {result.failed - 5}개" if result.failed > 5 else ""
            lines.append(f"{result.failed}개 실패: {fail_names}{suffix}")
        lines.append(f"저장 위치: `{result.output_dir}`")
        return " ".join(lines)

    # ── LLM 기반 의도 파악 (선택적) ─────────────────────────────────────────

    async def extract_intent_llm(self, text: str) -> dict[str, Any] | None:
        """LLM으로 자연어 의도를 추출. 실패 시 None 반환 (폴백용)."""
        try:
            client = await self._get_client()
            if client is None:
                return None
            response_text = await self._call_llm(client, text)
            return self._parse_json(response_text)
        except Exception as exc:
            logger.warning("LLM 의도 추출 실패 (폴백 사용): %s", exc)
            return None

    async def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            self._client = _build_client(self._provider, self._model, self._api_key)
        except Exception as exc:
            logger.warning("LLM 클라이언트 초기화 실패: %s", exc)
            return None
        return self._client

    async def _call_llm(self, client: Any, text: str) -> str:
        if self._provider == "anthropic":
            resp = await client.messages.create(
                model=self._model,
                max_tokens=256,
                system=_INTENT_SYSTEM,
                messages=[{"role": "user", "content": text}],
            )
            return resp.content[0].text
        else:
            resp = await client.chat.completions.create(
                model=self._model,
                max_tokens=256,
                messages=[
                    {"role": "system", "content": _INTENT_SYSTEM},
                    {"role": "user", "content": text},
                ],
            )
            return resp.choices[0].message.content

    def _parse_json(self, text: str) -> dict[str, Any] | None:
        text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
        return None


def _build_client(provider: str, model: str, api_key: str) -> Any:
    """LLM 클라이언트 팩토리. provider에 따라 적절한 클라이언트 반환."""
    match provider:
        case "anthropic":
            import anthropic
            return anthropic.AsyncAnthropic(api_key=api_key or None)

        case "openai":
            from openai import AsyncOpenAI
            return AsyncOpenAI(api_key=api_key or None)

        case "grok":
            from openai import AsyncOpenAI
            return AsyncOpenAI(
                api_key=api_key or None,
                base_url="https://api.x.ai/v1",
            )

        case "ollama":
            from openai import AsyncOpenAI
            return AsyncOpenAI(
                api_key="ollama",
                base_url="http://localhost:11434/v1",
            )

        case _:
            raise ValueError(f"지원하지 않는 LLM 프로바이더: {provider}")

# 지원 플러그인 목록

> CLAUDE.md에서 `@docs/plugins.md`로 참조됩니다.

## 번역 플러그인

| ID       | 파일                                 | API 키 설정                                   |
| -------- | ---------------------------------- | ------------------------------------------ |
| `deepl`  | `translators/deepl_translator.py`  | `DEEPL_API_KEY` 환경변수                       |
| `gemini` | `translators/gemini_translator.py` | `GOOGLE_API_KEY`                           |
| `grok`   | `translators/grok_translator.py`   | `XAI_API_KEY`                              |
| `papago` | `translators/papago_translator.py` | `PAPAGO_CLIENT_ID`, `PAPAGO_CLIENT_SECRET` |
| `ollama` | `translators/ollama_translator.py` | 로컬 (키 불필요)                                 |

## 에이전트 플러그인

| ID       | 파일                       | 모델                     |
| -------- | ------------------------ | ---------------------- |
| `claude` | `agents/claude_agent.py` | claude-sonnet-4-6 (기본) |
| `openai` | `agents/openai_agent.py` | gpt-4o                 |
| `ollama` | `agents/ollama_agent.py` | 로컬 (설정 가능)             |

## OCR 플러그인

| ID          | 파일                        | 특징         |
| ----------- | ------------------------- | ---------- |
| `easyocr`   | `ocr/easyocr_plugin.py`   | 기본, 80+ 언어 |
| `paddleocr` | `ocr/paddleocr_plugin.py` | CJK 특화     |

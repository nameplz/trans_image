# 대화형 에이전트 인터페이스 사양

사용자가 AI 에이전트와 텍스트로 소통하여 이미지 번역 작업을 지시하는 인터페이스.

---

## 관련 모듈

| 파일 | 역할 |
|------|------|
| `src/chat/chat_agent.py` | LLM 호출, 자연어 명령 해석, 응답 생성 |
| `src/chat/conversation.py` | 대화 세션 관리 (히스토리, 상태) |
| `src/chat/message_parser.py` | `@경로` 멘션 및 파라미터 파싱 |
| `src/chat/batch_processor.py` | 디렉토리 일괄 처리 오케스트레이션 |
| `src/gui/widgets/chat_panel.py` | 채팅 UI 위젯 (입력창, 메시지 표시) |

---

## @경로 멘션 문법

Claude Code의 `@파일` 멘션과 동일한 방식으로 디렉토리 경로를 지정한다.

```
@/절대/경로/디렉토리
@./상대/경로/디렉토리
@"C:/공백 포함/경로"
```

### 파싱 규칙 (`message_parser.py`)

1. `@` 뒤에 공백 없이 이어지는 토큰을 경로로 인식
2. 따옴표(`"` 또는 `'`)로 감싸면 공백 포함 경로 허용
3. 상대 경로는 앱 실행 시점의 CWD 기준으로 절대 경로로 정규화
4. 경로가 파일이면 해당 파일 단독 처리, 디렉토리이면 하위 이미지 전체 처리
5. 지원 확장자: `.png` `.jpg` `.jpeg` `.webp` `.bmp` `.tiff`

### 파라미터 파싱

메시지 본문에서 자연어로 지정하거나 명시적 플래그로 지정한다.

| 파라미터 | 자연어 예시 | 명시적 플래그 |
|----------|-------------|---------------|
| `target_lang` | "한국어로", "영어 번역" | `--lang ko` |
| `translator_id` | "DeepL 써줘", "gemini로" | `--translator deepl` |
| `agent_id` | "claude 에이전트", "openai 사용" | `--agent claude` |
| `output_dir` | "results 폴더에 저장" | `--output ./results` |
| `use_agent` | "에이전트 없이", "에이전트 켜줘" | `--no-agent` / `--agent` |

파싱 결과는 `ParsedMessage` dataclass로 반환:

```python
@dataclass
class ParsedMessage:
    raw_text: str               # 원본 메시지
    directory_path: Path | None # @경로에서 추출한 경로
    target_lang: str | None     # 목표 언어 코드
    translator_id: str | None   # 번역 플러그인 ID
    agent_id: str | None        # 번역 보조 에이전트 플러그인 ID
    output_dir: Path | None     # 출력 디렉토리 (None이면 자동 생성)
    use_agent: bool | None      # 번역 보조 에이전트 사용 여부
    intent: str | None          # LLM이 해석한 사용자 의도
```

---

## 대화 흐름

### 정상 흐름

```
[사용자] @./manhwa 한국어로 번역해줘
    ↓
message_parser: directory_path=Path("./manhwa"), target_lang="ko"
    ↓
chat_agent: 파라미터 확인 → 누락 항목 없으면 즉시 실행
    → "manhwa 디렉토리에서 12개 이미지를 찾았습니다. 번역을 시작합니다."
    ↓
batch_processor: 이미지 목록 수집 → ProcessingJob 생성 × 12
    ↓
Pipeline.run() 순차/병렬 실행
    ↓
chat_agent: 진행 상황 스트리밍
    → "[1/12] image001.png 완료"
    → "[2/12] image002.png 완료" ...
    ↓
완료 후 결과 요약
    → "12개 중 11개 번역 완료. 1개는 검토 필요 (image007.png). 저장 위치: ./manhwa_translated/"
```

### 파라미터 누락 시

```
[사용자] @./images 번역해줘
    ↓
chat_agent: target_lang 누락 감지
    → "목표 언어를 지정해주세요. (예: 한국어, 영어, 일본어)"
    ↓
[사용자] 한국어
    ↓
chat_agent: 파라미터 보완 후 실행
```

### 오류 처리

| 상황 | 에이전트 응답 |
|------|--------------|
| 경로가 존재하지 않음 | "경로를 찾을 수 없습니다: `{path}`" |
| 디렉토리에 이미지 없음 | "지원하는 이미지 파일이 없습니다. (지원: png, jpg, jpeg, webp, bmp, tiff)" |
| API 키 미설정 | "번역기 `{id}` 설정이 필요합니다. 환경변수 `{KEY_NAME}`을 확인해주세요." |
| 파이프라인 실패 | "image003.png 처리 실패: {오류 메시지}. 나머지 이미지는 계속 진행합니다." |

---

## 출력 디렉토리 규칙

```python
# output_dir 미지정 시 자동 생성 규칙
def default_output_dir(input_dir: Path) -> Path:
    return input_dir.parent / f"{input_dir.name}_translated"

# 예시
# @/home/user/manhwa  →  /home/user/manhwa_translated/
# @./screenshots      →  ./screenshots_translated/
```

출력 디렉토리가 이미 존재하면 덮어쓰기 전 확인 메시지를 표시한다.

---

## ConversationSession 상태 관리 (`conversation.py`)

```python
@dataclass
class ConversationSession:
    session_id: str
    messages: list[ChatMessage]         # 전체 대화 히스토리
    last_directory: Path | None         # 마지막으로 처리한 디렉토리
    pending_jobs: list[ProcessingJob]   # 진행 중 작업
    default_params: dict[str, Any]      # 세션 기본값 (언어, 번역기 등)
```

- 이전 대화 맥락을 유지하여 "다시 해줘", "이번엔 영어로" 같은 후속 명령 처리 가능
- `last_directory`를 기억하여 `@경로` 없이 재처리 가능

---

## GUI 채팅 패널 (`chat_panel.py`)

- 메시지 입력창: 엔터로 전송, Shift+Enter로 줄바꿈
- `@` 입력 시 경로 자동완성 드롭다운 표시 (파일 시스템 탐색)
- 에이전트 응답은 스트리밍으로 실시간 표시
- 진행 중 작업은 인라인 프로그레스바 표시
- `needs_review = True` 이미지는 결과 메시지에 경고 아이콘과 함께 목록화

---

## 대화형 에이전트 vs 번역 보조 에이전트

이 두 에이전트는 완전히 다른 역할이며 혼동하지 않는다.

| | 대화형 에이전트 | 번역 보조 에이전트 |
|--|----------------|-------------------|
| 위치 | `src/chat/chat_agent.py` | `src/plugins/agents/*.py` |
| 역할 | 사용자 명령 해석, 배치 처리 지시 | 파이프라인 내 OCR 보정·검증 |
| 호출 시점 | 사용자가 채팅 입력 시 | Pipeline 내부에서 자동 |
| LLM 목적 | 자연어 이해, 상태 보고 | OCR 교정, 컨텍스트, 검증 |
| 플러그인 여부 | 아님 | `AbstractAgentPlugin` 구현 |
| 번역 API 호출 | 금지 | 금지 (번역 플러그인에 위임) |

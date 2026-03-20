# trans_image — AI 기반 이미지 텍스트 자동 번역 프로그램

## 프로젝트 개요

이미지 속 텍스트를 자동으로 탐지·번역하고 원문 위치에 삽입하는 데스크탑 애플리케이션.

- **언어**: Python 3.11+
- **GUI**: PySide6 (Qt6)
- **아키텍처**: 플러그인 기반 — 번역 모델과 AI 에이전트 모두 교체 가능

## Git 규칙

.env 등의 시크릿 파일 commit, push 등 금지

## 핵심 아키텍처 원칙

1. **플러그인 분리**: OCR / 번역 / 에이전트 각각 별도 ABC (추상 기반 클래스)
2. **두 가지 에이전트 역할 구분** (혼동 금지):
   - **대화형 에이전트** (`src/chat/chat_agent.py`): 사용자와 텍스트로 소통. 자연어 명령 해석 → 배치 처리 트리거. 플러그인 아님.
   - **번역 보조 에이전트** (`src/plugins/agents/`): 파이프라인 내부에서 OCR 보정·컨텍스트 생성·번역 검증 담당. `AbstractAgentPlugin` 플러그인.
3. **에이전트 ≠ 번역기**: 번역 보조 에이전트는 번역 API 직접 호출 금지 — 파이프라인을 통해 번역 플러그인에 위임.
4. **비동기 우선**: 모든 플러그인 메서드는 async. QThread 내부에서 asyncio 루프 실행.
5. **GUI 응답성**: 처리 중 UI 블로킹 금지. PipelineWorker(QThread) + Signal 패턴 사용.

## 디렉토리 구조

```
trans_image/
├── main.py                 # 진입점
├── pyproject.toml
├── config/
│   ├── default_config.yaml
│   └── plugins.yaml        # 플러그인 레지스트리 (활성화/비활성화, API 키 참조)
├── docs/
│   ├── pipeline.md         # 파이프라인 상세 설명
│   ├── plugins.md          # 플러그인 개발 가이드
│   └── chat_interface.md   # 대화형 에이전트 인터페이스 사양
├── src/
│   ├── core/               # pipeline.py, plugin_manager.py, config_manager.py
│   ├── models/             # TextRegion, ProcessingJob, TranslationResult 데이터클래스
│   ├── plugins/
│   │   ├── base/           # ABC: PluginBase, AbstractOCRPlugin, AbstractTranslatorPlugin, AbstractAgentPlugin
│   │   ├── ocr/            # easyocr_plugin.py, paddleocr_plugin.py
│   │   ├── translators/    # deepl, gemini, grok, papago, ollama
│   │   └── agents/         # claude_agent, openai_agent, ollama_agent  ← 번역 보조 에이전트
│   ├── chat/               # 대화형 에이전트 인터페이스 (사용자 ↔ AI 소통)
│   │   ├── chat_agent.py   # 대화형 에이전트 (자연어 명령 해석, 배치 처리 지시)
│   │   ├── conversation.py # 대화 세션 관리 (메시지 히스토리, 상태)
│   │   ├── message_parser.py  # @경로 멘션 파싱
│   │   └── batch_processor.py # 디렉토리 일괄 처리 오케스트레이션
│   ├── services/           # ocr_service, language_service, inpainting_service, rendering_service, font_service
│   ├── gui/
│   │   ├── widgets/        # image_viewer, region_overlay, region_editor, comparison_view, chat_panel 등
│   │   ├── dialogs/
│   │   └── workers/        # pipeline_worker.py (QThread ↔ asyncio 브릿지)
│   └── utils/
├── assets/
│   ├── fonts/              # NotoSansCJK 서브셋 번들
│   └── styles/main.qss
└── tests/
    ├── unit/
    └── integration/
```

## 대화형 에이전트 인터페이스

> 상세 사양: [`docs/chat_interface.md`](docs/chat_interface.md)

사용자가 GUI 채팅 패널에서 AI 에이전트와 텍스트로 소통하여 번역 작업을 지시하는 인터페이스.

### @경로 멘션 입력 방식

Claude Code의 `@파일` 멘션과 동일한 방식으로 디렉토리 경로를 제공한다.

```
사용자: @C:/Users/YH/manhwa 이 폴더 이미지들 한국어로 번역해줘
사용자: @./screenshots DeepL로 영어 번역하고 새 폴더에 저장해줘
사용자: @/tmp/images 번역기는 gemini, 에이전트는 claude 써줘
```

- `@경로` 토큰은 `message_parser.py`가 파싱하여 절대 경로로 정규화
- 경로에 공백이 있으면 따옴표로 감싸기: `@"C:/My Images/folder"`
- 디렉토리 안의 지원 이미지 확장자: `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tiff`

### 배치 처리 흐름

```
사용자 메시지 수신
    → message_parser: @경로 추출 + 자연어 파라미터 파싱
        (target_lang, translator_id, agent_id, output_dir 등)
    → chat_agent: LLM에 의도 확인 및 파라미터 보완 요청
    → batch_processor: 디렉토리 내 이미지 목록 수집
    → 각 이미지에 대해 ProcessingJob 생성 → Pipeline.run()
    → 결과 이미지를 출력 디렉토리에 저장
    → chat_agent: 완료 메시지를 자연어로 사용자에게 전달
```

### 출력 디렉토리 규칙

| 입력 | 기본 출력 |
|------|---------|
| `@/path/to/images` | `/path/to/images_translated/` |
| `@./relative/dir` | `./relative/dir_translated/` |

사용자가 `--output` 또는 자연어로 다른 경로를 지정하면 해당 경로 우선.

### chat_agent vs 번역 보조 에이전트 역할 비교

| 구분 | 대화형 에이전트 (`src/chat/`) | 번역 보조 에이전트 (`src/plugins/agents/`) |
|------|------------------------------|------------------------------------------|
| 역할 | 사용자 명령 해석, 배치 처리 지시 | 파이프라인 내 OCR 보정·컨텍스트·검증 |
| 호출 주체 | 사용자 (채팅 패널) | Pipeline (자동, 선택적) |
| 구현 위치 | `src/chat/chat_agent.py` | `src/plugins/agents/*.py` |
| 플러그인 여부 | 아님 (core service) | `AbstractAgentPlugin` 구현체 |
| LLM 사용 목적 | 자연어 이해, 상태 보고 | OCR 교정, 컨텍스트 생성, 번역 검증 |

## 지원 플러그인

### 번역 플러그인

| ID       | 파일                                 | API 키 설정                                   |
| -------- | ---------------------------------- | ------------------------------------------ |
| `deepl`  | `translators/deepl_translator.py`  | `DEEPL_API_KEY` 환경변수                       |
| `gemini` | `translators/gemini_translator.py` | `GOOGLE_API_KEY`                           |
| `grok`   | `translators/grok_translator.py`   | `XAI_API_KEY`                              |
| `papago` | `translators/papago_translator.py` | `PAPAGO_CLIENT_ID`, `PAPAGO_CLIENT_SECRET` |
| `ollama` | `translators/ollama_translator.py` | 로컬 (키 불필요)                                 |

### 에이전트 플러그인

| ID       | 파일                       | 모델                     |
| -------- | ------------------------ | ---------------------- |
| `claude` | `agents/claude_agent.py` | claude-sonnet-4-6 (기본) |
| `openai` | `agents/openai_agent.py` | gpt-4o                 |
| `ollama` | `agents/ollama_agent.py` | 로컬 (설정 가능)             |

### OCR 플러그인

| ID          | 파일                        | 특징         |
| ----------- | ------------------------- | ---------- |
| `easyocr`   | `ocr/easyocr_plugin.py`   | 기본, 80+ 언어 |
| `paddleocr` | `ocr/paddleocr_plugin.py` | CJK 특화     |

## 핵심 데이터 구조

### TextRegion (`src/models/text_region.py`)

- `bbox`: BoundingBox (x, y, width, height, rotation)
- `raw_text`: OCR 인식 원문
- `detected_language`: lingua-py 감지 결과
- `confidence`: OCR 신뢰도 (0~1)
- `style`: TextStyle (폰트, 크기, 색상, 방향)
- `translated_text`: 번역 결과
- `context_hint`: 에이전트가 생성한 번역 컨텍스트
- `reading_order`: 올바른 읽기 순서 (만화 등)

### ProcessingJob (`src/models/processing_job.py`)

- `status`: JobStatus Enum (QUEUED → OCR_RUNNING → TRANSLATING → INPAINTING → RENDERING → COMPLETE)
- `source_lang`: 자동 감지 시 "auto"
- `target_lang`: 목표 언어 코드 (예: "ko", "en", "ja")
- `regions`: list[TextRegion]
- `original_image`, `inpainted_image`, `final_image`: numpy 배열

## 파이프라인 흐름

```
이미지 로드
    → OCR 플러그인 (바운딩박스 + 텍스트)
    → 에이전트.analyze_ocr_results() (오류 수정, 읽기 순서)
    → 언어 감지 서비스 (lingua-py)
    → 에이전트.generate_translation_context() (컨텍스트 힌트)
    → 번역 플러그인.translate_batch()
    → 에이전트.validate_translations() (일관성 검증)
    → 인페인팅 서비스 (원문 제거, OpenCV NS / LaMa)
    → 렌더링 서비스 (번역 텍스트 삽입, 폰트 자동 조절)
    → GUI 미리보기 → 내보내기
```

## 플러그인 개발 가이드

새 번역 플러그인 추가 시:

1. `src/plugins/base/translator_plugin.py`의 `AbstractTranslatorPlugin` 상속
2. `PLUGIN_NAME`, `PLUGIN_VERSION`, `PLUGIN_DESCRIPTION` 클래스 변수 설정
3. 필수 메서드 구현:
   - `load()` / `unload()` / `validate_config()` / `get_capabilities()`
   - `translate(text, source_lang, target_lang, context)` → `TranslationResult`
   - `translate_batch(regions, source_lang, target_lang)` → `list[TranslationResult]`
   - `get_supported_language_pairs()` → `list[tuple[str, str]]`
4. `config/plugins.yaml`의 `translators` 섹션에 등록

## 코딩 컨벤션

- Python 3.11+ 문법 사용 (예: `list[str]` 대신 `list[str]`, `X | Y` 유니온 타입)
- 모든 플러그인 메서드는 `async def`
- 데이터 전달은 dataclass 사용, dict 남용 금지
- GUI 스레드에서 절대 blocking I/O 호출 금지
- API 키는 환경변수 또는 `config/default_config.yaml`의 `api_keys` 섹션에서 로드
- 로깅: `src/utils/logger.py`의 구조화 로거 사용

## 주요 기술 주의사항

- **asyncio + Qt**: QThread 내부에서 `asyncio.new_event_loop()` 생성. 메인 스레드에서 `asyncio.run()` 호출 금지
- **EasyOCR 초기화**: 첫 실행 시 모델 다운로드 (수백 MB). 백그라운드 스레드에서 프리로드
- **인페인팅 마스크**: bbox를 `cv2.dilate()`로 팽창시켜 텍스트 스트로크 완전 제거
- **CJK 폰트**: 번들된 `assets/fonts/NotoSansCJK-*.ttf` 사용. 시스템 폰트 없을 때 폴백
- **언어 감지**: 전체 페이지 텍스트 연결 후 감지. 짧은 영역 단독 감지 신뢰도 낮음

## 환경 설정

```bash
# 의존성 설치
pip install -e ".[dev]"

# 실행
python main.py

# CLI 모드
python -m trans_image --input image.png --output result.png --target-lang ko --translator deepl --agent claude
```

## 테스트

```bash
pytest tests/unit/          # 단위 테스트
pytest tests/integration/   # 통합 테스트 (API 키 필요)
pytest --cov=src            # 커버리지 측정
```

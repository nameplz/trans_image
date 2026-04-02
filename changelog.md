# 📝 변경 이력 (Changelog)

> 매 세션 종료 시 업데이트됩니다.
> 형식: `## YYYY-MM-DD: [변경 요약]`

---

## 2026-04-02: Wave 2 완료 — GUI 위젯 연동 (Phase 5) + 단위 테스트 303개

### 수정 (버그)

- `src/models/text_region.py` — `is_manually_edited: bool = False` 필드 추가. `region_editor.py`에서 이미 이 속성에 쓰기를 하고 있었으나 dataclass 선언 누락으로 `AttributeError` 위험 존재
- `src/models/processing_job.py` — `is_running` property 추가. QTimer 리셋 콜백에서 진행 중인 job 여부 확인에 사용

### 추가 (Phase 5 구현)

- `src/gui/widgets/region_overlay.py` — `RegionOverlayItem.mousePressEvent()` 오버라이드 (ScrollHandDrag 모드와의 충돌 해소). `RegionOverlayManager`를 `QObject` 상속으로 변경하고 `region_selected = Signal(str)` 추가 (오버레이 클릭 이벤트 전파)
- `src/core/pipeline.py` — `reprocess_region()` async 메서드 추가. 단일 TextRegion의 번역만 재실행 후 기존 `inpainted_image`를 재사용하여 전체 regions 재렌더링하는 안전한 방식
- `src/gui/workers/pipeline_worker.py` — `RegionReprocessWorker(QThread)` 클래스 추가. 단일 영역 재처리 전용 워커. `region_reprocessed`, `region_reprocess_failed` 시그널 포함
- `src/gui/main_window.py` — Phase 5 연동 완성:
  - `_on_region_selected()` — 오버레이 클릭 → `RegionEditorPanel.load_region()` 연동 (5-1)
  - `_on_reprocess_requested()` / `_on_region_reprocess_done()` / `_on_region_reprocess_failed()` — 단일 영역 재처리 워커 생성·완료·실패 처리 (5-2)
  - `_on_job_done()`에 `self._tabs.setCurrentIndex(1)` 추가 — 작업 완료 시 비교 탭 자동 전환 (5-3)
  - `_do_reset_progress_if_idle()` — 완료/실패 후 QTimer 3초 → `progress_panel.reset()`. `is_running` 가드로 진행 중 다른 job이 있을 때 리셋 방지 (5-4)

### 테스트

- `tests/unit/test_main_window_phase5.py` — MainWindow Phase 5 슬롯/시그널 26개 테스트 (신규)
- `tests/unit/test_region_overlay_phase5.py` — `RegionOverlayItem` 콜백·`RegionOverlayManager` Signal 15개 테스트 (신규)
- `tests/unit/test_pipeline_reprocess.py` — `reprocess_region()` async 7개 테스트 (신규)
- 신규 테스트 **41개 추가**, 총 **303개 통과** (기존 3건 Windows 경로 하드코딩 실패는 이번 범위 외)

---

## 2026-04-01: Wave 1 완료 — 버그 수정 + 폰트 번들 + 단위 테스트 204개

### 수정 (버그)

- `src/models/processing_job.py` — `ProcessingJob.status_label` `@property` 추가 (`status.value` 반환). `pipeline_worker.py:69`, `job_queue_panel.py:62` 참조 오류 해소
- `src/models/text_region.py` — `TextStyle` Enum → dataclass 교체. `font_family`, `font_size`, `color`, `background_color`, `bold`, `italic` 필드 추가. `TextRegion.style` 기본값 `default_factory=TextStyle`로 변경
- `src/services/rendering_service.py` — `bg_color is not None` 가드 추가. 배경색 없는 영역에 빈 사각형이 그려지던 문제 수정
- `src/plugins/translators/gemini_translator.py`, `grok_translator.py`, `papago_translator.py` — `translate_batch`에서 frozen `TranslationResult`에 직접 대입(`res.region_id = ...`) → `dataclasses.replace()` 패턴으로 교체. `FrozenInstanceError` 방지

### 추가

- `scripts/download_fonts.py` — NotoSansCJKkr Regular/Bold OTF 자동 다운로드 스크립트 (`urllib.request` 전용, 진행률 표시, 이미 존재 시 스킵)
- `scripts/download_fonts.sh` — `download_fonts.py` 래퍼 셸 스크립트
- `assets/fonts/NotoSansCJKkr-Regular.otf` (16 MB), `assets/fonts/NotoSansCJKkr-Bold.otf` (17 MB) — 번들 폰트 파일
- `tests/conftest.py` — 프로젝트 공유 fixture (`mock_config`, `sample_image`, `sample_text_region`, `sample_regions`, `sample_job`)
- `tests/unit/test_session.py` — `Session` 클래스 11개 테스트
- `tests/unit/test_image_utils.py` — `resize_keep_aspect`, `crop_region`, 변환 왕복 7개 테스트
- `tests/unit/test_font_service.py` — 번들/폴백/캐시/`detect_text_color` 6개 테스트
- `tests/unit/test_inpainting_service.py` — 빈 regions, 마스크 생성, NS/LaMa 폴백 5개 테스트
- `tests/unit/test_rendering_service.py` — `_wrap_text`, `_fit_font_size`, bg_color 가드 7개 테스트
- `tests/unit/test_plugin_manager.py` — 로드/캐시/env 해석/`unload_all` 10개 테스트
- `tests/unit/test_pipeline.py` — `Pipeline.run()` 정상/취소/실패/에이전트 분기 12개 테스트
- `tests/unit/test_translator_plugins.py` — DeepL/Gemini/Grok/Papago/Ollama validate+translate+batch 20개 테스트
- `tests/unit/test_ocr_plugins.py` — EasyOCR/PaddleOCR mock 6개 테스트
- `tests/unit/test_agent_plugins.py` — Claude/OpenAI/Ollama analyze+context+validate 11개 테스트

### 테스트 결과

- 신규 테스트 **204개 통과** (`pytest tests/unit/ --ignore=tests/unit/test_message_parser.py`)
- 기존 `test_message_parser.py` 실패 3건 — Windows 경로 하드코딩 사전 존재 버그 (이번 범위 외)

---

## 2026-03-30: 구현 계획 수립 및 TODO.md 재구성

### 변경

- `TODO.md` — 기존 대기 항목 4개를 세부 작업으로 분해, Wave 1~5 병렬 실행 로드맵 추가
  - Wave 1: 잠재 버그 수정 + 폰트 번들 + 서비스/플러그인 테스트 (동시 3개)
  - Wave 2: GUI 위젯 연동 완성 (Phase 5)
  - Wave 3: GUI 위젯 테스트 + UX 편의 기능 (Phase C, 6)
  - Wave 4: 고급 기능 + 통합 테스트 (Phase 7, D)
  - Wave 5: PyInstaller 배포 패키징

### 발견된 잠재 버그 (수정 예정)

- `pipeline_worker.py:69`, `job_queue_panel.py:62` — `ProcessingJob.status_label` 미정의 참조
- `rendering_service.py` — `region.style`이 `TextStyle` Enum이므로 `.font_family`/`.font_size`/`.color` 접근 시 `AttributeError` 발생

---

## 2026-03-20: 채팅 기반 배치 이미지 번역 인터페이스 구현

### 추가

- `src/chat/conversation.py` — `ChatMessage`, `ParsedMessage`, `ConversationSession` 불변 데이터 모델
- `src/chat/message_parser.py` — `@경로` 멘션 파싱, `--lang`/`--translator`/`--agent`/`--no-agent` 플래그, 자연어 파라미터 추출 (9개 언어, deepl/gemini/grok/papago/ollama 번역기)
- `src/chat/batch_processor.py` — 디렉토리 이미지 스캔 (6개 확장자), `ProcessingJob` 배치 생성, 순차 실행 (개별 실패 시 계속 진행), `BatchResult` 요약
- `src/chat/chat_agent.py` — 명령 해석, 진행 메시지 포맷, LLM 의도 추출 팩토리 (anthropic/openai/grok/ollama)
- `src/gui/widgets/chat_panel.py` — PySide6 채팅 위젯 (`@` 자동완성, 인라인 진행 바, 중단 버튼)
- `src/gui/workers/batch_worker.py` — QThread↔asyncio 브릿지 배치 워커, 취소 지원
- `TODO.md` — 세션 간 작업 연속성 관리 파일
- `tests/unit/test_message_parser.py` — 44개 테스트
- `tests/unit/test_batch_processor.py` — 28개 테스트 (72/72 통과)

### 변경

- `src/gui/main_window.py` — ChatPanel 우측 패널 통합, `_on_chat_message` / `_cancel_batch` 슬롯 추가
- `config/default_config.yaml` — `chat` 섹션 추가 (llm_provider: anthropic|openai|ollama|grok)
- `pyproject.toml` — build-backend 수정 (`setuptools.backends.legacy:build` → `setuptools.build_meta`)

### 환경

- conda 가상환경 `trans_image` (Python 3.11) 구성, `pip install -e ".[dev]"` 의존성 설치

### 알려진 문제 (다음 세션 수정 예정, `TODO.md` 참조)

- **[C-1]** `config/default_config.yaml:32` — YAML 파싱 오류 (`deepl: env: DEEPL_API_KEY` 문자열 리터럴)
- **[H-1]** `message_parser.py` — 경로 순회 취약점
- **[H-2]** `batch_processor.py:87` — `ProcessingJob` 뮤테이션 패턴
- **[H-3]** `batch_worker.py:96` — 취소 플래그가 루프를 중단하지 않음
- **[H-4]** `main_window.py:310` — 이전 `BatchWorker` 미정리
- **[H-5]** `main_window.py:342` — `last_directory` 미갱신

---

## 2026-03-15: 프로젝트 초기 구조 구현 (Phase 1~4)

### 추가

- **데이터 모델** (`src/models/`) — `BoundingBox`, `TextStyle`, `TextRegion`, `ProcessingJob` (JobStatus 상태 머신), `TranslationResult`
- **플러그인 ABC** (`src/plugins/base/`) — `PluginBase`, `AbstractOCRPlugin`, `AbstractTranslatorPlugin`, `AbstractAgentPlugin`
- **OCR 플러그인** — EasyOCR (기본 활성), PaddleOCR (옵션, 비활성)
- **번역 플러그인 5종** — DeepL, Gemini, Grok (xAI), Papago, Ollama
- **에이전트 플러그인 3종** — Claude (claude-sonnet-4-6), OpenAI (gpt-4o), Ollama
- **서비스** — OCR 정규화/읽기순서, 언어 감지 (lingua-py + CJK Unicode), 인페인팅 (OpenCV NS / LaMa), 렌더링 (Pillow 이진탐색 폰트크기), 폰트 매칭/색상 감지
- **핵심 인프라** — `Pipeline` 오케스트레이터, `PluginManager` 동적 로드, `ConfigManager` YAML 관리, `Session` 작업 세션
- **GUI** — `MainWindow` (드래그앤드롭), `PipelineWorker` (QThread↔asyncio), 위젯 7종, 다이얼로그 2종
- **진입점** — `main.py` (GUI 모드), `src/__main__.py` (CLI 모드)
- **문서** (`docs/`) — pipeline.md, plugins.md, chat_interface.md

---

<!-- 최신 변경 이력을 위에 추가하세요 -->

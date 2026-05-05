# Changelog

## 2026-05-05: 프로젝트 정리 및 문서 정본 통합

- 루트 문서 참조를 `docs/` 정본 기준으로 정리
  - `AGENTS.md`, `CLAUDE.md`의 파이프라인 참조를 `docs/pipeline.md`로 통일
- 중복/임시 문서 정리
  - 루트 `plugins.md`, `pipeline.md`, `changelog.md`, `fix.md` 제거
  - 변경 이력은 `docs/changelog.md` 하나로 통합
- 로컬 환경 기본값 정리
  - `config/default_config.yaml`의 `app.recent_files` 절대경로 기본값 제거
- 로컬 작업 산출물 정리
  - `.claude/worktrees/` 작업 사본 제거
  - `.codex/`, `.claude/worktrees/`를 `.gitignore`에 추가
  - `trans_test_images_translated/`와 캐시/로그/egg-info 등 재생성 가능한 로컬 산출물 정리
- 유지
  - `trans_test_images/`는 테스트용 입력 자산으로 유지
  - `graphify-out/` 전체는 사용자 요청에 따라 유지

## 2026-04-28: Wave A 아키텍처 안정화 마감

- **A1 엔트리포인트/패키징 정합성**
  - `pyproject.toml`의 `trans-image` script를 `src.app:main`으로 정리
  - `main.py`는 GUI 공개 진입점만 호출하도록 정리
  - CLI 공개 진입점을 `python -m src` 기준으로 정리
  - `README.md`, `setup.md`의 실행 예시를 현재 공개 진입점 기준으로 갱신

- **A2 ConfigManager 단일 진실원 정리**
  - `ConfigManager.set()` 이후 typed settings snapshot 즉시 갱신
  - `SettingsPanel` 초기값과 저장 경로를 typed settings 기준으로 통일
  - `SettingsDialog`에서 `OK` 시 `ConfigManager.save()` 호출, 저장 실패는 다이얼로그 에러로 처리

- **A3 Pipeline 공개 경계 복구**
  - `Pipeline.export_image()` 공개 메서드 추가
  - GUI가 `Pipeline` 내부 구현(`_export_service`)에 직접 접근하지 않도록 제거
  - export 흐름을 `MainWindow -> JobController -> Pipeline` 경계로 정리

- **A4 WorkerPool / Session 책임 정리**
  - `WorkerPool.max_concurrent=2`를 실제 제한으로 강제
  - 동시 실행 초과 정책을 “즉시 거절”로 고정
  - `Session`은 작업 저장/조회만 담당하고, 실행 스케줄링은 `WorkerPool`이 담당하도록 역할 분리
  - 단일 이미지 작업은 제한 초과 시 UI 경고를 표시하고 rejected job을 세션에 남기지 않도록 정리

- **A5 검증 및 문서 정리**
  - 엔트리포인트, 설정 저장/재적용, export 공개 경계, 동시성 제한 회귀 테스트 보강
  - 실행/설정 동작 기준을 `README.md`, `setup.md`, `TODO.md`에 반영

- **테스트 및 검증**
  - 부분 회귀: 엔트리포인트/설정/UI/controller 관련 테스트 `91 passed`
  - 전체 회귀: `uv run pytest --cov=src --cov-report=term-missing` → `421 passed`, 총 커버리지 `82%`
  - `graphify update .` 실행으로 지식 그래프 최신화

## 2026-04-25: 설정 및 문서 정리

- `config/default_config.yaml` — API 설정 기본값과 환경변수 안내 정리
- `setup.md`, `README.md` — 환경변수/`.env` 기반 API 키 설정만 안내하도록 정리
- 기본 설정 파일에는 실제 시크릿을 저장하지 않는 정책으로 정리

## 2026-04-25: Gemini 번역 보조 에이전트 추가

- `src/plugins/agents/gemini_agent.py` — Google Gemini 기반 번역 보조 에이전트 플러그인 추가
  - OCR 결과 분석
  - 번역 컨텍스트 생성
  - 번역 검증
  - GUI용 스트리밍 분석
- `config/plugins.yaml` — `agents.gemini` 등록 (`GOOGLE_API_KEY`, `gemini-1.5-flash`)
- `src/chat/message_parser.py` — `gemini 에이전트` 자연어 파싱 지원
- `src/chat/chat_agent.py` — LLM intent schema의 `agent_id` 허용 목록에 `gemini` 추가
- `docs/plugins.md` — 지원 에이전트 목록에 Gemini 추가
- `tests/unit/test_agent_plugins.py`, `tests/unit/test_message_parser.py` 테스트 추가
- `uv run pytest tests/unit/test_agent_plugins.py tests/unit/test_message_parser.py` → `74 passed`

## 2026-04-25: Wave 4 완료 — 통합 테스트 보강 + 커버리지 81%

- `tests/integration/test_pipeline_e2e.py` — 더미 이미지와 mock 플러그인 기반 파이프라인 통합 테스트 3개 추가
- 커버리지 보강 단위 테스트 추가
  - `tests/unit/test_pipeline_worker.py`
  - `tests/unit/test_app_entrypoints.py`
  - `tests/unit/test_job_queue_panel.py`
  - `tests/unit/test_settings_dialog.py`
  - `tests/unit/test_theme.py`
  - `tests/unit/test_logger_utils.py`
- `TODO.md` — `[I] 항목 2 Phase D: 통합 테스트 보강` 완료 처리
- `graphify-out/` — `graphify update .` 실행으로 코드 그래프 갱신
- `uv run pytest tests/integration/test_pipeline_e2e.py tests/unit/test_pipeline_worker.py tests/unit/test_app_entrypoints.py tests/unit/test_job_queue_panel.py tests/unit/test_settings_dialog.py tests/unit/test_theme.py tests/unit/test_logger_utils.py` → `33 passed`
- `uv run pytest --cov=src --cov-report=term-missing` → `385 passed`, 총 커버리지 `81%`

## 2026-04-25: [H] Phase 7 고급 기능 완성

- **7-1 테마 전환**
  - `assets/styles/main.qss`를 제거하고 `assets/styles/dark.qss`, `assets/styles/light.qss`로 분리
  - `src/gui/theme.py` 신규 추가 — `app.theme` 설정값(`dark`/`light`) 기준으로 QSS 로드 및 폴백 처리
  - `src/app.py`에서 앱 시작 시 설정된 테마를 즉시 적용하도록 변경
  - `src/gui/main_window.py`에 `보기` 메뉴 추가, `다크 테마` / `라이트 테마` 단일 선택 액션과 즉시 저장(`ConfigManager.save()`) 연결
  - `src/gui/widgets/chat_panel.py`, `src/gui/widgets/image_viewer.py`, `src/gui/widgets/region_editor.py`의 하드코딩 색상 일부를 object/property 기반 QSS 스타일로 이동

- **7-2 에이전트 스트리밍 분석 UI**
  - `src/gui/widgets/chat_panel.py`: `start_stream()`, `append_stream_chunk()`, `finish_stream()` 추가
  - 동일 파일에 `QTimer` 기반 타이핑 애니메이션과 미완료 스트림 자동 종료 처리 추가
  - `src/gui/workers/batch_worker.py`: `agent_stream_chunk`, `agent_stream_finished` 시그널 추가
  - `src/gui/main_window.py`: worker 스트리밍 시그널을 `ChatPanel`로 중계하고, 일반 메시지 도착 시 미완료 스트림 정리하도록 보강

- **7-3 번역 편집 실시간 프리뷰**
  - `src/gui/widgets/region_editor.py`: `translation_preview_requested(region_id, draft_text)` 시그널 추가
  - `src/core/pipeline.py`: `preview_region_translation()` async API 추가
    - `job.regions`를 직접 수정하지 않고 `dataclasses.replace()`로 복사본을 만들어 전체 재렌더링
  - `src/gui/workers/pipeline_worker.py`: `RegionPreviewWorker(QThread)` 신규 추가
  - `src/gui/main_window.py`: `350ms` debounce, 최신 요청 번호 추적, 오래된 프리뷰 폐기, 적용 시 최근 성공 프리뷰를 `job.final_image`로 승격하는 흐름 추가

- **7-4 내보내기 옵션 강화**
  - `src/models/export_options.py` 신규 — `ExportOptions`, `ImageFormat`, `ResizeMode`
  - `src/services/export_service.py` 신규 — 저장 직전 포맷별 파라미터와 리사이즈 적용 공용 서비스
  - `src/gui/dialogs/export_dialog.py` 확장
    - JPEG 품질, WebP 품질, PNG 압축
    - 리사이즈 모드 3종 (`원본 유지`, `배율(%)`, `긴 변(px)`)
  - `src/core/pipeline.py`와 `src/gui/main_window.py`에서 공용 저장 로직 재사용
  - `config/default_config.yaml`에 `export.webp_quality`, `export.png_compression` 기본값 추가

- **테스트 및 검증**
  - 신규 테스트: `tests/unit/test_export_dialog.py`, `tests/unit/test_export_service.py`
  - 기존 테스트 확장: `tests/unit/test_chat_panel.py`, `tests/unit/test_batch_worker.py`, `tests/unit/test_main_window.py`, `tests/unit/test_pipeline.py`, `tests/unit/test_region_editor.py`
  - 검증: `QT_QPA_PLATFORM=offscreen UV_CACHE_DIR=/tmp/uv-cache uv run pytest tests/unit -q` → `347 passed`

- **부수 수정**
  - `src/chat/message_parser.py`: Windows 절대 경로(`C:/...`, `C:\...`)를 상대 경로로 잘못 붙이던 기존 테스트 실패 2건 수정
  - `graphify update .` 실행으로 `graphify-out/` 최신화


## 2026-04-08: [F] Phase C GUI 위젯 테스트 완성

- `tests/unit/test_image_viewer.py` 신규 — 12개 (set_image, zoom in/out/reset/clamp, fit_in_view, wheelEvent, signal emit)
- `tests/unit/test_region_editor.py` 신규 — 11개 (load_region, enable/disable, apply signal, translation_changed, clear, reprocess_requested)
- `tests/unit/test_settings_panel.py` 신규 — 7개 (초기값 로드, get_current_settings, apply → config.set, settings_changed signal, plugin 콤보박스)
- 신규 테스트 30개 전부 통과 (3개 에이전트 병렬 작성)

## 2026-04-02: [D] Phase 5 GUI 위젯 연동 완성 (TDD)

- **Phase 0** `src/models/text_region.py`: `TextRegion.is_manually_edited: bool = False` 필드 추가 (`region_editor.py`에서 설정하던 속성이 dataclass에 미선언이었던 버그 수정)
- **Phase 0** `src/models/processing_job.py`: `is_running` property 추가 (비종단·비대기 상태 판별)
- **5-1** `src/gui/widgets/region_overlay.py`: `RegionOverlayItem.mousePressEvent` 오버라이드 — `event.accept()` + 좌클릭 콜백 전달 (ScrollHandDrag 패닝 차단). `set_selection_callback()` 메서드 추가. `RegionOverlayManager`를 `QObject` 상속으로 변경, `region_selected = Signal(str)` 추가
- **5-1** `src/gui/main_window.py`: `_overlay_manager.region_selected` → `_on_region_selected()` 연결. `_on_region_selected()` 슬롯 추가 (overlay.select + editor.load_region)
- **5-2** `src/gui/workers/pipeline_worker.py`: `RegionReprocessWorker(QThread)` 클래스 추가 — 단일 영역 재번역+재렌더링을 비동기 실행
- **5-2** `src/core/pipeline.py`: `reprocess_region()` async 메서드 추가 — 해당 region만 번역 재실행 후 전체 regions로 재렌더링
- **5-2** `src/gui/main_window.py`: `_on_reprocess_requested()`, `_on_region_reprocess_done()`, `_on_region_reprocess_failed()` 슬롯 추가. `region_editor.reprocess_requested` 연결
- **5-3** `src/gui/main_window.py`: `_on_job_done()`에 `self._tabs.setCurrentIndex(1)` 추가
- **5-4** `src/gui/main_window.py`: `_on_job_done()`, `_on_job_failed()`에 `QTimer.singleShot(3000, self._do_reset_progress_if_idle)` 추가. `_do_reset_progress_if_idle()` 메서드 추가 (진행 중 job 가드)
- 신규 테스트 41개: `tests/unit/test_main_window_phase5.py`, `tests/unit/test_region_overlay_phase5.py`, `tests/unit/test_pipeline_reprocess.py`
- 전체: 303개 통과 (기존 3개 실패는 Windows 경로 이슈, 무관)

## 2026-04-01: Wave 1 완료 — 버그 수정 + 폰트 번들 + 단위 테스트 204개

- `src/models/processing_job.py` — `ProcessingJob.status_label` `@property` 추가
- `src/models/text_region.py` — `TextStyle` Enum → dataclass 교체
- `src/services/rendering_service.py` — `bg_color is not None` 가드 추가
- `src/plugins/translators/gemini_translator.py`, `grok_translator.py`, `papago_translator.py` — `dataclasses.replace()` 패턴으로 교체
- `scripts/download_fonts.py`, `scripts/download_fonts.sh` 추가
- `assets/fonts/NotoSansCJKkr-Regular.otf`, `assets/fonts/NotoSansCJKkr-Bold.otf` 번들 추가
- `tests/conftest.py`, `tests/unit/test_session.py`, `tests/unit/test_image_utils.py`, `tests/unit/test_font_service.py`, `tests/unit/test_inpainting_service.py`, `tests/unit/test_rendering_service.py`, `tests/unit/test_plugin_manager.py`, `tests/unit/test_pipeline.py`, `tests/unit/test_translator_plugins.py`, `tests/unit/test_ocr_plugins.py`, `tests/unit/test_agent_plugins.py` 추가
- `pytest tests/unit/ --ignore=tests/unit/test_message_parser.py` → 신규 테스트 `204개 통과`

## 2026-03-30: 구현 계획 수립 및 TODO.md 재구성

- `TODO.md` — 기존 대기 항목을 세부 작업으로 분해하고 Wave 1~5 병렬 실행 로드맵 추가
- 잠재 버그 후보를 다음 세션 작업 항목으로 정리

## 2026-03-20: 채팅 기반 배치 이미지 번역 인터페이스 구현

- `src/chat/conversation.py`, `src/chat/message_parser.py`, `src/chat/batch_processor.py`, `src/chat/chat_agent.py` 추가
- `src/gui/widgets/chat_panel.py`, `src/gui/workers/batch_worker.py` 추가
- `src/gui/main_window.py` — ChatPanel 우측 패널 통합, `_on_chat_message` / `_cancel_batch` 슬롯 추가
- `config/default_config.yaml` — `chat` 섹션 추가
- `pyproject.toml` — build backend를 `setuptools.build_meta`로 정리
- `tests/unit/test_message_parser.py`, `tests/unit/test_batch_processor.py` 추가
- `TODO.md` — 세션 간 작업 연속성 관리 파일 추가

## 2026-03-15: 프로젝트 초기 구조 구현 (Phase 1~4)

- 데이터 모델, 플러그인 ABC, OCR/번역/에이전트 플러그인, 서비스 계층, `Pipeline`, `PluginManager`, `ConfigManager`, `Session`, GUI, 진입점 기본 구조 구현
- 문서 초안으로 `docs/pipeline.md`, `docs/plugins.md`, `docs/chat_interface.md` 추가

## 2026-03-26: [M-1][M-2][M-3][Bug] 대기 중 이슈 병렬 처리

- **[M-1]** `src/chat/conversation.py`: `ChatMessage.metadata`를 `MappingProxyType`으로 래핑하여 불변성 강화
  - `from types import MappingProxyType` 추가, `__post_init__`에서 `dict` 인자를 자동 변환
- **[M-2]** `src/chat/batch_processor.py`: `scan_directory` docstring에 "하위 폴더 미포함" 명시
  - `src/gui/workers/batch_worker.py`: 이미지 없을 때 메시지에 "하위 폴더 미포함" 안내 추가
- **[M-3]** 테스트 커버리지 보강 — 3개 파일 신규 (17개 테스트 추가)
  - `tests/unit/test_chat_agent.py`: `resolve_params` 5개 분기 테스트
  - `tests/unit/test_batch_worker.py`: `_run_batch` 에러 경로 4개 테스트
  - `tests/unit/test_chat_panel.py`: 시그널·자동완성 로직 8개 테스트
- **[Bug]** `BoundingBox.to_xyxy()` 테스트 확인 → 이미 정상 (통과 중)
- 전체: 154개 중 152개 통과 (2개는 macOS에서 Windows 경로 테스트, 기존 사전 실패)

## 2026-03-26: [H-5] last_directory 미갱신 수정

- `src/gui/main_window.py` `_on_batch_completed`: `self._chat_session.last_directory = result.output_dir` 추가
- `tests/unit/test_main_window.py`: `TestOnBatchCompleted`에 테스트 2개 추가 (6/6 통과)
- 참고 파일: `src/gui/main_window.py`, `src/chat/conversation.py`



## 2026-03-26: [H-4] 이전 BatchWorker 미정리 수정

- `src/gui/main_window.py` `_on_chat_message`: 진입 시 `isRunning()` 확인, 실행 중이면 안내 메시지 후 얼리 리턴
- `src/gui/main_window.py` `_on_batch_completed`: 완료 후 `self._batch_worker = None` 참조 해제
- `tests/unit/test_main_window.py`: 신규 생성 — 이중 메시지 시나리오 4개 테스트 (4/4 통과)
- 참고 파일: `src/gui/main_window.py`, `tests/unit/test_main_window.py`



## 2026-03-26: [H-3] 취소 버튼 미작동 수정

- `src/chat/batch_processor.py`: `ProgressCallback` 반환 타입 `None` → `bool | None`; `on_progress()` 반환값이 `False`이면 루프 `break`
- `src/gui/workers/batch_worker.py`: `on_progress` 클로저가 취소 시 `False` 반환; `cancel()`에 `asyncio.all_tasks().cancel()` 추가; `self._loop` 필드로 루프 참조 보관; 취소 시 완료 신호 스킵
- `tests/unit/test_batch_processor.py`: 취소 테스트 2개 추가 (`test_cancels_mid_batch`, `test_none_return_does_not_cancel`)
- 참고 파일: `src/chat/batch_processor.py`, `src/gui/workers/batch_worker.py`, `tests/unit/test_batch_processor.py`



## 2026-03-26: [H-1] 경로 순회 취약점 + [H-2] ProcessingJob 뮤테이션 수정

- `src/chat/message_parser.py` `_normalize_path`: `os.path.normpath()`로 `..` 정규화 후 cwd 범위 벗어나면 `ValueError` 발생
- `src/chat/batch_processor.py` `scan_directory`: `path.is_dir()` 검증 추가
- `src/chat/batch_processor.py` `create_batch_jobs`: 생성 후 필드 직접 수정 제거, 생성자에 한 번에 전달
- `src/models/` 패키지 신규 생성 (`processing_job.py`, `text_region.py`, `translation_result.py`)
- `src/services/ocr_service.py`: computed property 직접 쓰기 제거
- `tests/unit/test_message_parser.py`: 경로 순회 방어 테스트 12개 추가
- `tests/unit/test_batch_processor.py`: 불변성 검증 테스트 추가
- `.gitignore`: `models/` → `assets/models/` 수정 (`src/models/` 소스 패키지 추적 허용)
- 참고 파일: `src/chat/message_parser.py`, `src/chat/batch_processor.py`, `src/models/`, `src/services/ocr_service.py`



## 2026-03-26: [C-1] YAML 파싱 오류 수정

- `config/default_config.yaml` 32-34번 줄의 `deepl: env: DEEPL_API_KEY` 형식을 빈 문자열(`""`)로 복원
  - 기존 형식이 YAML에서 `{"env": "DEEPL_API_KEY"}` 딕셔너리로 파싱되어 런타임 인증 오류 유발
- `src/core/config_manager.py` `get_api_key()` 에 비문자열 반환 방어 코드 추가
  - YAML 값이 `str`이 아닐 경우 경고 로그 출력 후 `""` 반환
- `tests/unit/test_config_manager.py` 단위 테스트 10개 추가
  - 환경변수 우선 조회, 빈 문자열 폴백, 딕셔너리 방어 케이스 커버
- 참고 파일: `config/default_config.yaml`, `src/core/config_manager.py`, `tests/unit/test_config_manager.py`
## 2026-04-24: Codex CLI 작업 지침 정리
- `AGENTS.md`를 추가해 Codex CLI 기준 프로젝트 작업 지침을 분리했다.
- `CLAUDE.md`를 레거시 안내 문서로 축소하고 참조 문서를 `AGENTS.md` 기준으로 정리했다.
- Claude Code 직접 언급이 있던 문서를 중립적인 표현으로 수정했다.

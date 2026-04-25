# Changelog

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

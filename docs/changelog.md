# Changelog

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

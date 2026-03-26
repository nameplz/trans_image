# Changelog

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

# Changelog

## 2026-03-26: [C-1] YAML 파싱 오류 수정

- `config/default_config.yaml` 32-34번 줄의 `deepl: env: DEEPL_API_KEY` 형식을 빈 문자열(`""`)로 복원
  - 기존 형식이 YAML에서 `{"env": "DEEPL_API_KEY"}` 딕셔너리로 파싱되어 런타임 인증 오류 유발
- `src/core/config_manager.py` `get_api_key()` 에 비문자열 반환 방어 코드 추가
  - YAML 값이 `str`이 아닐 경우 경고 로그 출력 후 `""` 반환
- `tests/unit/test_config_manager.py` 단위 테스트 10개 추가
  - 환경변수 우선 조회, 빈 문자열 폴백, 딕셔너리 방어 케이스 커버
- 참고 파일: `config/default_config.yaml`, `src/core/config_manager.py`, `tests/unit/test_config_manager.py`

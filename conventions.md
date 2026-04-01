# 코딩 컨벤션

> CLAUDE.md에서 `@docs/conventions.md`로 참조됩니다.

## Python 스타일

- Python 3.11+ 문법 사용 (`list[str]`, `X | Y` 유니온 타입 등)
- 모든 플러그인 메서드는 `async def`
- 데이터 전달은 dataclass 사용, dict 남용 금지
- GUI 스레드에서 절대 blocking I/O 호출 금지
- API 키는 환경변수 또는 `config/default_config.yaml`의 `api_keys` 섹션에서 로드
- 로깅: `src/utils/logger.py`의 구조화 로거 사용

## 스크립트 원칙

- 단일 책임 — 하나의 스크립트는 하나의 작업만
- 거대한 `all-in-one` 스크립트 금지
- 결과는 `output/` 폴더에 JSON 또는 Markdown으로 저장

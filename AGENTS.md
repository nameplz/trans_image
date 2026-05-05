# trans_image — Codex CLI 작업 지침

## 프로젝트 개요

이미지 속 텍스트를 자동으로 탐지·번역하고 원문 위치에 삽입하는 데스크탑 애플리케이션.

- 언어: Python 3.11+
- GUI: PySide6 (Qt6)
- 아키텍처: 플러그인 기반 — OCR / 번역 / 보조 에이전트 교체 가능

## 상세 문서 참조

필요한 문서만 선택해서 읽는다.

- 플러그인 개발 가이드: `plugin-dev-guide.md`
- 지원 플러그인 전체 목록: `docs/plugins.md`
- 핵심 데이터 구조 상세: `data-models.md`
- 파이프라인 흐름 상세: `pipeline.md`
- 코딩 컨벤션: `conventions.md`
- 환경 설정 & 실행: `setup.md`
- 변경 이력: `docs/changelog.md`

## Git 규칙

- `.env` 등 시크릿 파일 commit / push 금지
- 시크릿 값은 문서나 로그에 직접 복사하지 않는다

## 핵심 아키텍처 원칙

1. 플러그인 분리: OCR / 번역 / 에이전트는 각각 별도 ABC로 유지한다.
2. 에이전트 ≠ 번역기: 보조 에이전트는 OCR 분석, 컨텍스트 생성, 검증만 담당한다.
3. 비동기 우선: 플러그인 메서드는 `async`를 기본으로 한다.
4. GUI 응답성 유지: 처리 중 UI 블로킹 금지. `QThread` + Signal 패턴을 유지한다.

## 디렉토리 구조

```text
trans_image/
├── AGENTS.md
├── CLAUDE.md
├── TODO.md
├── docs/
├── config/
├── src/
├── assets/
└── tests/
```

## 작업 원칙

### 세션 관리

- 한 세션에서 한 작업 단위를 끝내는 것을 기본으로 한다.
- 세션 시작 시 `TODO.md`를 확인하고, 진행 중 항목과 우선순위를 파악한다.
- 세션 종료 시 `TODO.md`와 필요 시 `docs/changelog.md`를 갱신한다.
- 컨텍스트가 커지면 현재 상태를 요약해 문서나 작업 메시지에 남기고 이어서 진행한다.

### 구현 루프

- 복잡한 변경은 먼저 계획을 세운 뒤 구현한다.
- 작은 변경 단위로 테스트와 검증을 반복한다.
- 추정에 의존하지 말고 코드, 설정, 테스트 결과로 판단한다.
- 에러 로그는 요약 전에 원문 기준으로 확인한다.

### 검증

- 단위 테스트 우선, 필요한 경우 통합 테스트까지 실행한다.
- 가능하면 변경 범위에 가까운 테스트부터 실행한다.
- 린트와 타입 체크가 필요한 변경이면 함께 확인한다.

## 자주 쓰는 명령

```bash
uv sync
uv run python main.py
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run ruff check .
uv run mypy src
```

## 주요 기술 주의사항

- `asyncio + Qt`: QThread 내부에서 이벤트 루프를 생성한다.
- EasyOCR은 첫 실행 시 모델 다운로드가 발생할 수 있다.
- 인페인팅 마스크는 텍스트 스트로크가 남지 않도록 충분히 팽창시킨다.
- CJK 폰트는 번들 폰트를 우선 사용한다.
- 짧은 단일 영역의 언어 감지는 신뢰도가 낮을 수 있다.

## 출력 원칙

- 답변은 요청 범위만 다룬다.
- 핵심 결과와 검증 상태를 먼저 전달한다.
- 모르는 사실은 추정하지 말고 확인 후 적는다.

## graphify

This project has a graphify knowledge graph at graphify-out/.

Rules:
- Before answering architecture or codebase questions, read graphify-out/GRAPH_REPORT.md for god nodes and community structure
- If graphify-out/wiki/index.md exists, navigate it instead of reading raw files
- For cross-module "how does X relate to Y" questions, prefer `graphify query "<question>"`, `graphify path "<A>" "<B>"`, or `graphify explain "<concept>"` over grep — these traverse the graph's EXTRACTED + INFERRED edges instead of scanning files
- After modifying code files in this session, run `graphify update .` to keep the graph current (AST-only, no API cost)

# 📋 TODO.md

> 세션 시작 시 Claude가 이 파일을 읽고 첫 번째 미완료 항목부터 시작합니다.
> 세션 종료 시 진행 상황을 자동으로 반영합니다.

---

## 🔥 진행 중

_없음_

---

## 🚨 코드 리뷰 수정 필요 (커밋 블록 중)

> `/code-review` 결과 — CRITICAL 1건 + HIGH 5건. 수정 완료 후 커밋할 것.

### CRITICAL

- [x] **[C-1] YAML 파싱 오류** `config/default_config.yaml:32-34`
  - 문제: `deepl: env: DEEPL_API_KEY` 형식이 문자열 리터럴로 파싱됨 → 런타임 인증 오류
  - 수정: 빈 문자열(`""`)로 복원 + `get_api_key()` 비문자열 방어 코드 추가

### HIGH

- [x] **[H-1] 경로 순회 취약점** `src/chat/message_parser.py` `_normalize_path`
  - 문제: `@../../../etc/passwd` 같은 경로를 무제한 허용
  - 수정: `_normalize_path`에서 cwd 범위 벗어나면 `ValueError`, `scan_directory`에 `is_dir()` 검증 추가

- [x] **[H-2] ProcessingJob 뮤테이션** `src/chat/batch_processor.py:87-93`
  - 문제: 객체 생성 후 필드 직접 수정 — 프로젝트 불변 패턴 위반
  - 수정: `ProcessingJob(...)` 생성자에 모든 필드를 한 번에 전달, `src/models/` 패키지 신규 생성

- [x] **[H-3] 취소 버튼 미작동** `src/gui/workers/batch_worker.py:96-104`
  - 문제: `_cancelled=True`로 설정해도 `run_batch` 루프가 계속 실행됨
  - 수정: `ProgressCallback` 반환값 `bool | None` 추가, `False` 반환 시 루프 `break`; `cancel()`에 asyncio 태스크 취소 추가

- [x] **[H-4] 이전 BatchWorker 미정리** `src/gui/main_window.py:310-336`
  - 문제: 이전 워커가 실행 중일 때 새 메시지가 오면 시그널 중복 발행
  - 수정: `_on_chat_message` 진입 시 `isRunning()` 확인 후 얼리 리턴; `_on_batch_completed`에서 `_batch_worker = None` 초기화

- [x] **[H-5] last_directory 미갱신** `src/gui/main_window.py:342-344`
  - 문제: `_on_batch_completed`에서 `session.last_directory`가 갱신되지 않아 경로 재사용 미동작
  - 수정: `self._chat_session.last_directory = result.output_dir` 추가

---

## 📌 대기 중

- [x] **[M-1] ChatMessage.metadata 불완전한 불변성** `src/chat/conversation.py:17`
  - `MappingProxyType`으로 래핑, `__post_init__`에서 dict 자동 변환

- [x] **[M-2] 비재귀 스캔 사용자 안내 부재** `src/chat/batch_processor.py:56`
  - docstring에 "하위 폴더 미포함" 명시, batch_worker.py 빈 이미지 메시지에 안내 추가

- [x] **[M-3] 테스트 커버리지 보강**
  - `tests/unit/test_chat_agent.py` — `resolve_params` 5개 분기 테스트 추가
  - `tests/unit/test_batch_worker.py` — `_run_batch` 에러 경로 4개 테스트 추가
  - `tests/unit/test_chat_panel.py` — 시그널·자동완성 8개 테스트 추가

- [ ] **Phase 5~7 GUI 고급 기능 구현**
- [ ] **테스트 커버리지 80%+ 달성**
- [ ] **NotoSansCJK 폰트 번들 추가** (`assets/fonts/`)
- [ ] **PyInstaller 배포 패키징**

---

## 🐛 버그

- [x] `src/models/text_region.py` `BoundingBox.to_xyxy()` — y2 계산 오프바이원 오류
  - 확인 결과 테스트 통과 중 (이미 해결됨)

---

## ✅ 완료

- [x] 프로젝트 초기 구조 구현 (Phase 1~4)
- [x] conda 가상환경 `trans_image` 구성 (Python 3.11)
- [x] 채팅 기반 배치 번역 인터페이스 설계 및 구현
  - `src/chat/` 모듈 신규 생성 (conversation, message_parser, batch_processor, chat_agent)
  - `src/gui/widgets/chat_panel.py` — PySide6 채팅 UI
  - `src/gui/workers/batch_worker.py` — QThread↔asyncio 브릿지
  - `config/default_config.yaml` — chat 섹션 추가 (grok 포함 4개 LLM 프로바이더)
- [x] TDD: test_message_parser (44개), test_batch_processor (28개) — 72/72 통과

---

> **사용법**: 세션 시작 시 "TODO.md 읽고 첫 번째 항목부터 시작해" 라고 지시하세요.

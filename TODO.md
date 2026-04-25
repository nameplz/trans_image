# 📋 TODO.md

> 세션 시작 시 Claude가 이 파일을 읽고 첫 번째 미완료 항목부터 시작합니다.
> 세션 종료 시 진행 상황을 자동으로 반영합니다.

---

## 🔥 진행 중

_없음_

---

## 🗺️ 병렬 실행 로드맵

```
Wave 1 (동시 3개) ─────────────────────────────────────────
  [A] 잠재 버그 2건 수정
  [B] 항목 3: NotoSansCJK 폰트 번들
  [C] 항목 2 Phase A+B: 서비스/플러그인 단위 테스트

Wave 2 (동시 2개) ─────────────────────────────────────────
  [D] 항목 1 Phase 5: GUI 위젯 연동 완성   ← [A] 완료 후
  [E] (Wave 1 테스트 커버리지 보완)

Wave 3 (동시 2개) ─────────────────────────────────────────
  [F] 항목 2 Phase C: GUI 위젯 테스트      ← [D] 완료 후
  [G] 항목 1 Phase 6: UX 편의 기능        ← [D] 완료 후

Wave 4 (동시 2개) ─────────────────────────────────────────
  [H] 항목 1 Phase 7: 고급 기능           ← [G] 완료 후
  [I] 항목 2 Phase D: 통합 테스트 보강    ← [F] 완료 후

Wave 5 (단독) ─────────────────────────────────────────────
  [J] 항목 4: PyInstaller 배포 패키징     ← 전체 안정화 후
```

---

## 🐛 먼저 수정할 잠재 버그 `Wave 1 - [A]`

- [x] **`ProcessingJob.status_label` 미정의** — `@property status_label` 추가 (`status.value` 반환)
- [x] **`rendering_service.py` `region.style` 속성 오류** — `TextStyle` Enum → dataclass 교체 (`font_family`, `font_size`, `color`, `background_color`, `bold`, `italic`), `bg_color is not None` 가드 추가

---

## 📌 대기 중

### [B] 항목 3: NotoSansCJK 폰트 번들 추가 `Wave 1` ✅

- [x] `scripts/download_fonts.py` + `download_fonts.sh` 작성
- [x] `NotoSansCJKkr-Regular.otf` (16MB), `NotoSansCJKkr-Bold.otf` (17MB) → `assets/fonts/` 다운로드 완료
- [x] `FontService._BUNDLED_FONTS` 파일명 일치 확인 (변경 불필요)
- [x] `.gitattributes` `*.otf binary` 이미 설정됨 (LFS 불필요)

---

### [C] 항목 2 Phase A+B: 단위 테스트 `Wave 1` ✅

- [x] `tests/conftest.py` — 공유 fixture (mock_config, sample_image, sample_regions, sample_job)
- [x] `tests/unit/test_pipeline.py` — 12개
- [x] `tests/unit/test_session.py` — 11개
- [x] `tests/unit/test_plugin_manager.py` — 10개
- [x] `tests/unit/test_font_service.py` — 6개
- [x] `tests/unit/test_inpainting_service.py` — 5개
- [x] `tests/unit/test_rendering_service.py` — 7개
- [x] `tests/unit/test_image_utils.py` — 7개
- [x] `tests/unit/test_translator_plugins.py` — 20개 (DeepL/Gemini/Grok/Papago/Ollama)
- [x] `tests/unit/test_ocr_plugins.py` — 6개
- [x] `tests/unit/test_agent_plugins.py` — 11개
- [x] 부수 버그 수정: Gemini/Grok/Papago `translate_batch` FrozenInstanceError (`dataclasses.replace` 사용)

---

### [D] 항목 1 Phase 5: GUI 위젯 연동 완성 `Wave 2` ✅

- [x] **Phase 0** `TextRegion.is_manually_edited` 필드 추가 (dataclass 선언 누락 수정)
- [x] **5-1.** 오버레이 클릭 → RegionEditorPanel 연동 (`RegionOverlayManager.region_selected` → `_on_region_selected()` → `load_region()`)
- [x] **5-2.** 재처리 핸들러 구현 (`reprocess_requested` → `_on_reprocess_requested()` → `RegionReprocessWorker`)
- [x] **5-3.** 작업 완료 후 자동 비교 탭 전환 (`_on_job_done()`에 `setCurrentIndex(1)`)
- [x] **5-4.** 진행 패널 자동 리셋 (완료/실패 후 `QTimer.singleShot(3000, ...)` → `_do_reset_progress_if_idle()`)

---

### [F] 항목 2 Phase C: GUI 위젯 테스트 `Wave 3` ✅

- [x] `tests/unit/test_image_viewer.py` — 12개 (set_image/zoom/fit_in_view/wheelEvent/signal/clamp)
- [x] `tests/unit/test_region_editor.py` — 11개 (load_region/enable/apply/signal/clear/reprocess)
- [x] `tests/unit/test_settings_panel.py` — 7개 (초기값/get_current_settings/apply/signal/plugin목록)

### [G] 항목 1 Phase 6: UX 편의 기능 `Wave 3` _([D] Phase 5 이후)_

- [ ] **6-1.** 키보드 단축키 체계 (Ctrl+O, Ctrl+Shift+O, F5, Escape, Ctrl+S, Ctrl+,)
- [ ] **6-2.** 폴더 열기 + 다중 이미지 일괄 처리 (`_open_folder()` 신규)
- [ ] **6-3.** 최근 파일 히스토리 — ConfigManager에 `recent_files`(최대 10개) + 메뉴 서브메뉴
- [ ] **6-4.** 드래그앤드롭 폴더 지원 (`dropEvent()`에서 폴더 URL 감지 후 `_open_folder()` 분기)

---

### [H] 항목 1 Phase 7: 고급 기능 `Wave 4` _([G] Phase 6 이후)_

- [x] **7-1.** 다크/라이트 테마 전환 (`assets/styles/light.qss` 추가 + 메뉴 토글)
- [x] **7-2.** 에이전트 스트리밍 분석 UI (ChatPanel에 토큰 단위 스트리밍 + 타이핑 애니메이션)
- [x] **7-3.** 번역 편집 시 실시간 렌더링 프리뷰 (단일 영역 재렌더링 후 ImageViewer 갱신)
- [x] **7-4.** 내보내기 옵션 강화 (JPEG 품질 슬라이더, WebP 품질, PNG 압축, 리사이즈 옵션)

### [I] 항목 2 Phase D: 통합 테스트 보강 `Wave 4` _([F] Phase C 이후)_

- [x] `tests/integration/test_pipeline_e2e.py` — 더미 이미지 + 전 플러그인 mock 으로 E2E 3개 추가
- [x] 커버리지 보강 테스트 추가: `test_pipeline_worker.py`, `test_app_entrypoints.py`, `test_job_queue_panel.py`, `test_settings_dialog.py`, `test_theme.py`, `test_logger_utils.py`
- [x] `pytest --cov=src` 실행 후 커버리지 80%+ 확인 (`81%`, 385 passed)

---

### [J] 항목 4: PyInstaller 배포 패키징 `Wave 5` _(모든 기능 안정화 후 마지막)_

- [ ] `src/utils/path_utils.py` 신규 — `get_resource_path()` (`sys._MEIPASS` 기반)
- [ ] `config_manager.py`, `font_service.py`, `app.py` 리소스 경로를 `get_resource_path()` 사용으로 교체
- [ ] `trans_image.spec` 작성 — hidden imports, data files(`assets/`, `config/`), `--onedir --windowed`
- [ ] EasyOCR 모델은 런타임 다운로드 유지 (전략 A — 배포 크기 절감)
- [ ] `scripts/build.sh` 빌드 스크립트 작성
- [ ] `assets/icon.ico` 아이콘 파일 추가 후 spec에 등록
- [ ] Windows에서 빌드 실행 + `dist/trans_image/trans_image.exe` 동작 확인

---

## ✅ 완료

- [x] Phase 1~4 기본 구조 구현
- [x] 채팅 기반 배치 이미지 번역 인터페이스 구현
- [x] uv 마이그레이션

---

> **사용법**: 세션 시작 시 "TODO.md 읽고 첫 번째 항목부터 시작해" 라고 지시하세요.

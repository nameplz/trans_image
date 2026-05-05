# 코드 리뷰 수정 사항 목록

## P0 — 즉시 수정 필요 (런타임 크래시)

### 1. `src/core/pipeline.py` — `agent` 변수 미초기화
**문제:** `use_agent`가 False이거나 `agent_analyze`가 비활성화된 경우, `agent` 변수가 정의되지 않은 상태에서 번역 컨텍스트 생성 단계(라인 114)에서 참조되어 `NameError` 발생.

**현재 코드:**
```python
if job.use_agent and self._config.get("processing", "agent_analyze"):
    agent = self._plugins.get_agent_plugin(job.agent_plugin_id)
    ...

# 이후 별도 블록에서 agent 재사용 → agent 미정의 시 NameError
if job.use_agent and self._config.get("processing", "agent_analyze"):
    context_hints = await agent.generate_translation_context(regions, job)
```

**수정 방향:** `agent` 변수를 파이프라인 시작 시 한 번만 초기화하거나, 각 블록에서 독립적으로 로드.

---

### 2. `src/gui/main_window.py` — 이미지 경로 파싱 버그
**문제:** 처리 시작 시 상태 바 메시지에서 경로를 추출하는 로직 오류. `replace`로 접두사를 제거한 뒤 동일 문자열을 다시 검사하여 `path`가 항상 `None`이 됨.

**현재 코드:**
```python
path_str = self._status_bar.currentMessage().replace("로드: ", "")
path = Path(path_str) if "로드:" not in path_str else None  # 항상 None
```

**수정 방향:** 상태 바 메시지 대신 인스턴스 변수(`self._current_image_path`)로 현재 로드된 경로를 별도 관리.

---

### 3. `src/plugins/ocr/easyocr_plugin.py` — EasyOCR Reader 매번 재생성
**문제:** `detect_regions` 호출 시마다 `_readtext_sync` 내부에서 새 `easyocr.Reader`를 생성. EasyOCR Reader 초기화는 수 초가 소요되어 실사용 시 극심한 성능 저하 발생.

**현재 코드:**
```python
def _readtext_sync(self, image, languages):
    import easyocr
    reader = easyocr.Reader(languages, gpu=self._gpu)  # 매번 생성!
    return reader.readtext(image, detail=1)
```

**수정 방향:** 언어 목록을 키로 하는 Reader 캐시 딕셔너리(`self._reader_cache`) 도입. 동일 언어 조합 재사용.

---

### 4. `src/plugins/base/translator_plugin.py` — 배치 결과 길이 검증 없음
**문제:** `translate_batch`의 반환 목록이 입력보다 짧을 경우, `pipeline.py`의 `zip(regions, results)`에서 초과 영역이 조용히 누락되어 번역되지 않은 영역이 발생.

**현재 코드 (pipeline.py):**
```python
for region, result in zip(regions, results):  # 길이 불일치 시 데이터 손실
    if result.is_success:
        region.translated_text = result.translated_text
```

**수정 방향:** `translate_batch` 호출 후 결과 길이 검증 추가. 불일치 시 `TranslationError` 발생 또는 누락 영역에 오류 결과 채움.

---

## P1 — 중요 개선

### 5. `src/services/rendering_service.py` — 설정 조건식 오류
**문제:** `auto_font_size` 설정값을 읽는 조건식에 `if True`가 하드코딩되어 항상 `config.get()`이 실행됨. falsy 값(0, False, None)이 설정되어도 의도대로 반영되지 않을 수 있음.

**현재 코드:**
```python
self._auto_size = bool(config.get("rendering", "auto_font_size") if True else True)
```

**수정 방향:**
```python
self._auto_size = bool(config.get("rendering", "auto_font_size") ?? True)
# 또는
val = config.get("rendering", "auto_font_size")
self._auto_size = val if val is not None else True
```

---

### 6. `src/core/plugin_manager.py` — `assert` 사용
**문제:** Python 최적화 모드(`-O`, `-OO`)에서 `assert`문이 제거되어 타입 검사가 무력화됨.

**현재 코드:**
```python
def get_ocr_plugin(self, plugin_id: str) -> AbstractOCRPlugin:
    plugin = self.get_plugin("ocr", plugin_id)
    assert isinstance(plugin, AbstractOCRPlugin)
    return plugin
```

**수정 방향:** `assert` 대신 명시적 타입 검사 후 `PluginLoadError` 발생.
```python
if not isinstance(plugin, AbstractOCRPlugin):
    raise PluginLoadError(f"{plugin_id}는 AbstractOCRPlugin이 아님")
```

---

### 7. `src/gui/workers/pipeline_worker.py` — 취소 시 경쟁 조건
**문제:** `cancel()` 호출과 `run()`의 `finally: self._loop.close()` 사이에 경쟁 조건 발생 가능. 진행 중인 태스크가 강제 종료될 수 있음.

**현재 코드:**
```python
def cancel(self) -> None:
    if self._loop and self._loop.is_running():
        for task in asyncio.all_tasks(self._loop):
            task.cancel()

def run(self) -> None:
    ...
    finally:
        self._loop.close()  # 취소 중인 태스크와 경쟁
```

**수정 방향:** 루프 종료 전 `loop.run_until_complete(loop.shutdown_asyncgens())` 호출 및 대기 처리 추가.

---

### 8. `src/plugins/agents/claude_agent.py` — 에이전트 실패 시 침묵
**문제:** JSON 파싱 실패 등 에이전트 오류 발생 시 `warning` 로그만 남기고 원본을 그대로 반환. 에이전트가 무음으로 실패해도 사용자/파이프라인이 감지 불가.

**현재 코드:**
```python
except Exception as e:
    logger.warning("OCR 분석 실패, 원본 사용: %s", e)
return sorted(regions, key=lambda r: r.reading_order)
```

**수정 방향:** `job` 또는 `region`에 에이전트 실패 플래그 설정, GUI에서 표시. 또는 재시도 로직 추가.

---

## P2 — 개선 권장

### 9. `src/services/inpainting_service.py` — `is_rgb` 하드코딩
**문제:** `is_rgb = True`로 고정되어 BGR 입력 처리 불가. 조건 분기가 무의미.

**수정 방향:** 파라미터로 받거나, 파이프라인에서 항상 RGB로 통일하고 변수 제거.

---

### 10. `src/services/font_service.py` — 시스템 폰트 탐색 반복
**문제:** `get_font_path` 호출 시마다 `_font_cache` 미스 발생하면 `rglob`으로 전체 폰트 디렉토리를 탐색. 첫 렌더링 시 지연 발생.

**수정 방향:** 앱 시작 시 `_find_system_font`를 백그라운드에서 전체 인덱싱하여 딕셔너리로 캐싱.

---

### 11. 공유 ThreadPoolExecutor 부재
**문제:** `InpaintingService`와 `RenderingService`가 각각 독립적인 `ThreadPoolExecutor(max_workers=2)`를 보유. 동시 실행 시 스레드 낭비.

**수정 방향:** `src/utils/executor.py`에 공유 executor 싱글턴 정의 후 각 서비스에서 임포트.

---

### 12. 테스트 커버리지 부족
**문제:** 핵심 모듈 대부분에 테스트 없음.

**추가 필요한 테스트:**

| 모듈 | 테스트 파일 |
|------|------------|
| `Pipeline` | `tests/unit/test_pipeline.py` |
| `PluginManager` | `tests/unit/test_plugin_manager.py` |
| `ConfigManager` | `tests/unit/test_config_manager.py` |
| `InpaintingService` | `tests/unit/test_inpainting_service.py` |
| `RenderingService` | `tests/unit/test_rendering_service.py` |
| `PipelineWorker` | `tests/unit/test_pipeline_worker.py` |
| 번역 플러그인 전체 | `tests/unit/test_translators.py` |

---

## 수정 우선순위 요약

| 우선순위 | 항목 | 파일 | 영향 |
|:--------:|------|------|------|
| P0 | agent 변수 미초기화 | `pipeline.py` | 런타임 크래시 |
| P0 | 이미지 경로 파싱 버그 | `main_window.py` | 처리 시작 불가 |
| P0 | EasyOCR Reader 재생성 | `easyocr_plugin.py` | 심각한 성능 저하 |
| P0 | 배치 결과 길이 검증 없음 | `translator_plugin.py` + `pipeline.py` | 번역 누락 |
| P1 | 렌더링 설정 조건식 오류 | `rendering_service.py` | 설정 미반영 |
| P1 | assert 대신 명시적 검사 | `plugin_manager.py` | 타입 안전성 |
| P1 | 취소 경쟁 조건 | `pipeline_worker.py` | 취소 불안정 |
| P1 | 에이전트 실패 침묵 | `claude_agent.py` | 오류 미감지 |
| P2 | is_rgb 하드코딩 | `inpainting_service.py` | 코드 품질 |
| P2 | 폰트 탐색 반복 | `font_service.py` | 성능 |
| P2 | 공유 executor | `inpainting/rendering_service.py` | 리소스 |
| P2 | 테스트 커버리지 | `tests/` | 회귀 방지 |

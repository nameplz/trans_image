# 파이프라인 상세 설명

번역 파이프라인(`src/core/pipeline.py`)의 각 단계와 관련 컴포넌트를 설명한다.

---

## 전체 흐름

```
이미지 로드 (0%)
    → OCR (5~20%)
    → 번역 보조 에이전트: OCR 분석 (25~30%)    ← use_agent=True 시만
    → 언어 감지 (32~35%)
    → 번역 보조 에이전트: 컨텍스트 생성 (37~40%) ← use_agent=True 시만
    → 번역 (42~60%)
    → 번역 보조 에이전트: 번역 검증 (62~65%)    ← use_agent=True 시만
    → 인페인팅: 원문 제거 (67~80%)
    → 렌더링: 번역 텍스트 삽입 (82~95%)
    → 저장 (97~100%)
```

---

## 각 단계 상세

### 1. 이미지 로드

- `cv2.imread()` → RGB numpy 배열로 변환 (BGR→RGB)
- 실패 시 `ImageProcessingError` 발생

### 2. OCR (`AbstractOCRPlugin.detect_regions`)

- 플러그인: `easyocr` (기본) / `paddleocr` (CJK 특화)
- 반환: 바운딩박스 + 원문 텍스트 + 신뢰도를 담은 `list[TextRegion]`
- `OCRService.normalize()`: 중복 제거, 최소 신뢰도 필터링, bbox 정규화

### 3. 번역 보조 에이전트: OCR 분석 (선택)

- 조건: `job.use_agent=True` AND `config.processing.agent_analyze=True`
- `agent.analyze_ocr_results(regions)`: OCR 오류 교정, 읽기 순서(`reading_order`) 부여
- 실패해도 파이프라인 중단하지 않음 (원본 regions 사용)

### 4. 언어 감지

- `source_lang == "auto"` 일 때만 실행
- `LanguageService.detect(regions)`: 전체 텍스트를 합산 후 lingua-py로 감지
- 짧은 영역 단독 감지는 신뢰도 낮으므로 전체 페이지 텍스트 기준으로 감지

### 5. 번역 보조 에이전트: 컨텍스트 생성 (선택)

- `agent.generate_translation_context(regions, job)` → `{region_id: hint}` 딕셔너리
- 각 `TextRegion.context_hint`에 저장 → `translate_batch()` 호출 시 번역 플러그인으로 전달

### 6. 번역 (`AbstractTranslatorPlugin.translate_batch`)

- `translator.translate_batch(regions, source_lang, target_lang)`
- 성공 시 `region.translated_text` 저장, 실패 시 `region.needs_review = True`
- `job.translated_regions` / `job.failed_regions` 카운트 업데이트

### 7. 번역 보조 에이전트: 번역 검증 (선택)

- 조건: `job.use_agent=True` AND `config.processing.agent_validate=True`
- `agent.validate_translations(original_regions, translated_regions)`
- 문제 있는 영역에 `needs_review = True` 플래그 설정

### 8. 인페인팅 (`InpaintingService.remove_text`)

- 각 bbox를 `cv2.dilate()`로 팽창시켜 마스크 생성 (텍스트 스트로크 완전 제거)
- 기본: `cv2.inpaint()` NS 알고리즘
- 고품질 옵션: LaMa 모델 (설정 필요)
- 반환: 원문 텍스트가 제거된 `inpainted_image` numpy 배열

### 9. 렌더링 (`RenderingService.render`)

- `inpainted_image` 위에 번역 텍스트 삽입
- `FontService`로 bbox 크기에 맞게 폰트 크기 자동 조절
- CJK 텍스트: 번들 `assets/fonts/NotoSansCJK-*.ttf` 사용
- `reading_order` 순서대로 렌더링

### 10. 저장

- `job.output_path` 지정 시에만 실행
- JPEG: quality=95, 나머지: 기본 파라미터

---

## JobStatus Enum

```
QUEUED → OCR_RUNNING → AGENT_ANALYZING → DETECTING_LANGUAGE
       → GENERATING_CONTEXT → TRANSLATING → AGENT_VALIDATING
       → INPAINTING → RENDERING → COMPLETE
       (오류 시) → FAILED
       (취소 시) → CANCELLED
```

---

## 배치 처리 (대화형 에이전트에서 호출)

`src/chat/batch_processor.py`가 디렉토리의 이미지 파일마다 `ProcessingJob`을 생성하고 `Pipeline.run()`을 순차 호출한다.

```python
# batch_processor.py 처리 흐름
for image_path in image_files:
    job = ProcessingJob(
        input_path=image_path,
        output_path=output_dir / image_path.name,
        target_lang=params.target_lang,
        translator_plugin_id=params.translator_id,
        agent_plugin_id=params.agent_id,
        use_agent=params.use_agent,
    )
    await pipeline.run(job, progress_cb=on_progress)
```

각 이미지 처리 결과는 즉시 출력 디렉토리에 저장되며, 실패 이미지는 건너뛰고 계속 진행한다.

---

## 진행 상태 콜백

`Pipeline.run(job, progress_cb)`의 콜백 시그니처:

```python
ProgressCallback = Callable[[ProcessingJob, str], None]
# job.progress: 0.0~1.0 (현재 진행률)
# job.status: 현재 JobStatus
# message: 사람이 읽을 수 있는 상태 메시지
```

GUI에서는 `PipelineWorker`(QThread)가 Signal로 메인 스레드에 전달하고,
대화형 에이전트에서는 채팅 패널에 실시간 스트리밍으로 표시한다.

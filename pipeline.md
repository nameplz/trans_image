# 파이프라인 흐름

> AGENTS.md에서 참조됩니다.

## 전체 흐름

```
이미지 로드
    → OCR 플러그인 (바운딩박스 + 텍스트)
    → 에이전트.analyze_ocr_results() (오류 수정, 읽기 순서)
    → 언어 감지 서비스 (lingua-py)
    → 에이전트.generate_translation_context() (컨텍스트 힌트)
    → 번역 플러그인.translate_batch()
    → 에이전트.validate_translations() (일관성 검증)
    → 인페인팅 서비스 (원문 제거, OpenCV NS / LaMa)
    → 렌더링 서비스 (번역 텍스트 삽입, 폰트 자동 조절)
    → GUI 미리보기 → 내보내기
```

## JobStatus 전환

```
QUEUED → OCR_RUNNING → TRANSLATING → INPAINTING → RENDERING → COMPLETE
```

# 핵심 데이터 구조

> AGENTS.md에서 참조됩니다.

## TextRegion (`src/models/text_region.py`)

- `bbox`: BoundingBox (x, y, width, height, rotation)
- `raw_text`: OCR 인식 원문
- `detected_language`: lingua-py 감지 결과
- `confidence`: OCR 신뢰도 (0~1)
- `style`: TextStyle (폰트, 크기, 색상, 방향)
- `translated_text`: 번역 결과
- `context_hint`: 에이전트가 생성한 번역 컨텍스트
- `reading_order`: 올바른 읽기 순서 (만화 등)

## ProcessingJob (`src/models/processing_job.py`)

- `status`: JobStatus Enum (QUEUED → OCR_RUNNING → TRANSLATING → INPAINTING → RENDERING → COMPLETE)
- `source_lang`: 자동 감지 시 "auto"
- `target_lang`: 목표 언어 코드 (예: "ko", "en", "ja")
- `regions`: list[TextRegion]
- `original_image`, `inpainted_image`, `final_image`: numpy 배열

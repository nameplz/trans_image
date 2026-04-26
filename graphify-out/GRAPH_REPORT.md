# Graph Report - trans_image  (2026-04-26)

## Corpus Check
- 126 files · ~45,026 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1782 nodes · 5636 edges · 28 communities detected
- Extraction: 37% EXTRACTED · 63% INFERRED · 0% AMBIGUOUS · INFERRED: 3565 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]

## God Nodes (most connected - your core abstractions)
1. `TextRegion` - 326 edges
2. `BoundingBox` - 262 edges
3. `ProcessingJob` - 221 edges
4. `ConfigManager` - 117 edges
5. `TranslationResult` - 96 edges
6. `MainWindow` - 96 edges
7. `PluginManager` - 95 edges
8. `BatchProcessor` - 92 edges
9. `Pipeline` - 91 edges
10. `ParsedMessage` - 89 edges

## Surprising Connections (you probably didn't know these)
- `sample_job()` --calls--> `ProcessingJob`  [INFERRED]
  tests/unit/test_pipeline_worker.py → src/models/processing_job.py
- `make_translation_result()` --calls--> `TranslationResult`  [INFERRED]
  tests/unit/test_pipeline.py → src/models/translation_result.py
- `test_translation_result_creation()` --calls--> `TranslationResult`  [INFERRED]
  tests/integration/test_pipeline_mock.py → src/models/translation_result.py
- `QThread and Signal Responsiveness Pattern` --semantically_similar_to--> `No Blocking I/O in GUI Thread`  [INFERRED] [semantically similar]
  AGENTS.md → conventions.md
- `Agent Is Not Translator Principle` --semantically_similar_to--> `Conversational Agent vs Assistant Agent Separation`  [INFERRED] [semantically similar]
  AGENTS.md → docs/chat_interface.md

## Hyperedges (group relationships)
- **Plugin System Contracts** — agents_plugin_architecture, plugin_dev_plugin_base, plugin_dev_ocr_plugin, plugin_dev_translator_plugin, plugin_dev_agent_plugin, plugins_plugin_catalog [EXTRACTED 1.00]
- **Core Translation Flow** — docs_pipeline_detailed_flow, data_models_processing_job, data_models_text_region, plugin_dev_ocr_plugin, plugin_dev_translator_plugin, plugin_dev_agent_plugin, plugin_dev_translation_result [EXTRACTED 1.00]
- **Chat Batch Orchestration Pattern** — docs_chat_chat_interface, docs_chat_path_mentions, docs_chat_conversation_session, docs_pipeline_batch_processing, data_models_processing_job [EXTRACTED 1.00]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.02
Nodes (94): BatchProcessor, BatchWorker, 배치 처리 QThread 워커 — QThread↔asyncio 브릿지., 채팅 명령으로 시작된 배치 번역 작업을 비동기로 실행.      PipelineWorker와 동일한 QThread+asyncio 패턴 사용., QThread 진입점 — 새 asyncio 루프에서 배치 실행., QThread 진입점 — 새 asyncio 루프에서 배치 실행., _build_client(), ChatAgent (+86 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (76): ComparisonView, ExportDialog, JobQueuePanel, _on_progress(), QMainWindow 루트 — 메인 윈도우., 진행 중인 job이 없을 때만 ProgressPanel을 리셋한다., 오버레이 아이템 클릭 시 RegionEditorPanel에 영역 로드., 단일 영역 재처리 요청 처리 — RegionReprocessWorker 시작. (+68 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (74): ChatController, JobController, RegionEditState, MainWindow, _on_batch_completed(), _on_chat_message(), _on_job_failed(), _on_region_selected() (+66 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (76): AbstractOCRPlugin, iou(), is_inside(), merge_boxes(), 여러 박스를 감싸는 최소 경계 박스 반환., inner가 outer 안에 threshold 이상 포함되는지 확인., 박스 목록을 읽기 순서로 정렬한 인덱스 반환.      Args:         boxes: 정렬할 박스 목록         right_to_l, 두 바운딩박스의 IoU (Intersection over Union) 계산. (+68 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (62): AbstractTranslatorPlugin, DeepLTranslatorPlugin, PluginConfigError, RateLimitError, 플러그인 설정 오류 (API 키 누락 등)., 번역 API 호출 실패 (HTTP 오류 등)., API 속도 제한 초과 (HTTP 429)., TranslationAPIError (+54 more)

### Community 5 - "Community 5"
Cohesion: 0.04
Nodes (77): Enum, ImageProcessingError, InpaintingError, RenderingError, ExportOptions, ImageFormat, 저장 직전에만 적용되는 이미지 내보내기 옵션., ResizeMode (+69 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (86): BatchResult, 디렉토리 이미지 배치 처리 오케스트레이터., 작업 목록을 순차 실행. 개별 실패 시 나머지 계속 진행.          Args:             jobs: ProcessingJob, 디렉토리 스캔 → ProcessingJob 생성 → 파이프라인 순차 실행., 입력 디렉토리 옆에 `{name}_translated` 디렉토리 경로 반환., 디렉토리에서 지원하는 이미지 파일 목록을 알파벳 순으로 반환.          현재 디렉토리(depth=1)의 파일만 스캔합니다. 하위 폴더는, 이미지 목록에서 ProcessingJob 목록 생성.          출력 경로: parsed.output_dir 또는 default_outpu, PipelineError (+78 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (65): create_app(), QApplication 래퍼 — 앱 초기화., QApplication 및 MainWindow 생성., run_gui(), ConfigManager, plugin_type: 'ocr' | 'translators' | 'agents, plugin_type: 'ocr' | 'translators' | 'agents, 앱 설정 및 플러그인 레지스트리 로드·조회. (+57 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (38): AbstractAgentPlugin, analyze_ocr_results(), generate_translation_context(), AbstractAgentPlugin ABC., stream_analysis(), validate_translations(), ClaudeAgentPlugin, Claude (Anthropic) 에이전트 플러그인. (+30 more)

### Community 9 - "Community 9"
Cohesion: 0.05
Nodes (54): ABC, AbstractAgentPlugin, AI 에이전트 플러그인 추상 기반 클래스.      중요: 에이전트는 번역 API를 직접 호출하지 않는다.     OCR 결과 분석, 번역 컨텍, OCR 결과를 분석하여 품질 개선.          수행 작업:         - OCR 오류 텍스트 교정         - 읽기 순서 정렬 (, 각 TextRegion에 대한 번역 컨텍스트 힌트 생성.          Args:             regions: 언어 감지 완료된 Te, 번역 결과 일관성·완전성 검증.          검증 항목:         - 번역 누락 영역 탐지         - 언어 일관성 확인, GUI 실시간 피드백을 위한 스트리밍 분석.          Args:             prompt: 에이전트에게 전달할 프롬프트, EasyOCRPlugin (+46 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (24): 원본/번역 비교 뷰 (슬라이더 방식)., ImageViewer, 줌/패닝 지원 QGraphicsView 이미지 뷰어., 드래그 패닝, 휠 줌 지원 이미지 뷰어., numpy RGB 배열 → 뷰어에 표시., _on_job_done(), _on_preview_ready(), _on_region_reprocess_done() (+16 more)

### Community 11 - "Community 11"
Cohesion: 0.06
Nodes (28): _ChatInput, ChatPanel, _MessageBubble, 채팅 패널 위젯 — @경로 멘션으로 배치 번역을 지시하는 대화형 UI., 채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실, 배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화., 스트리밍 메시지를 시작한다. 기존 미완료 스트림은 즉시 마무리한다., 현재 스트리밍 메시지에 chunk를 추가한다. (+20 more)

### Community 12 - "Community 12"
Cohesion: 0.14
Nodes (8): QApplication 및 MainWindow 생성., _on_job_selected(), Session, test_session_job_management(), make_job(), TestSessionCRUD, TestSessionNextPending, TestSessionRunningCount

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (33): Agent Is Not Translator Principle, QThread and Signal Responsiveness Pattern, Plugin-Based Architecture, Project Overview, Phase 5 GUI Integration Completion, Legacy CLAUDE Guidance Note, Async Plugin Method Convention, No Blocking I/O in GUI Thread (+25 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (17): crop_region(), cv2_to_pil(), pil_to_cv2(), PIL Image (RGB) → BGR numpy 배열., 긴 쪽이 max_dim을 넘지 않도록 리사이즈.      Returns:         (resized_image, scale_factor), BGR numpy 배열 → PIL Image (RGB)., resize_keep_aspect(), 300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨. (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.16
Nodes (7): get_logger(), LogContext, 이름으로 로거 반환. 최초 요청 시 생성., 앱 시작 시 한 번 호출하여 로깅 설정., with 문으로 사용하는 구조화 로그 컨텍스트., setup_logging(), TestLoggerUtils

### Community 16 - "Community 16"
Cohesion: 0.67
Nodes (2): download_font(), main()

### Community 17 - "Community 17"
Cohesion: 1.0
Nodes (2): API Key Management Rules, Environment Variable API Key Setup

### Community 29 - "Community 29"
Cohesion: 1.0
Nodes (1): 플러그인 초기화 (모델 로드, API 클라이언트 생성 등).

### Community 30 - "Community 30"
Cohesion: 1.0
Nodes (1): 설정 유효성 검사.         반환값: 오류 메시지 목록. 빈 목록이면 유효.

### Community 31 - "Community 31"
Cohesion: 1.0
Nodes (1): 플러그인 기능 정보 반환.         예: {'languages': ['en', 'ko'], 'batch_size': 50}

### Community 41 - "Community 41"
Cohesion: 1.0
Nodes (1): 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')

### Community 42 - "Community 42"
Cohesion: 1.0
Nodes (1): 파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)

### Community 43 - "Community 43"
Cohesion: 1.0
Nodes (1): 파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): @를 입력하면 경로 자동완성을 표시하는 입력창.

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): 채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): 배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화.

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): Structured Logger Convention

## Knowledge Gaps
- **85 isolated node(s):** `300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨.`, `200x300 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨.`, `max_dim 이하 이미지는 scale=1.0 반환, 원본 크기 유지.`, `정확히 max_dim 크기 이미지는 그대로 반환.`, `이미지 크기 초과 좌표는 이미지 경계로 클리핑.` (+80 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 16`** (4 nodes): `download_font()`, `main()`, `_progress_hook()`, `download_fonts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 17`** (2 nodes): `API Key Management Rules`, `Environment Variable API Key Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 29`** (1 nodes): `플러그인 초기화 (모델 로드, API 클라이언트 생성 등).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 30`** (1 nodes): `설정 유효성 검사.         반환값: 오류 메시지 목록. 빈 목록이면 유효.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 31`** (1 nodes): `플러그인 기능 정보 반환.         예: {'languages': ['en', 'ko'], 'batch_size': 50}`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 41`** (1 nodes): `점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 42`** (1 nodes): `파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 43`** (1 nodes): `파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `@를 입력하면 경로 자동완성을 표시하는 입력창.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `Structured Logger Convention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TextRegion` connect `Community 4` to `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 8`, `Community 9`?**
  _High betweenness centrality (0.242) - this node is a cross-community bridge._
- **Why does `ProcessingJob` connect `Community 6` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 7`, `Community 8`, `Community 9`, `Community 12`?**
  _High betweenness centrality (0.196) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Community 2` to `Community 0`, `Community 1`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 12`?**
  _High betweenness centrality (0.133) - this node is a cross-community bridge._
- **Are the 325 inferred relationships involving `TextRegion` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`TextRegion` has 325 INFERRED edges - model-reasoned connections that need verification._
- **Are the 258 inferred relationships involving `BoundingBox` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`BoundingBox` has 258 INFERRED edges - model-reasoned connections that need verification._
- **Are the 215 inferred relationships involving `ProcessingJob` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`ProcessingJob` has 215 INFERRED edges - model-reasoned connections that need verification._
- **Are the 104 inferred relationships involving `ConfigManager` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`ConfigManager` has 104 INFERRED edges - model-reasoned connections that need verification._
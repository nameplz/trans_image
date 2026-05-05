# Graph Report - trans_image  (2026-05-05)

## Corpus Check
- 128 files · ~102,258 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2001 nodes · 6715 edges · 35 communities detected
- Extraction: 34% EXTRACTED · 66% INFERRED · 0% AMBIGUOUS · INFERRED: 4450 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]

## God Nodes (most connected - your core abstractions)
1. `TextRegion` - 381 edges
2. `BoundingBox` - 317 edges
3. `ProcessingJob` - 247 edges
4. `ConfigManager` - 151 edges
5. `TranslationResult` - 142 edges
6. `MainWindow` - 134 edges
7. `PluginManager` - 110 edges
8. `ParsedMessage` - 107 edges
9. `Pipeline` - 102 edges
10. `BatchProcessor` - 101 edges

## Surprising Connections (you probably didn't know these)
- `sample_job()` --calls--> `ProcessingJob`  [INFERRED]
  tests/unit/test_pipeline_worker.py → src/models/processing_job.py
- `app.py 및 __main__.py 진입점 테스트.` --uses--> `ProcessingJob`  [INFERRED]
  tests/unit/test_app_entrypoints.py → src/models/processing_job.py
- `make_translation_result()` --calls--> `TranslationResult`  [INFERRED]
  tests/unit/test_pipeline.py → src/models/translation_result.py
- `test_translation_result_creation()` --calls--> `TranslationResult`  [INFERRED]
  tests/integration/test_pipeline_mock.py → src/models/translation_result.py
- `QThread and Signal Responsiveness Pattern` --semantically_similar_to--> `No Blocking I/O in GUI Thread`  [INFERRED] [semantically similar]
  AGENTS.md → conventions.md

## Hyperedges (group relationships)
- **Plugin System Contracts** — agents_plugin_architecture, plugin_dev_plugin_base, plugin_dev_ocr_plugin, plugin_dev_translator_plugin, plugin_dev_agent_plugin, plugins_plugin_catalog [EXTRACTED 1.00]
- **Core Translation Flow** — docs_pipeline_detailed_flow, data_models_processing_job, data_models_text_region, plugin_dev_ocr_plugin, plugin_dev_translator_plugin, plugin_dev_agent_plugin, plugin_dev_translation_result [EXTRACTED 1.00]
- **Chat Batch Orchestration Pattern** — docs_chat_chat_interface, docs_chat_path_mentions, docs_chat_conversation_session, docs_pipeline_batch_processing, data_models_processing_job [EXTRACTED 1.00]

## Communities

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (149): AbstractTranslatorPlugin, mock_config(), 공유 테스트 픽스처 — 전체 테스트 스위트용., ConfigManager mock — get() 호출에 기본값 반환., 기본 ProcessingJob 샘플 (실제 파일 경로 포함)., sample_job(), sample_regions(), sample_text_region() (+141 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (136): generate_translation_context(), validate_translations(), 작업 목록을 순차 실행. 개별 실패 시 나머지 계속 진행.          Args:             jobs: ProcessingJob, 작업 목록을 순차 실행. 개별 실패 시 나머지 계속 진행.          Args:             jobs: ProcessingJob, 입력 디렉토리 옆에 `{name}_translated` 디렉토리 경로 반환., 디렉토리에서 지원하는 이미지 파일 목록을 알파벳 순으로 반환.          현재 디렉토리(depth=1)의 파일만 스캔합니다. 하위 폴더는, 이미지 목록에서 ProcessingJob 목록 생성.          출력 경로: parsed.output_dir 또는 default_outpu, Enum (+128 more)

### Community 2 - "Community 2"
Cohesion: 0.02
Nodes (100): BatchProcessor, BatchResult, 디렉토리 이미지 배치 처리 오케스트레이터., 디렉토리 스캔 → ProcessingJob 생성 → 파이프라인 순차 실행., 배치 처리 QThread 워커 — QThread↔asyncio 브릿지., 채팅 명령으로 시작된 배치 번역 작업을 비동기로 실행.      PipelineWorker와 동일한 QThread+asyncio 패턴 사용., QThread 진입점 — 새 asyncio 루프에서 배치 실행., QThread 진입점 — 새 asyncio 루프에서 배치 실행. (+92 more)

### Community 3 - "Community 3"
Cohesion: 0.02
Nodes (107): plugin_type: 'ocr' | 'translators' | 'agents, 환경변수 우선, 없으면 config.yaml의 api_keys 섹션 참조.          YAML 값이 str이 아닌 경우(예: 잘못된 YAM, 환경변수 우선, 없으면 config.yaml의 api_keys 섹션 참조.          YAML 값이 str이 아닌 경우(예: 잘못된 YAM, plugin_type: 'ocr' | 'translators' | 'agents, plugin_type: 'ocr' | 'translators' | 'agents, plugin_type: 'ocr' | 'translators' | 'agents, 앱 설정 및 플러그인 레지스트리 로드·조회., 앱 설정 및 플러그인 레지스트리 로드·조회. (+99 more)

### Community 4 - "Community 4"
Cohesion: 0.02
Nodes (85): BatchWorker, _ChatInput, ChatPanel, _MessageBubble, 채팅 패널 위젯 — @경로 멘션으로 배치 번역을 지시하는 대화형 UI., 채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실, 배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화., 스트리밍 메시지를 시작한다. 기존 미완료 스트림은 즉시 마무리한다. (+77 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (102): ABC, AbstractOCRPlugin, AbstractAgentPlugin, AbstractAgentPlugin ABC., AI 에이전트 플러그인 추상 기반 클래스.      중요: 에이전트는 번역 API를 직접 호출하지 않는다.     OCR 결과 분석, 번역 컨텍, OCR 결과를 분석하여 품질 개선.          수행 작업:         - OCR 오류 텍스트 교정         - 읽기 순서 정렬 (, 각 TextRegion에 대한 번역 컨텍스트 힌트 생성.          Args:             regions: 언어 감지 완료된 Te, 번역 결과 일관성·완전성 검증.          검증 항목:         - 번역 누락 영역 탐지         - 언어 일관성 확인 (+94 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (62): create_app(), main(), QApplication 래퍼 — 앱 초기화., QApplication 및 MainWindow 생성., Public GUI entrypoint used by the launcher script., run_gui(), ConfigManager, 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang') (+54 more)

### Community 7 - "Community 7"
Cohesion: 0.04
Nodes (46): AbstractAgentPlugin, analyze_ocr_results(), ClaudeAgentPlugin, Claude (Anthropic) 에이전트 플러그인., AgentAPIError, GeminiAgentPlugin, Google Gemini 에이전트 플러그인., OllamaAgentPlugin (+38 more)

### Community 8 - "Community 8"
Cohesion: 0.05
Nodes (24): 원본/번역 비교 뷰 (슬라이더 방식)., ImageViewer, 줌/패닝 지원 QGraphicsView 이미지 뷰어., 드래그 패닝, 휠 줌 지원 이미지 뷰어., numpy RGB 배열 → 뷰어에 표시., _on_job_done(), _on_preview_ready(), _on_region_reprocess_done() (+16 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (11): JobController, _on_translation_edited(), _on_translation_preview_requested(), 처리 시작 — 상태를 OCR_RUNNING 으로 전환., QObject, make_controller(), TestChatController, make_controller() (+3 more)

### Community 10 - "Community 10"
Cohesion: 0.09
Nodes (25): QGraphicsRectItem, 바운딩박스 오버레이 QGraphicsItem., 단일 TextRegion 바운딩박스를 표시하는 QGraphicsItem.      ScrollHandDrag 충돌 방지를 위해 mousePres, 클릭 시 호출할 콜백 등록. callback(region_id: str)., 좌클릭 시 콜백으로 region_id 전달. ScrollHandDrag 패닝 차단., 씬의 모든 RegionOverlayItem 관리.      QObject를 상속하여 region_selected 시그널을 제공한다.     아이, RegionOverlayItem, RegionOverlayManager (+17 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (14): QApplication 및 MainWindow 생성., QApplication 및 MainWindow 생성., Public GUI entrypoint used by the launcher script., JobQueuePanel, _on_job_selected(), _on_progress(), Session, JobQueuePanel 단위 테스트. (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.11
Nodes (33): Agent Is Not Translator Principle, QThread and Signal Responsiveness Pattern, Plugin-Based Architecture, Project Overview, Phase 5 GUI Integration Completion, Legacy CLAUDE Guidance Note, Async Plugin Method Convention, No Blocking I/O in GUI Thread (+25 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (16): make_font_service(), make_service(), RenderingService 단위 테스트., _fit_font_size 결과 → min_font 이상, max_font 이하., 아주 작은 영역에서는 최소 폰트 크기 반환., regions=[] → 입력 이미지와 shape 동일., has_translation=False region → 렌더링 건너뜀 (픽셀 변화 없음)., TextStyle(background_color=None) → 배경 사각형 그리지 않음. (+8 more)

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (17): crop_region(), cv2_to_pil(), pil_to_cv2(), PIL Image (RGB) → BGR numpy 배열., 긴 쪽이 max_dim을 넘지 않도록 리사이즈.      Returns:         (resized_image, scale_factor), BGR numpy 배열 → PIL Image (RGB)., resize_keep_aspect(), 300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨. (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.11
Nodes (13): iou(), is_inside(), merge_boxes(), 여러 박스를 감싸는 최소 경계 박스 반환., inner가 outer 안에 threshold 이상 포함되는지 확인., 박스 목록을 읽기 순서로 정렬한 인덱스 반환.      Args:         boxes: 정렬할 박스 목록         right_to_l, 두 바운딩박스의 IoU (Intersection over Union) 계산., scale_bbox() (+5 more)

### Community 16 - "Community 16"
Cohesion: 0.19
Nodes (4): ExportDialog, QDialog, make_config(), TestExportDialog

### Community 17 - "Community 17"
Cohesion: 0.19
Nodes (5): get_logger(), LogContext, 이름으로 로거 반환. 최초 요청 시 생성., with 문으로 사용하는 구조화 로그 컨텍스트., TestLoggerUtils

### Community 18 - "Community 18"
Cohesion: 0.25
Nodes (9): _get_project_root(), load_project_env(), Project-level `.env` loading helpers., Load environment variables from the project root `.env` file.      Existing proc, Project `.env` loader unit tests., test_load_project_env_does_not_override_existing_environment(), test_load_project_env_logs_warning_on_loader_failure(), test_load_project_env_populates_missing_environment_value() (+1 more)

### Community 19 - "Community 19"
Cohesion: 0.33
Nodes (4): TestTheme, apply_theme(), load_theme_stylesheet(), normalize_theme_name()

### Community 20 - "Community 20"
Cohesion: 0.67
Nodes (2): download_font(), main()

### Community 21 - "Community 21"
Cohesion: 1.0
Nodes (2): API Key Management Rules, Environment Variable API Key Setup

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): 플러그인 초기화 (모델 로드, API 클라이언트 생성 등).

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): 설정 유효성 검사.         반환값: 오류 메시지 목록. 빈 목록이면 유효.

### Community 35 - "Community 35"
Cohesion: 1.0
Nodes (1): 플러그인 기능 정보 반환.         예: {'languages': ['en', 'ko'], 'batch_size': 50}

### Community 45 - "Community 45"
Cohesion: 1.0
Nodes (1): 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')

### Community 46 - "Community 46"
Cohesion: 1.0
Nodes (1): 새 메시지를 추가한 새 세션 반환 (불변 패턴).

### Community 47 - "Community 47"
Cohesion: 1.0
Nodes (1): 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')

### Community 48 - "Community 48"
Cohesion: 1.0
Nodes (1): 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')

### Community 49 - "Community 49"
Cohesion: 1.0
Nodes (1): 파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)

### Community 50 - "Community 50"
Cohesion: 1.0
Nodes (1): 파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)

### Community 51 - "Community 51"
Cohesion: 1.0
Nodes (1): @를 입력하면 경로 자동완성을 표시하는 입력창.

### Community 52 - "Community 52"
Cohesion: 1.0
Nodes (1): 채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실

### Community 53 - "Community 53"
Cohesion: 1.0
Nodes (1): 배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화.

### Community 54 - "Community 54"
Cohesion: 1.0
Nodes (1): Structured Logger Convention

## Knowledge Gaps
- **103 isolated node(s):** `Project `.env` loader unit tests.`, `300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨.`, `200x300 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨.`, `max_dim 이하 이미지는 scale=1.0 반환, 원본 크기 유지.`, `정확히 max_dim 크기 이미지는 그대로 반환.` (+98 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 20`** (4 nodes): `download_font()`, `main()`, `_progress_hook()`, `download_fonts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 21`** (2 nodes): `API Key Management Rules`, `Environment Variable API Key Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `플러그인 초기화 (모델 로드, API 클라이언트 생성 등).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `설정 유효성 검사.         반환값: 오류 메시지 목록. 빈 목록이면 유효.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 35`** (1 nodes): `플러그인 기능 정보 반환.         예: {'languages': ['en', 'ko'], 'batch_size': 50}`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 45`** (1 nodes): `점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 46`** (1 nodes): `새 메시지를 추가한 새 세션 반환 (불변 패턴).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 47`** (1 nodes): `점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 48`** (1 nodes): `점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 49`** (1 nodes): `파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 50`** (1 nodes): `파이프라인 실행.          Args:             job: 처리할 작업 (input_path, target_lang 등 설정됨)`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 51`** (1 nodes): `@를 입력하면 경로 자동완성을 표시하는 입력창.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 52`** (1 nodes): `채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 53`** (1 nodes): `배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 54`** (1 nodes): `Structured Logger Convention`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `TextRegion` connect `Community 0` to `Community 1`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 13`?**
  _High betweenness centrality (0.214) - this node is a cross-community bridge._
- **Why does `ProcessingJob` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 5`, `Community 6`, `Community 7`, `Community 9`, `Community 11`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 16`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Are the 380 inferred relationships involving `TextRegion` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`TextRegion` has 380 INFERRED edges - model-reasoned connections that need verification._
- **Are the 313 inferred relationships involving `BoundingBox` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`BoundingBox` has 313 INFERRED edges - model-reasoned connections that need verification._
- **Are the 241 inferred relationships involving `ProcessingJob` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`ProcessingJob` has 241 INFERRED edges - model-reasoned connections that need verification._
- **Are the 133 inferred relationships involving `ConfigManager` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`ConfigManager` has 133 INFERRED edges - model-reasoned connections that need verification._
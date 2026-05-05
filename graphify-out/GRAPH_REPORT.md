# Graph Report - trans_image  (2026-05-05)

## Corpus Check
- 128 files · ~102,810 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2043 nodes · 6888 edges · 35 communities detected
- Extraction: 33% EXTRACTED · 67% INFERRED · 0% AMBIGUOUS · INFERRED: 4596 edges (avg confidence: 0.59)
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
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 44|Community 44]]
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
1. `TextRegion` - 391 edges
2. `BoundingBox` - 327 edges
3. `ProcessingJob` - 247 edges
4. `ConfigManager` - 169 edges
5. `TranslationResult` - 142 edges
6. `MainWindow` - 134 edges
7. `PluginManager` - 122 edges
8. `ParsedMessage` - 107 edges
9. `Pipeline` - 102 edges
10. `BatchProcessor` - 101 edges

## Surprising Connections (you probably didn't know these)
- `app.py 및 __main__.py 진입점 테스트.` --uses--> `ProcessingJob`  [INFERRED]
  tests/unit/test_app_entrypoints.py → src/models/processing_job.py
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
Cohesion: 0.03
Nodes (159): AbstractTranslatorPlugin, iou(), is_inside(), merge_boxes(), 여러 박스를 감싸는 최소 경계 박스 반환., inner가 outer 안에 threshold 이상 포함되는지 확인., 박스 목록을 읽기 순서로 정렬한 인덱스 반환.      Args:         boxes: 정렬할 박스 목록         right_to_l, 두 바운딩박스의 IoU (Intersection over Union) 계산. (+151 more)

### Community 1 - "Community 1"
Cohesion: 0.02
Nodes (99): BatchWorker, 배치 처리 QThread 워커 — QThread↔asyncio 브릿지., 채팅 명령으로 시작된 배치 번역 작업을 비동기로 실행.      PipelineWorker와 동일한 QThread+asyncio 패턴 사용., QThread 진입점 — 새 asyncio 루프에서 배치 실행., _build_client(), ChatAgent, ComparisonView, ChatMessage (+91 more)

### Community 2 - "Community 2"
Cohesion: 0.03
Nodes (99): analyze_ocr_results(), generate_translation_context(), AbstractAgentPlugin ABC., validate_translations(), Enum, Exception, ImageProcessingError, InpaintingError (+91 more)

### Community 3 - "Community 3"
Cohesion: 0.03
Nodes (88): create_app(), main(), QApplication 래퍼 — 앱 초기화., QApplication 및 MainWindow 생성., Public GUI entrypoint used by the launcher script., run_gui(), ConfigManager, 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang') (+80 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (107): BatchResult, 디렉토리 이미지 배치 처리 오케스트레이터., 작업 목록을 순차 실행. 개별 실패 시 나머지 계속 진행.          Args:             jobs: ProcessingJob, 작업 목록을 순차 실행. 개별 실패 시 나머지 계속 진행.          Args:             jobs: ProcessingJob, 디렉토리 스캔 → ProcessingJob 생성 → 파이프라인 순차 실행., 입력 디렉토리 옆에 `{name}_translated` 디렉토리 경로 반환., 디렉토리에서 지원하는 이미지 파일 목록을 알파벳 순으로 반환.          현재 디렉토리(depth=1)의 파일만 스캔합니다. 하위 폴더는, 이미지 목록에서 ProcessingJob 목록 생성.          출력 경로: parsed.output_dir 또는 default_outpu (+99 more)

### Community 5 - "Community 5"
Cohesion: 0.03
Nodes (84): QApplication 및 MainWindow 생성., QApplication 및 MainWindow 생성., Public GUI entrypoint used by the launcher script., plugin_type: 'ocr' | 'translators' | 'agents, 환경변수 우선, 없으면 config.yaml의 api_keys 섹션 참조.          YAML 값이 str이 아닌 경우(예: 잘못된 YAM, 환경변수 우선, 없으면 config.yaml의 api_keys 섹션 참조.          YAML 값이 str이 아닌 경우(예: 잘못된 YAM, plugin_type: 'ocr' | 'translators' | 'agents, plugin_type: 'ocr' | 'translators' | 'agents (+76 more)

### Community 6 - "Community 6"
Cohesion: 0.04
Nodes (80): ABC, AbstractOCRPlugin, AbstractAgentPlugin, AI 에이전트 플러그인 추상 기반 클래스.      중요: 에이전트는 번역 API를 직접 호출하지 않는다.     OCR 결과 분석, 번역 컨텍, OCR 결과를 분석하여 품질 개선.          수행 작업:         - OCR 오류 텍스트 교정         - 읽기 순서 정렬 (, 각 TextRegion에 대한 번역 컨텍스트 힌트 생성.          Args:             regions: 언어 감지 완료된 Te, 번역 결과 일관성·완전성 검증.          검증 항목:         - 번역 누락 영역 탐지         - 언어 일관성 확인, GUI 실시간 피드백을 위한 스트리밍 분석.          Args:             prompt: 에이전트에게 전달할 프롬프트 (+72 more)

### Community 7 - "Community 7"
Cohesion: 0.03
Nodes (55): BatchProcessor, MessageParser, _normalize_path(), 경로 토큰을 Path로 변환. 상대 경로는 cwd 기준으로 결합.      상대 경로가 cwd 밖으로 탈출(경로 순회)하는 경우 ValueErr, 채팅 메시지에서 @경로 멘션과 파라미터를 파싱하는 상태 없는 파서., 메시지를 파싱하여 ParsedMessage 반환.          Args:             text: 사용자 입력 메시지, 처리 완료 — 상태를 COMPLETE 로 전환., make_parsed() (+47 more)

### Community 8 - "Community 8"
Cohesion: 0.04
Nodes (54): AbstractAgentPlugin, stream_analysis(), ClaudeAgentPlugin, Claude (Anthropic) 에이전트 플러그인., AgentAPIError, AgentError, PluginError, trans_image 커스텀 예외 계층. (+46 more)

### Community 9 - "Community 9"
Cohesion: 0.04
Nodes (30): _ChatInput, ChatPanel, _MessageBubble, 채팅 패널 위젯 — @경로 멘션으로 배치 번역을 지시하는 대화형 UI., 채팅 기반 배치 번역 인터페이스 패널.      사용자가 @경로 멘션으로 디렉토리를 지정하면 BatchWorker를 통해     파이프라인을 실, 배치 실행 상태에 따라 입력창·중단 버튼 활성화/비활성화., 스트리밍 메시지를 시작한다. 기존 미완료 스트림은 즉시 마무리한다., 현재 스트리밍 메시지에 chunk를 추가한다. (+22 more)

### Community 10 - "Community 10"
Cohesion: 0.07
Nodes (26): QGraphicsRectItem, 바운딩박스 오버레이 QGraphicsItem., 단일 TextRegion 바운딩박스를 표시하는 QGraphicsItem.      ScrollHandDrag 충돌 방지를 위해 mousePres, 클릭 시 호출할 콜백 등록. callback(region_id: str)., 좌클릭 시 콜백으로 region_id 전달. ScrollHandDrag 패닝 차단., 씬의 모든 RegionOverlayItem 관리.      QObject를 상속하여 region_selected 시그널을 제공한다.     아이, RegionOverlayItem, RegionOverlayManager (+18 more)

### Community 11 - "Community 11"
Cohesion: 0.05
Nodes (14): ChatController, JobController, RegionEditState, _on_chat_message(), _on_translation_edited(), _on_translation_preview_requested(), 처리 시작 — 상태를 OCR_RUNNING 으로 전환., QObject (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.08
Nodes (21): 원본/번역 비교 뷰 (슬라이더 방식)., ImageViewer, 줌/패닝 지원 QGraphicsView 이미지 뷰어., 드래그 패닝, 휠 줌 지원 이미지 뷰어., numpy RGB 배열 → 뷰어에 표시., _on_preview_ready(), QGraphicsView, ImageViewer 위젯 단위 테스트 — 줌/패닝/이미지 로드 동작 검증. (+13 more)

### Community 13 - "Community 13"
Cohesion: 0.11
Nodes (33): Agent Is Not Translator Principle, QThread and Signal Responsiveness Pattern, Plugin-Based Architecture, Project Overview, Phase 5 GUI Integration Completion, Legacy CLAUDE Guidance Note, Async Plugin Method Convention, No Blocking I/O in GUI Thread (+25 more)

### Community 14 - "Community 14"
Cohesion: 0.15
Nodes (7): _on_job_selected(), Session, test_session_job_management(), make_job(), TestSessionCRUD, TestSessionNextPending, TestSessionRunningCount

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (17): crop_region(), cv2_to_pil(), pil_to_cv2(), PIL Image (RGB) → BGR numpy 배열., 긴 쪽이 max_dim을 넘지 않도록 리사이즈.      Returns:         (resized_image, scale_factor), BGR numpy 배열 → PIL Image (RGB)., resize_keep_aspect(), 300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨. (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.19
Nodes (5): get_logger(), LogContext, 이름으로 로거 반환. 최초 요청 시 생성., with 문으로 사용하는 구조화 로그 컨텍스트., TestLoggerUtils

### Community 17 - "Community 17"
Cohesion: 0.25
Nodes (9): _get_project_root(), load_project_env(), Project-level `.env` loading helpers., Load environment variables from the project root `.env` file.      Existing proc, Project `.env` loader unit tests., test_load_project_env_does_not_override_existing_environment(), test_load_project_env_logs_warning_on_loader_failure(), test_load_project_env_populates_missing_environment_value() (+1 more)

### Community 18 - "Community 18"
Cohesion: 0.33
Nodes (4): TestTheme, apply_theme(), load_theme_stylesheet(), normalize_theme_name()

### Community 19 - "Community 19"
Cohesion: 0.67
Nodes (2): download_font(), main()

### Community 20 - "Community 20"
Cohesion: 1.0
Nodes (2): API Key Management Rules, Environment Variable API Key Setup

### Community 32 - "Community 32"
Cohesion: 1.0
Nodes (1): 플러그인 초기화 (모델 로드, API 클라이언트 생성 등).

### Community 33 - "Community 33"
Cohesion: 1.0
Nodes (1): 설정 유효성 검사.         반환값: 오류 메시지 목록. 빈 목록이면 유효.

### Community 34 - "Community 34"
Cohesion: 1.0
Nodes (1): 플러그인 기능 정보 반환.         예: {'languages': ['en', 'ko'], 'batch_size': 50}

### Community 44 - "Community 44"
Cohesion: 1.0
Nodes (1): 점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')

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
- **105 isolated node(s):** `Project `.env` loader unit tests.`, `300x200 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨.`, `200x300 이미지 max_dim=100 → 긴 쪽(300)이 100이 됨.`, `max_dim 이하 이미지는 scale=1.0 반환, 원본 크기 유지.`, `정확히 max_dim 크기 이미지는 그대로 반환.` (+100 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Community 19`** (4 nodes): `download_font()`, `main()`, `_progress_hook()`, `download_fonts.py`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 20`** (2 nodes): `API Key Management Rules`, `Environment Variable API Key Setup`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 32`** (1 nodes): `플러그인 초기화 (모델 로드, API 클라이언트 생성 등).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 33`** (1 nodes): `설정 유효성 검사.         반환값: 오류 메시지 목록. 빈 목록이면 유효.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 34`** (1 nodes): `플러그인 기능 정보 반환.         예: {'languages': ['en', 'ko'], 'batch_size': 50}`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Community 44`** (1 nodes): `점(.) 경로로 중첩 설정 조회. 예: get('processing', 'default_target_lang')`
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

- **Why does `TextRegion` connect `Community 0` to `Community 1`, `Community 2`, `Community 4`, `Community 6`, `Community 8`, `Community 10`, `Community 11`?**
  _High betweenness centrality (0.207) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `Community 5` to `Community 1`, `Community 3`, `Community 4`, `Community 6`, `Community 7`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 14`?**
  _High betweenness centrality (0.167) - this node is a cross-community bridge._
- **Why does `ProcessingJob` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 5`, `Community 6`, `Community 7`, `Community 8`, `Community 11`, `Community 14`?**
  _High betweenness centrality (0.163) - this node is a cross-community bridge._
- **Are the 390 inferred relationships involving `TextRegion` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`TextRegion` has 390 INFERRED edges - model-reasoned connections that need verification._
- **Are the 323 inferred relationships involving `BoundingBox` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`BoundingBox` has 323 INFERRED edges - model-reasoned connections that need verification._
- **Are the 241 inferred relationships involving `ProcessingJob` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`ProcessingJob` has 241 INFERRED edges - model-reasoned connections that need verification._
- **Are the 149 inferred relationships involving `ConfigManager` (e.g. with `공유 테스트 픽스처 — 전체 테스트 스위트용.` and `ConfigManager mock — get() 호출에 기본값 반환.`) actually correct?**
  _`ConfigManager` has 149 INFERRED edges - model-reasoned connections that need verification._
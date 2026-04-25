# 플러그인 개발 가이드

trans_image의 플러그인 시스템은 OCR / 번역 / 번역 보조 에이전트를 독립적으로 교체할 수 있도록 설계되어 있다.

---

## 공통 기반: PluginBase (`src/plugins/base/plugin_base.py`)

모든 플러그인이 상속하는 최상위 ABC.

```python
class PluginBase(ABC):
    PLUGIN_NAME: str        # 고유 식별자 (plugins.yaml에서 참조)
    PLUGIN_VERSION: str     # 버전 문자열
    PLUGIN_DESCRIPTION: str # 사람이 읽는 설명

    async def load(self) -> None: ...    # 초기화 (API 클라이언트, 모델 로드)
    async def unload(self) -> None: ...  # 정리
    def validate_config(self) -> list[str]: ...  # 설정 오류 목록 반환 (빈 리스트 = 정상)
    def get_capabilities(self) -> dict[str, Any]: ...
    def get_config(self, key: str, default: Any = None) -> Any: ...
    @property
    def is_loaded(self) -> bool: ...
```

---

## OCR 플러그인 (`AbstractOCRPlugin`)

### 필수 구현 메서드

```python
async def detect_regions(
    self,
    image: np.ndarray,           # RGB numpy 배열
) -> list[TextRegion]:
    """이미지에서 텍스트 영역 탐지.
    반환: bbox + raw_text + confidence가 채워진 TextRegion 목록
    """
```

### 기존 구현체

| ID | 파일 | 특징 |
|----|------|------|
| `easyocr` | `ocr/easyocr_plugin.py` | 기본, 80+ 언어 지원 |
| `paddleocr` | `ocr/paddleocr_plugin.py` | CJK 특화, 선택 의존성 |

### 새 OCR 플러그인 추가

1. `AbstractOCRPlugin` 상속
2. `PLUGIN_NAME`, `PLUGIN_VERSION`, `PLUGIN_DESCRIPTION` 설정
3. `detect_regions()` 구현
4. `config/plugins.yaml`의 `ocr` 섹션에 등록:

```yaml
ocr:
  - id: my_ocr
    class: src.plugins.ocr.my_ocr_plugin.MyOCRPlugin
    enabled: true
```

---

## 번역 플러그인 (`AbstractTranslatorPlugin`)

### 필수 구현 메서드

```python
async def translate(
    self,
    text: str,
    source_lang: str,
    target_lang: str,
    context: str = "",        # 번역 보조 에이전트가 생성한 컨텍스트 힌트
) -> TranslationResult:
    """단일 텍스트 번역."""

async def translate_batch(
    self,
    regions: list[TextRegion],
    source_lang: str,
    target_lang: str,
) -> list[TranslationResult]:
    """여러 TextRegion 일괄 번역.
    regions[i]에 대응하는 TranslationResult[i]를 순서 유지하여 반환.
    각 region.context_hint를 translate() 호출 시 context 인자로 전달.
    """

def get_supported_language_pairs(self) -> list[tuple[str, str]]:
    """지원 언어 쌍 목록. ("*", "*") 이면 모든 쌍 지원."""
```

### TranslationResult 구조

```python
@dataclass
class TranslationResult:
    translated_text: str
    source_lang: str
    target_lang: str
    is_success: bool
    error_message: str | None = None
    confidence: float = 1.0
```

### 기존 구현체

| ID | 파일 | API 키 |
|----|------|--------|
| `deepl` | `translators/deepl_translator.py` | `DEEPL_API_KEY` |
| `gemini` | `translators/gemini_translator.py` | `GOOGLE_API_KEY` |
| `grok` | `translators/grok_translator.py` | `XAI_API_KEY` |
| `papago` | `translators/papago_translator.py` | `PAPAGO_CLIENT_ID`, `PAPAGO_CLIENT_SECRET` |
| `ollama` | `translators/ollama_translator.py` | 불필요 (로컬) |

### 새 번역 플러그인 추가

1. `AbstractTranslatorPlugin` 상속
2. 클래스 변수 3개 설정
3. `load()` / `unload()` / `validate_config()` / `get_capabilities()` 구현
4. `translate()` / `translate_batch()` / `get_supported_language_pairs()` 구현
5. `config/plugins.yaml`의 `translators` 섹션에 등록

---

## 번역 보조 에이전트 플러그인 (`AbstractAgentPlugin`)

> **주의**: 이것은 사용자와 대화하는 에이전트가 아니다.
> 파이프라인 내부에서 OCR 보정 / 컨텍스트 생성 / 번역 검증을 담당하는 플러그인이다.
> 대화형 에이전트는 `src/chat/chat_agent.py` 참조.

### 필수 구현 메서드

```python
async def analyze_ocr_results(
    self,
    regions: list[TextRegion],
    image_description: str | None = None,
) -> list[TextRegion]:
    """OCR 오류 교정 + reading_order 부여.
    실패해도 원본 반환 (파이프라인 중단 금지).
    """

async def generate_translation_context(
    self,
    regions: list[TextRegion],
    job: ProcessingJob,
) -> dict[str, str]:
    """각 region_id에 대한 번역 컨텍스트 힌트 생성.
    반환: {region_id: hint_string}
    """

async def validate_translations(
    self,
    original_regions: list[TextRegion],
    translated_regions: list[TextRegion],
) -> list[TextRegion]:
    """번역 품질 검증. 문제 영역에 needs_review=True 설정."""

async def stream_analysis(self, prompt: str) -> AsyncIterator[str]:
    """GUI 실시간 피드백용 스트리밍. 텍스트 청크를 yield."""
```

### 번역 API 직접 호출 금지

번역 보조 에이전트는 번역 API를 절대 호출하지 않는다. 번역은 파이프라인이 번역 플러그인에 위임한다.

### 기존 구현체

| ID | 파일 | 모델 |
|----|------|------|
| `claude` | `agents/claude_agent.py` | claude-sonnet-4-6 |
| `openai` | `agents/openai_agent.py` | gpt-4o |
| `gemini` | `agents/gemini_agent.py` | gemini-1.5-flash |
| `ollama` | `agents/ollama_agent.py` | 로컬 설정 가능 |

### 새 번역 보조 에이전트 플러그인 추가

1. `AbstractAgentPlugin` 상속
2. 4개 추상 메서드 구현
3. `config/plugins.yaml`의 `agents` 섹션에 등록:

```yaml
agents:
  - id: my_agent
    class: src.plugins.agents.my_agent.MyAgentPlugin
    enabled: true
    config:
      api_key: "${MY_API_KEY}"
      model: "my-model-name"
```

---

## plugins.yaml 구조

```yaml
# config/plugins.yaml
ocr:
  default: easyocr
  plugins:
    - id: easyocr
      class: src.plugins.ocr.easyocr_plugin.EasyOCRPlugin
      enabled: true
    - id: paddleocr
      class: src.plugins.ocr.paddleocr_plugin.PaddleOCRPlugin
      enabled: false   # pip install trans_image[paddleocr] 필요

translators:
  default: deepl
  plugins:
    - id: deepl
      class: src.plugins.translators.deepl_translator.DeepLTranslatorPlugin
      enabled: true
      config:
        api_key: "${DEEPL_API_KEY}"
    # ... 나머지 번역기

agents:
  default: claude
  plugins:
    - id: claude
      class: src.plugins.agents.claude_agent.ClaudeAgentPlugin
      enabled: true
      config:
        api_key: "${ANTHROPIC_API_KEY}"
        model: "claude-sonnet-4-6"
        max_tokens: 4096
```

---

## API 키 관리 규칙

- API 키는 **환경변수**에서만 로드 (`${VAR_NAME}` 형식으로 plugins.yaml에 참조)
- 소스 코드 또는 설정 파일에 하드코딩 금지
- `.env` 파일은 `.gitignore`에 포함 — commit/push 절대 금지
- 플러그인 `validate_config()`에서 키 존재 여부 검증, 오류 메시지에 환경변수 이름 명시

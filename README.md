# trans_image

AI 기반 이미지 텍스트 자동 번역 프로그램.
이미지 속 텍스트를 OCR로 감지하고, AI 에이전트가 컨텍스트를 분석한 뒤 원문 위치에 번역문을 삽입합니다.

---

## 요구사항

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (패키지 매니저)

---

## uv 설치

### Windows

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS / Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

설치 후 터미널을 재시작하거나 PATH를 reload하세요.

```bash
uv --version  # 설치 확인
```

---

## 저장소 클론 & 환경 구축

```bash
# 1. 클론
git clone https://github.com/<your-org>/trans_image.git
cd trans_image

# 2. 가상환경 생성 + 의존성 설치 (uv.lock 기반으로 완전히 재현 가능)
uv sync

# 3. 개발 도구 포함 설치
uv sync --extra dev
```

> `uv sync`는 `.venv/`를 자동 생성합니다. `activate` 없이 바로 아래 명령어로 실행 가능합니다.

---

## 실행

```bash
# GUI 모드
uv run python main.py

# CLI 모드
uv run python -m trans_image --input image.png --output result.png \
  --target-lang ko --translator deepl --agent claude
```

---

## API 키 설정

`.env.example`을 복사해 `.env`를 만들고 키를 채우세요.

```bash
cp .env.example .env
```

```dotenv
# .env
GOOGLE_API_KEY=...
DEEPL_API_KEY=...
ANTHROPIC_API_KEY=...
XAI_API_KEY=...
PAPAGO_CLIENT_ID=...
PAPAGO_CLIENT_SECRET=...
```

> `.env`는 `.gitignore`에 포함되어 있어 절대 커밋되지 않습니다.

---

## PaddleOCR (선택)

기본 OCR은 EasyOCR입니다. PaddleOCR을 사용하려면:

```bash
uv sync --extra paddleocr
```

---

## 테스트 & 린트

```bash
uv run pytest tests/unit/          # 단위 테스트
uv run pytest tests/integration/   # 통합 테스트 (API 키 필요)
uv run pytest --cov=src            # 커버리지

uv run ruff check .                # 린트
uv run mypy src                    # 타입 체크
```

---

## 의존성 추가/업데이트

```bash
# 패키지 추가 (pyproject.toml + uv.lock 자동 업데이트)
uv add <package>

# 개발용 패키지 추가
uv add --dev <package>

# 전체 의존성 최신 버전으로 업데이트
uv lock --upgrade
uv sync
```

> `uv.lock`은 반드시 git에 커밋하세요. 모든 협업자가 동일한 환경을 재현할 수 있습니다.

---

## 로컬 AI (Ollama, 선택)

```bash
# Ollama 설치 후
ollama pull llama3.1
```

`config/default_config.yaml`에서 `ollama.base_url` 확인 (기본값: `http://localhost:11434`).

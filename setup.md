# 환경 설정 & 실행

> AGENTS.md에서 참조됩니다.

## 의존성 설치

```bash
uv sync
uv sync --extra dev
```

## API 키 설정

기본 설정 파일(`config/default_config.yaml`)에는 실제 API 키를 넣지 않는다.
실행 전 환경변수 또는 `.env`에 키를 설정한다.

```bash
export DEEPL_API_KEY="your-deepl-key"
export GOOGLE_API_KEY="your-google-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export OPENAI_API_KEY="your-openai-key"
export XAI_API_KEY="your-xai-key"
export PAPAGO_CLIENT_ID="your-papago-client-id"
export PAPAGO_CLIENT_SECRET="your-papago-client-secret"
```

`.env`를 쓰려면 `.env.example`을 복사해 사용한다.
앱 실행 시 프로젝트 루트의 `.env`를 자동 로드한다.
이미 셸에 export된 환경변수가 있으면 `.env`보다 우선하고,
둘 다 없을 때만 `config/default_config.yaml`의 `api_keys`를 fallback으로 사용한다.

## 실행

```bash
# GUI 모드
uv run python main.py

# 설치된 프로젝트 스크립트
uv run trans-image

# CLI 모드
uv run python -m src --input image.png --output result.png \
  --target-lang ko --translator deepl --agent claude
```

## 현재 동작 기준

- `설정` 다이얼로그에서 변경한 값은 `ConfigManager.save()`를 통해 영속 저장되며 다음 실행에도 다시 적용된다.
- 단일 이미지 처리는 `WorkerPool(max_concurrent=2)` 기준으로 동시에 최대 2개까지만 실행된다.
- 동시 실행 제한을 넘는 새 단일 이미지 작업은 대기열 적재 대신 즉시 거절된다.

## 테스트

```bash
pytest tests/unit/          # 단위 테스트
pytest tests/integration/   # 통합 테스트 (API 키 필요)
pytest --cov=src            # 커버리지 측정
```

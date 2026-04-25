# 환경 설정 & 실행

> AGENTS.md에서 참조됩니다.

## 의존성 설치

```bash
pip install -e ".[dev]"
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

## 실행

```bash
# GUI 모드
python main.py

# CLI 모드
python -m trans_image --input image.png --output result.png \
  --target-lang ko --translator deepl --agent claude
```

## 테스트

```bash
pytest tests/unit/          # 단위 테스트
pytest tests/integration/   # 통합 테스트 (API 키 필요)
pytest --cov=src            # 커버리지 측정
```

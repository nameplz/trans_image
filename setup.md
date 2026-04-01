# 환경 설정 & 실행

> CLAUDE.md에서 `@docs/setup.md`로 참조됩니다.

## 의존성 설치

```bash
pip install -e ".[dev]"
```

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

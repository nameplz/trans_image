#!/usr/bin/env bash
# 파일 수정 후 자동 린트 실행
# ruff가 설치되어 있으면 src/ 검사, 없으면 조용히 종료
if command -v ruff &>/dev/null; then
    ruff check src/ --quiet 2>/dev/null || true
fi

"""Project-level `.env` loading helpers."""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

from src.utils.logger import get_logger

logger = get_logger("trans_image.env")


def _get_project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_project_env() -> None:
    """Load environment variables from the project root `.env` file.

    Existing process environment variables always win over `.env` values.
    Missing `.env` files and loader failures are treated as non-fatal.
    """
    dotenv_path = _get_project_root() / ".env"
    if not dotenv_path.exists():
        return

    try:
        load_dotenv(dotenv_path=dotenv_path, override=False)
    except Exception as exc:
        logger.warning("프로젝트 .env 로드 실패: %s", exc)

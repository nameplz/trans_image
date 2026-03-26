"""ConfigManager 단위 테스트.

TDD 순서에 따라 테스트를 먼저 작성 (RED).
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.core.config_manager import ConfigManager


# ---------------------------------------------------------------------------
# 헬퍼 — 임시 YAML 파일 생성
# ---------------------------------------------------------------------------

def _write_yaml(tmp_path: Path, content: dict) -> Path:
    """딕셔너리를 YAML 파일로 작성하고 경로 반환."""
    p = tmp_path / "config.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(content, f, allow_unicode=True)
    return p


def _write_raw_yaml(tmp_path: Path, raw: str) -> Path:
    """원시 문자열을 YAML 파일로 작성하고 경로 반환."""
    p = tmp_path / "config.yaml"
    p.write_text(raw, encoding="utf-8")
    return p


def _plugins_yaml(tmp_path: Path) -> Path:
    """빈 플러그인 YAML 파일 생성."""
    p = tmp_path / "plugins.yaml"
    p.write_text("{}", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# (a) 환경변수가 설정된 경우 → 환경변수 값을 반환해야 한다
# ---------------------------------------------------------------------------

class TestGetApiKeyFromEnvironment:
    """환경변수 우선 동작 검증."""

    def test_returns_env_var_value_when_set(self, tmp_path):
        """DEEPL_API_KEY 환경변수가 설정되면 그 값을 반환한다."""
        cfg_path = _write_yaml(tmp_path, {"api_keys": {"deepl": ""}})
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        with patch.dict(os.environ, {"DEEPL_API_KEY": "env-deepl-secret"}):
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result == "env-deepl-secret"

    def test_env_var_takes_precedence_over_yaml_value(self, tmp_path):
        """환경변수가 YAML 값보다 우선한다."""
        cfg_path = _write_yaml(tmp_path, {"api_keys": {"deepl": "yaml-deepl-key"}})
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        with patch.dict(os.environ, {"DEEPL_API_KEY": "env-override"}):
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result == "env-override"

    def test_returns_env_var_for_google(self, tmp_path):
        """GOOGLE_API_KEY 환경변수가 설정되면 그 값을 반환한다."""
        cfg_path = _write_yaml(tmp_path, {"api_keys": {"google": ""}})
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        with patch.dict(os.environ, {"GOOGLE_API_KEY": "env-google-secret"}):
            result = mgr.get_api_key("GOOGLE_API_KEY")

        assert result == "env-google-secret"


# ---------------------------------------------------------------------------
# (b) YAML 빈 문자열 폴백 → "" 반환
# ---------------------------------------------------------------------------

class TestGetApiKeyFromYamlEmptyString:
    """YAML api_keys 값이 빈 문자열일 때 폴백 동작 검증."""

    def test_returns_empty_string_when_yaml_is_empty_and_no_env(self, tmp_path):
        """환경변수 없고 YAML 값이 '' 이면 빈 문자열을 반환한다."""
        cfg_path = _write_yaml(tmp_path, {"api_keys": {"deepl": ""}})
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        # 해당 환경변수가 없는 상태를 보장
        env = {k: v for k, v in os.environ.items() if k != "DEEPL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result == ""

    def test_returns_empty_string_for_missing_key_in_yaml(self, tmp_path):
        """api_keys 섹션에 해당 키가 없으면 빈 문자열을 반환한다."""
        cfg_path = _write_yaml(tmp_path, {"api_keys": {}})
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        env = {k: v for k, v in os.environ.items() if k != "XAI_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = mgr.get_api_key("XAI_API_KEY")

        assert result == ""

    def test_returns_empty_string_when_api_keys_section_absent(self, tmp_path):
        """api_keys 섹션 자체가 없을 때도 빈 문자열을 반환한다."""
        cfg_path = _write_yaml(tmp_path, {})
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        env = {k: v for k, v in os.environ.items() if k != "DEEPL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result == ""


# ---------------------------------------------------------------------------
# (c) YAML에 딕셔너리가 있을 때 → 방어 코드로 "" 반환
# ---------------------------------------------------------------------------

class TestGetApiKeyDefensiveAgainstDict:
    """YAML api_keys 값이 딕셔너리일 때 방어 코드 검증.

    broken YAML (deepl: env: DEEPL_API_KEY)은 PyYAML이
    {"env": "DEEPL_API_KEY"} 딕셔너리로 파싱한다.
    get_api_key()는 이 경우 "" 를 반환하고 경고를 로그해야 한다.
    """

    def _make_broken_config(self, tmp_path: Path) -> Path:
        """deepl 값이 딕셔너리인 YAML 설정 파일을 생성한다."""
        raw = "api_keys:\n  deepl:\n    env: DEEPL_API_KEY\n"
        return _write_raw_yaml(tmp_path, raw)

    def test_returns_empty_string_when_yaml_value_is_dict(self, tmp_path):
        """api_keys.deepl 이 딕셔너리면 빈 문자열을 반환한다."""
        cfg_path = self._make_broken_config(tmp_path)
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        env = {k: v for k, v in os.environ.items() if k != "DEEPL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result == ""
        assert isinstance(result, str)

    def test_returns_empty_string_not_dict_repr(self, tmp_path):
        """반환값이 딕셔너리의 str() 표현이 아닌 순수 빈 문자열이어야 한다."""
        cfg_path = self._make_broken_config(tmp_path)
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        env = {k: v for k, v in os.environ.items() if k != "DEEPL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result != "{'env': 'DEEPL_API_KEY'}"
        assert result != str({"env": "DEEPL_API_KEY"})

    def test_dict_value_does_not_raise(self, tmp_path):
        """딕셔너리 값이 있어도 예외가 발생하지 않아야 한다."""
        cfg_path = self._make_broken_config(tmp_path)
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        env = {k: v for k, v in os.environ.items() if k != "DEEPL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            # 예외가 발생하면 테스트 실패
            result = mgr.get_api_key("DEEPL_API_KEY")

        assert result is not None

    def test_warning_logged_when_yaml_value_is_not_string(self, tmp_path, caplog):
        """YAML 값이 str이 아닐 때 경고 로그가 기록되어야 한다."""
        import logging
        cfg_path = self._make_broken_config(tmp_path)
        mgr = ConfigManager(config_path=cfg_path, plugins_path=_plugins_yaml(tmp_path))
        mgr.load()

        env = {k: v for k, v in os.environ.items() if k != "DEEPL_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with caplog.at_level(logging.WARNING, logger="trans_image.config"):
                mgr.get_api_key("DEEPL_API_KEY")

        assert len(caplog.records) >= 1
        warning_messages = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("DEEPL_API_KEY" in msg or "deepl" in msg.lower() for msg in warning_messages)

"""Unit tests for Settings."""

from __future__ import annotations

import pytest

from src.config.settings import Settings, get_settings


@pytest.mark.unit
def test_settings_loads_openrouter_defaults(clean_env: Settings) -> None:
    assert clean_env.openrouter_base_url == "https://openrouter.ai/api/v1"
    assert clean_env.openrouter_model == "deepseek/deepseek-chat"
    assert clean_env.is_ai_configured is True


@pytest.mark.unit
def test_settings_detects_missing_api_key(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))
    settings = Settings()
    assert settings.is_ai_configured is False
    get_settings.cache_clear()


@pytest.mark.unit
def test_ensure_directories_creates_paths(clean_env: Settings) -> None:
    assert clean_env.logs_dir.is_dir()
    assert clean_env.cache_dir.is_dir()
    assert clean_env.exports_dir.is_dir()

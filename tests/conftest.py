"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from src.config.settings import Settings, get_settings
from src.core.container import reset_container
from src.core.bootstrap import build_container


@pytest.fixture()
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> Iterator[Settings]:
    """Provide isolated Settings pointing at a temp directory."""
    get_settings.cache_clear()
    reset_container()

    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-not-real")
    monkeypatch.setenv("OPENROUTER_MODEL", "deepseek/deepseek-chat")
    monkeypatch.setenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("EXPORTS_DIR", str(tmp_path / "exports"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("ASSETS_DIR", str(tmp_path / "assets"))

    get_settings.cache_clear()
    settings = Settings()
    settings.ensure_directories()
    yield settings

    get_settings.cache_clear()
    reset_container()


@pytest.fixture()
def container(clean_env: Settings):
    """Bootstrapped DI container for unit tests."""
    return build_container(clean_env)

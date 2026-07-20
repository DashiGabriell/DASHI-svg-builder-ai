"""Typed application settings loaded from environment / `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: .../svg-builder-ai (three levels up from this file)
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Immutable runtime configuration for SVG Builder AI.

    Values are read from environment variables and an optional `.env` file.
    OpenRouter is the only supported AI gateway — never call model vendors
    directly.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # --- Application ---------------------------------------------------------
    app_name: str = Field(default="SVG Builder AI", alias="APP_NAME")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        alias="LOG_LEVEL",
    )

    # --- OpenRouter ----------------------------------------------------------
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field(
        default="deepseek/deepseek-chat",
        alias="OPENROUTER_MODEL",
    )
    openrouter_base_url: str = Field(
        default="https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_timeout_seconds: float = Field(
        default=60.0,
        alias="OPENROUTER_TIMEOUT_SECONDS",
        gt=0,
    )
    openrouter_max_retries: int = Field(
        default=3,
        alias="OPENROUTER_MAX_RETRIES",
        ge=0,
        le=10,
    )
    openrouter_site_url: str = Field(
        default="https://github.com/svg-builder-ai",
        alias="OPENROUTER_SITE_URL",
    )
    openrouter_app_name: str = Field(
        default="SVG Builder AI",
        alias="OPENROUTER_APP_NAME",
    )

    # --- Paths ---------------------------------------------------------------
    cache_dir: Path = Field(default=PROJECT_ROOT / "cache", alias="CACHE_DIR")
    exports_dir: Path = Field(default=PROJECT_ROOT / "exports", alias="EXPORTS_DIR")
    logs_dir: Path = Field(default=PROJECT_ROOT / "logs", alias="LOGS_DIR")
    assets_dir: Path = Field(default=PROJECT_ROOT / "assets", alias="ASSETS_DIR")

    @field_validator("cache_dir", "exports_dir", "logs_dir", "assets_dir", mode="before")
    @classmethod
    def resolve_relative_paths(cls, value: str | Path) -> Path:
        """Resolve relative directory paths against the project root."""
        path = Path(value)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()

    @property
    def project_root(self) -> Path:
        """Absolute path to the repository root."""
        return PROJECT_ROOT

    @property
    def is_ai_configured(self) -> bool:
        """Return True when an OpenRouter API key is present."""
        return bool(self.openrouter_api_key.strip())

    def ensure_directories(self) -> None:
        """Create runtime directories if they do not exist."""
        for directory in (self.cache_dir, self.exports_dir, self.logs_dir, self.assets_dir):
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance.

    Use `get_settings.cache_clear()` in tests when env vars change.
    """
    return Settings()

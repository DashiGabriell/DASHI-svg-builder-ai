"""Domain and infrastructure exception hierarchy."""

from __future__ import annotations


class SVGBuilderError(Exception):
    """Base exception for all SVG Builder AI errors."""


class ConfigurationError(SVGBuilderError):
    """Raised when application configuration is invalid or incomplete."""


class OpenRouterError(SVGBuilderError):
    """Raised when the OpenRouter HTTP client fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AIServiceError(SVGBuilderError):
    """Raised when the high-level AI service cannot fulfil a request."""


class ProcessorError(SVGBuilderError):
    """Raised when an image/SVG processor fails."""


class PluginError(SVGBuilderError):
    """Raised when a plugin cannot be loaded or executed."""

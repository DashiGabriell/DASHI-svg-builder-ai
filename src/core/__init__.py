"""Core package: DI, events, commands, and shared interfaces."""

from src.core.container import Container, get_container
from src.core.exceptions import (
    AIServiceError,
    ConfigurationError,
    OpenRouterError,
    ProcessorError,
    SVGBuilderError,
)

__all__ = [
    "AIServiceError",
    "ConfigurationError",
    "Container",
    "OpenRouterError",
    "ProcessorError",
    "SVGBuilderError",
    "get_container",
]

"""Unit tests for the DI container and bootstrap."""

from __future__ import annotations

import pytest

from src.config.settings import Settings
from src.core.container import Container
from src.core.events import EventBus
from src.core.exceptions import ConfigurationError
from src.services.ai import AIService, OpenRouterClient


@pytest.mark.unit
def test_container_resolve_singleton() -> None:
    container = Container()
    container.register(EventBus, factory=lambda _c: EventBus())
    a = container.resolve(EventBus)
    b = container.resolve(EventBus)
    assert a is b


@pytest.mark.unit
def test_container_missing_service_raises() -> None:
    container = Container()
    with pytest.raises(ConfigurationError):
        container.resolve(EventBus)


@pytest.mark.unit
def test_bootstrap_registers_ai_stack(container) -> None:
    assert container.is_registered(Settings)
    assert container.is_registered(OpenRouterClient)
    assert container.is_registered(AIService)

    ai = container.resolve(AIService)
    assert ai.is_enabled is True

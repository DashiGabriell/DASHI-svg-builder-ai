"""Composition root — wires Settings, logging, DI, AI, events, plugins."""

from __future__ import annotations

import logging

from src.config.settings import Settings, get_settings
from src.core.commands import CommandHistory
from src.core.container import Container, get_container
from src.core.events import EventBus
from src.processors.base.plugin_registry import PluginRegistry, get_plugin_registry
from src.services.ai.ai_service import AIService
from src.services.ai.openrouter_client import OpenRouterClient
from src.services.pipeline_service import PipelineService
from src.exports.export_service import ExportService
from src.utils.logging import setup_logging

logger = logging.getLogger(__name__)


def build_container(settings: Settings | None = None) -> Container:
    """Assemble and return the application DI container.

    This is the single composition root: every long-lived service is
    registered here and resolved elsewhere via injection.
    """
    settings = settings or get_settings()
    settings.ensure_directories()
    setup_logging(settings)

    container = get_container()
    container.reset()

    container.register(Settings, instance=settings)
    container.register(EventBus, factory=lambda _c: EventBus())
    container.register(CommandHistory, factory=lambda _c: CommandHistory())
    container.register(PluginRegistry, instance=get_plugin_registry())

    container.register(
        OpenRouterClient,
        factory=lambda c: OpenRouterClient(c.resolve(Settings)),
    )
    container.register(
        AIService,
        factory=lambda c: AIService(
            c.resolve(OpenRouterClient),
            default_model=c.resolve(Settings).openrouter_model,
            enabled=c.resolve(Settings).is_ai_configured,
        ),
    )

    # Discover processor plugins (load / upscale / remove_background, …)
    registry = container.resolve(PluginRegistry)
    try:
        imported = registry.discover("src.processors")
        logger.info(
            "Plugin discovery imported %d module(s); available=%s",
            imported,
            registry.available(),
        )
    except Exception:  # noqa: BLE001 — discovery must not block boot
        logger.exception("Plugin discovery failed; continuing without plugins")

    container.register(
        PipelineService,
        factory=lambda c: PipelineService(
            c.resolve(PluginRegistry),
            cache_dir=c.resolve(Settings).cache_dir,
            ai_service=c.resolve(AIService),
        ),
    )
    container.register(
        ExportService,
        factory=lambda c: ExportService(exports_dir=c.resolve(Settings).exports_dir),
    )

    logger.info(
        "Container ready | env=%s | ai_configured=%s | model=%s",
        settings.app_env,
        settings.is_ai_configured,
        settings.openrouter_model,
    )
    return container


def create_app_context() -> Container:
    """Public bootstrap entry used by ``main`` and tests."""
    return build_container()

"""Desktop application bootstrap for CustomTkinter."""

from __future__ import annotations

import logging

from src.config.settings import Settings
from src.core.commands import CommandHistory
from src.core.container import Container
from src.core.events import EventBus
from src.exports.export_service import ExportService
from src.services.ai import AIService
from src.services.pipeline_service import PipelineService
from src.ui.controller import AppController
from src.ui.themes.apply import apply_appearance
from src.ui.views.main_window import MainWindow

logger = logging.getLogger(__name__)


def run_app(container: Container) -> None:
    """Build the main window and enter the Tk event loop."""
    settings = container.resolve(Settings)
    event_bus = container.resolve(EventBus)
    ai = container.resolve(AIService)
    pipeline = container.resolve(PipelineService)
    export_service = container.resolve(ExportService)
    history = container.resolve(CommandHistory)

    apply_appearance()
    controller = AppController(
        event_bus,
        pipeline=pipeline,
        export_service=export_service,
        history=history,
    )

    window = MainWindow(
        controller,
        event_bus,
        ai_enabled=ai.is_enabled,
        ai_model=settings.openrouter_model,
    )
    logger.info("Starting CustomTkinter mainloop")
    window.mainloop()

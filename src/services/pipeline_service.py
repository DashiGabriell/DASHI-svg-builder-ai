"""Pipeline orchestration service for raster processors."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.core.exceptions import PluginError, ProcessorError
from src.models.project import ProjectDocument
from src.processors.base.plugin_registry import PluginRegistry
from src.services.ai import AIService

logger = logging.getLogger(__name__)

# Sidebar action_id → processor plugin name
ACTION_PROCESSOR_MAP: dict[str, str] = {
    "enhance_quality": "enhance_quality",
    "remove_background": "remove_background",
    "detect_objects": "detect_objects",
    "separate_layers": "separate_layers",
    "vectorize": "vectorize",
    "optimize_svg": "optimize_svg",
}


class PipelineService:
    """Runs registered processors against a ProjectDocument.

    Keeps the UI controller thin: resolve plugin → process → return document.
    """

    def __init__(
        self,
        registry: PluginRegistry,
        *,
        cache_dir: Path,
        ai_service: AIService | None = None,
    ) -> None:
        self._registry = registry
        self._cache_dir = cache_dir
        self._ai = ai_service

    @property
    def available_actions(self) -> list[str]:
        """Action ids that currently map to a live processor."""
        registered = set(self._registry.available())
        return [action for action, name in ACTION_PROCESSOR_MAP.items() if name in registered]

    def run(
        self,
        action_id: str,
        project: ProjectDocument,
        **kwargs: Any,
    ) -> ProjectDocument:
        """Execute the processor mapped to ``action_id``.

        Raises:
            PluginError: Unknown or unmapped action.
            ProcessorError: Processor execution failure.
        """
        processor_name = ACTION_PROCESSOR_MAP.get(action_id)
        if processor_name is None:
            raise PluginError(f"Nenhum processador mapeado para ação '{action_id}'")

        processor = self._registry.create(processor_name)
        payload = {
            "cache_dir": self._cache_dir,
            "ai_service": self._ai,
            **kwargs,
        }
        logger.info("Pipeline running action=%s processor=%s", action_id, processor_name)
        result = processor.process(project, **payload)
        if not isinstance(result, ProjectDocument):
            raise ProcessorError(f"Processor '{processor_name}' returned invalid result")
        return result

    def normalize_loaded(self, project: ProjectDocument) -> ProjectDocument:
        """Ensure a freshly imported project has a cached working PNG."""
        if "load_image" not in self._registry.available():
            return project
        processor = self._registry.create("load_image")
        return processor.process(project, cache_dir=self._cache_dir)

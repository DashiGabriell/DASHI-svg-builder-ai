"""Processor: classical super-resolution / quality enhancement."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.utils.image_io import (
    image_stats_summary,
    load_rgba,
    project_cache_dir,
    resolve_working_image,
    save_rgba,
)
from src.utils.super_resolution import upscale_image

logger = logging.getLogger(__name__)


@get_plugin_registry().register(name="enhance_quality")
class UpscaleProcessor(BaseProcessor):
    """Improve resolution offline; optionally ask AI for structural hints only."""

    processor_name = "enhance_quality"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para UpscaleProcessor")

        scale = float(kwargs.get("scale", 2.0))
        sharpen = bool(kwargs.get("sharpen", True))
        ai_service = kwargs.get("ai_service")

        source = resolve_working_image(project.original_image_path, project.processed_image_path)
        rgba = load_rgba(source)
        upscaled = upscale_image(rgba, scale=scale, sharpen=sharpen)

        out_dir = project_cache_dir(cache_root, project.id)
        out_path = out_dir / "upscaled.png"
        save_rgba(out_path, upscaled)

        h, w = upscaled.shape[:2]
        ai_notes = list(project.ai_notes)
        if ai_service is not None and getattr(ai_service, "is_enabled", False):
            hint = self._optional_ai_hint(ai_service, image_stats_summary(upscaled))
            if hint:
                ai_notes.append(hint)

        return project.model_copy(
            update={
                "processed_image_path": out_path,
                "width": w,
                "height": h,
                "stage": PipelineStage.UPSCALE,
                "ai_notes": ai_notes,
                "metadata": {
                    **project.metadata,
                    "upscale_scale": scale,
                    "upscale_sharpen": sharpen,
                },
            }
        )

    @staticmethod
    def _optional_ai_hint(ai_service: Any, stats: str) -> str | None:
        """Best-effort structural suggestion — never blocks / fails the CV path."""
        try:
            suggestion = asyncio.run(
                ai_service.suggest_structure(
                    f"Artwork after upscale. CV stats: {stats}. "
                    "Suggest layer organization for SVG export."
                )
            )
            if suggestion.summary:
                return f"[upscale] {suggestion.summary}"
            if suggestion.improvements:
                return f"[upscale] " + "; ".join(suggestion.improvements[:3])
        except Exception:  # noqa: BLE001
            logger.warning("AI structure hint skipped", exc_info=True)
        return None

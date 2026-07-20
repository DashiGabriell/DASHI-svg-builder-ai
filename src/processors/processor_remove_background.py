"""Processor: remove image background (traditional CV + optional AI note)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.utils.background import BgMethod, remove_background
from src.utils.image_io import (
    image_stats_summary,
    load_rgba,
    project_cache_dir,
    resolve_working_image,
    save_rgba,
)

logger = logging.getLogger(__name__)


@get_plugin_registry().register(name="remove_background")
class RemoveBackgroundProcessor(BaseProcessor):
    """Cut out the background using flood-fill (default), grabcut, or threshold."""

    processor_name = "remove_background"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para RemoveBackgroundProcessor")

        method: BgMethod = kwargs.get("method", "flood_fill")  # type: ignore[assignment]
        tolerance = int(kwargs.get("tolerance", 28))
        ai_service = kwargs.get("ai_service")

        source = resolve_working_image(project.original_image_path, project.processed_image_path)
        rgba = load_rgba(source)
        cutout = remove_background(rgba, method=method, tolerance=tolerance)

        out_dir = project_cache_dir(cache_root, project.id)
        out_path = out_dir / "no_background.png"
        save_rgba(out_path, cutout)

        h, w = cutout.shape[:2]
        opaque_ratio = float((cutout[:, :, 3] > 10).mean())
        ai_notes = list(project.ai_notes)
        if ai_service is not None and getattr(ai_service, "is_enabled", False):
            note = self._optional_ai_note(ai_service, image_stats_summary(cutout))
            if note:
                ai_notes.append(note)

        return project.model_copy(
            update={
                "processed_image_path": out_path,
                "width": w,
                "height": h,
                "stage": PipelineStage.BACKGROUND_REMOVED,
                "ai_notes": ai_notes,
                "metadata": {
                    **project.metadata,
                    "bg_method": method,
                    "bg_tolerance": tolerance,
                    "opaque_ratio": opaque_ratio,
                },
            }
        )

    @staticmethod
    def _optional_ai_note(ai_service: Any, stats: str) -> str | None:
        try:
            text = asyncio.run(
                ai_service.describe_image_context(
                    f"Foreground cutout ready for SVG layering. Stats: {stats}"
                )
            )
            if text.strip():
                return f"[background] {text.strip()[:240]}"
        except Exception:  # noqa: BLE001
            logger.warning("AI background note skipped", exc_info=True)
        return None

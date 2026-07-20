"""Processor: normalize / reload working raster into the project cache."""

from __future__ import annotations

from typing import Any

from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.utils.image_io import load_rgba, project_cache_dir, save_rgba


@get_plugin_registry().register(name="load_image")
class LoadImageProcessor(BaseProcessor):
    """Copy the source image into the project cache as a normalized PNG."""

    processor_name = "load_image"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para LoadImageProcessor")

        source = project.original_image_path or project.source_path
        if source is None:
            raise ValueError("Projeto sem caminho de imagem de origem")

        rgba = load_rgba(source)
        out_dir = project_cache_dir(cache_root, project.id)
        out_path = out_dir / "original.png"
        save_rgba(out_path, rgba)

        h, w = rgba.shape[:2]
        return project.model_copy(
            update={
                "original_image_path": out_path,
                "processed_image_path": out_path,
                "width": w,
                "height": h,
                "stage": PipelineStage.LOADED,
                "metadata": {
                    **project.metadata,
                    "normalized": True,
                    "channels": int(rgba.shape[2]),
                },
            }
        )

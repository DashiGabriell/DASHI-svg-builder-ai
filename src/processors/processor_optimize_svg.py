"""Processor: optimize vectorized SVG and layer paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.exceptions import ProcessorError
from src.models.layer import Layer
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.utils.image_io import project_cache_dir
from src.utils.svg_builder import build_svg_document, save_svg
from src.utils.svg_optimizer import optimize_layer_paths, optimize_svg


@get_plugin_registry().register(name="optimize_svg")
class OptimizeSvgProcessor(BaseProcessor):
    """Simplify paths, drop empties/duplicates and store optimized SVG."""

    processor_name = "optimize_svg"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para OptimizeSvgProcessor")

        precision = int(kwargs.get("precision", 2))
        minify = bool(kwargs.get("minify", True))

        if not project.layers and not project.svg_content:
            raise ProcessorError("Nada para otimizar. Vetorize o projeto antes.")

        updated_layers: list[Layer] = []
        for layer in project.layers:
            optimized_d = optimize_layer_paths(layer.path_data, precision=precision)
            updated_layers.append(layer.model_copy(update={"path_data": optimized_d}))

        # Rebuild from optimized layer paths to keep groups consistent
        draft = project.model_copy(update={"layers": updated_layers})
        mutable = [layer.model_copy() for layer in updated_layers]
        rebuilt = build_svg_document(draft, mutable, pretty=False)
        result = optimize_svg(
            rebuilt or project.svg_content,
            precision=precision,
            minify=minify,
            remove_duplicates=True,
        )

        final_layers: list[Layer] = []
        for original, mutated in zip(updated_layers, mutable, strict=True):
            final_layers.append(
                original.model_copy(update={"svg_group": mutated.svg_group or original.svg_group})
            )

        out_dir = project_cache_dir(cache_root, project.id)
        out_path = out_dir / "optimized.svg"
        save_svg(str(out_path), result.svg)

        return project.model_copy(
            update={
                "layers": final_layers,
                "svg_content": result.svg,
                "stage": PipelineStage.OPTIMIZED,
                "metadata": {
                    **project.metadata,
                    "svg_optimized_path": str(out_path),
                    "optimize_stats": {
                        "path_nodes_before": result.stats.path_nodes_before,
                        "path_nodes_after": result.stats.path_nodes_after,
                        "empty_groups_removed": result.stats.empty_groups_removed,
                        "duplicate_paths_removed": result.stats.duplicate_paths_removed,
                        "bytes_before": result.stats.bytes_before,
                        "bytes_after": result.stats.bytes_after,
                    },
                },
            }
        )

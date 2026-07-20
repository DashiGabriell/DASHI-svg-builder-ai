"""Processor: vectorize each layer independently via Potrace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.exceptions import ProcessorError
from src.models.layer import Layer
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.utils.image_io import project_cache_dir
from src.utils.potrace_trace import load_mask_array, trace_mask_to_path
from src.utils.svg_builder import build_svg_document, save_svg


@get_plugin_registry().register(name="vectorize")
class VectorizeProcessor(BaseProcessor):
    """Trace every layer mask with Potrace and assemble a modular SVG.

    Critical rule: each layer becomes its own ``<g id="...">`` — the whole
    image is never collapsed into a single path.
    """

    processor_name = "vectorize"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para VectorizeProcessor")

        if not project.layers:
            raise ProcessorError(
                "Nenhuma camada para vetorizar. Execute 'Separar camadas' antes."
            )

        turdsize = int(kwargs.get("turdsize", 2))
        alphamax = float(kwargs.get("alphamax", 1.0))
        opttolerance = float(kwargs.get("opttolerance", 0.2))
        opticurve = bool(kwargs.get("opticurve", True))

        updated_layers: list[Layer] = []
        traced = 0
        for layer in project.layers:
            mask_path = layer.source_mask_path
            if not mask_path or not Path(mask_path).exists():
                # Keep layer but mark empty path
                updated_layers.append(
                    layer.model_copy(
                        update={
                            "path_data": "",
                            "metadata": {
                                **layer.metadata,
                                "vectorize_error": "mask_missing",
                            },
                        }
                    )
                )
                continue

            mask = load_mask_array(mask_path)
            result = trace_mask_to_path(
                mask,
                turdsize=turdsize,
                alphamax=alphamax,
                opttolerance=opttolerance,
                opticurve=opticurve,
            )
            if not result.empty:
                traced += 1
            updated_layers.append(
                layer.model_copy(
                    update={
                        "path_data": result.path_d,
                        "metadata": {
                            **layer.metadata,
                            "curve_count": result.curve_count,
                            "vectorized": not result.empty,
                        },
                    }
                )
            )

        if traced == 0:
            raise ProcessorError(
                "Potrace não gerou paths. Verifique as máscaras das camadas."
            )

        # Build SVG from layers with path_data populated
        draft = project.model_copy(update={"layers": updated_layers})
        # Attach svg_group snippets via builder side-effect on copies
        # Re-build with mutable layer copies that receive svg_group
        mutable = [layer.model_copy() for layer in updated_layers]
        svg_content = build_svg_document(draft, mutable)

        # Persist svg_group from mutable back
        final_layers: list[Layer] = []
        for original, mutated in zip(updated_layers, mutable, strict=True):
            final_layers.append(
                original.model_copy(update={"svg_group": mutated.svg_group or original.svg_group})
            )

        out_dir = project_cache_dir(cache_root, project.id)
        svg_path = out_dir / "vectorized.svg"
        save_svg(str(svg_path), svg_content)

        return project.model_copy(
            update={
                "layers": final_layers,
                "svg_content": svg_content,
                "stage": PipelineStage.VECTORIZED,
                "metadata": {
                    **project.metadata,
                    "vectorized_layers": traced,
                    "svg_path": str(svg_path),
                    "potrace": {
                        "turdsize": turdsize,
                        "alphamax": alphamax,
                        "opttolerance": opttolerance,
                        "engine": "potracer",
                    },
                },
            }
        )

"""Processor: separate detected objects into editable Layer models."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from PIL import Image

from src.models.layer import Layer, LayerType
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.services.layer_repository import assign_semantic_ids, parse_layer_type
from src.utils.image_io import (
    load_rgba,
    project_cache_dir,
    resolve_working_image,
    save_rgba,
)
from src.utils.segmentation import (
    DetectMethod,
    detect_objects,
    extract_object_rgba,
)

logger = logging.getLogger(__name__)


@get_plugin_registry().register(name="separate_layers")
class SeparateLayersProcessor(BaseProcessor):
    """Turn each detected region into a ``Layer`` with mask + semantic id."""

    processor_name = "separate_layers"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para SeparateLayersProcessor")

        ai_service = kwargs.get("ai_service")
        method: DetectMethod = kwargs.get(
            "method",
            project.metadata.get("detection_method", "contours"),
        )  # type: ignore[assignment]
        min_area = float(kwargs.get("min_area", 64.0))

        source = resolve_working_image(project.original_image_path, project.processed_image_path)
        # Prefer non-overlay raster: if last processed is overlay, use original
        source = self._prefer_raster_source(project, source)
        rgba = load_rgba(source)

        cached = project.metadata.get("detections")
        objects = detect_objects(rgba, method=method, min_area=min_area)
        # If we have the same count of cached masks, reuse paths later
        _ = cached

        layers_dir = project_cache_dir(cache_root, project.id) / "layers"
        layers_dir.mkdir(parents=True, exist_ok=True)

        layers: list[Layer] = []
        descriptions: list[str] = []
        for obj in objects:
            cutout = extract_object_rgba(rgba, obj.mask)
            layer_raster = layers_dir / f"layer_{obj.index:02d}.png"
            mask_path = layers_dir / f"mask_{obj.index:02d}.png"
            save_rgba(layer_raster, cutout)
            Image.fromarray(obj.mask, mode="L").save(mask_path)

            layer = Layer(
                id=f"layer_{obj.index:02d}",
                name=f"Layer {obj.index + 1:02d}",
                layer_type=LayerType.UNKNOWN,
                color=obj.color_hex,
                opacity=1.0,
                visible=True,
                z_index=obj.index,
                bounds=obj.bounds,
                source_mask_path=str(mask_path),
                metadata={
                    "area": obj.area,
                    "centroid": {"x": obj.centroid[0], "y": obj.centroid[1]},
                    "raster_path": str(layer_raster),
                    "detection_index": obj.index,
                },
            )
            layers.append(layer)
            descriptions.append(obj.description)

        ai_notes = list(project.ai_notes)
        if ai_service is not None and getattr(ai_service, "is_enabled", False) and descriptions:
            layers, note = self._classify_with_ai(ai_service, layers, descriptions)
            if note:
                ai_notes.append(note)
        else:
            # Heuristic fallback: size-based rough typing stays UNKNOWN; color retained
            layers = [
                layer.model_copy(update={"layer_type": LayerType.OTHER}) for layer in layers
            ]

        layers = assign_semantic_ids(layers)

        # Composite preview of separated layers (visible stack)
        composite = self._compose_layers_preview(rgba.shape, layers)
        preview_path = project_cache_dir(cache_root, project.id) / "layers_preview.png"
        save_rgba(preview_path, composite)

        return project.model_copy(
            update={
                "layers": layers,
                "processed_image_path": preview_path,
                "stage": PipelineStage.LAYERS_SEPARATED,
                "ai_notes": ai_notes,
                "metadata": {
                    **project.metadata,
                    "layer_count": len(layers),
                    "detections": [
                        {
                            "index": i,
                            "id": layer.id,
                            "type": layer.layer_type.value,
                            "color": layer.color,
                            "bounds": layer.bounds.as_dict(),
                            "mask_path": layer.source_mask_path,
                        }
                        for i, layer in enumerate(layers)
                    ],
                },
            }
        )

    @staticmethod
    def _prefer_raster_source(project: ProjectDocument, current: Path) -> Path:
        """Avoid using detection overlay / preview PNGs as separation source."""
        name = current.name.lower()
        if "overlay" in name or "preview" in name:
            parent = current.parent
            for fname in ("no_background.png", "upscaled.png", "original.png"):
                alt = parent / fname
                if alt.exists():
                    return alt
            for candidate in (project.original_image_path, project.source_path):
                if candidate is not None and candidate.exists():
                    return candidate
        return current

    @staticmethod
    def _classify_with_ai(
        ai_service: Any,
        layers: list[Layer],
        descriptions: list[str],
    ) -> tuple[list[Layer], str | None]:
        try:
            result = asyncio.run(ai_service.classify_objects(descriptions))
        except Exception:  # noqa: BLE001
            logger.warning("AI classification skipped", exc_info=True)
            fallback = [
                layer.model_copy(update={"layer_type": LayerType.OTHER}) for layer in layers
            ]
            return fallback, None

        updated: list[Layer] = []
        for layer, label in zip(layers, result.labels, strict=False):
            layer_type = parse_layer_type(label.label)
            name = label.suggested_id or label.label
            updated.append(
                layer.model_copy(
                    update={
                        "layer_type": layer_type,
                        "name": name,
                        "metadata": {
                            **layer.metadata,
                            "ai_confidence": label.confidence,
                            "ai_description": label.description,
                        },
                    }
                )
            )
        # If AI returned fewer labels, pad remaining as OTHER
        if len(updated) < len(layers):
            for layer in layers[len(updated) :]:
                updated.append(layer.model_copy(update={"layer_type": LayerType.OTHER}))

        note = f"[layers] classified {len(result.labels)} object(s) via AI"
        return updated, note

    @staticmethod
    def _compose_layers_preview(
        shape: tuple[int, ...],
        layers: list[Layer],
    ) -> Any:
        import numpy as np

        h, w = shape[0], shape[1]
        canvas = np.zeros((h, w, 4), dtype=np.uint8)
        # Checkerboard for transparency visibility
        for y in range(0, h, 8):
            for x in range(0, w, 8):
                if ((x // 8) + (y // 8)) % 2 == 0:
                    canvas[y : y + 8, x : x + 8, :3] = 40
                    canvas[y : y + 8, x : x + 8, 3] = 255
                else:
                    canvas[y : y + 8, x : x + 8, :3] = 55
                    canvas[y : y + 8, x : x + 8, 3] = 255

        for layer in sorted(layers, key=lambda item: item.z_index):
            raster = layer.metadata.get("raster_path")
            if not raster or not Path(str(raster)).exists():
                continue
            rgba = load_rgba(Path(str(raster)))
            alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
            rgb = rgba[:, :, :3].astype(np.float32)
            base = canvas[:, :, :3].astype(np.float32)
            blended = base * (1.0 - alpha) + rgb * alpha
            canvas[:, :, :3] = np.clip(blended, 0, 255).astype(np.uint8)
            canvas[:, :, 3] = np.maximum(canvas[:, :, 3], rgba[:, :, 3])
        return canvas

"""Processor: detect objects via contours / connected components."""

from __future__ import annotations

from typing import Any

from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.processors.base.processor_base import BaseProcessor
from src.utils.image_io import (
    load_rgba,
    project_cache_dir,
    resolve_working_image,
    save_rgba,
)
from src.utils.segmentation import (
    DetectMethod,
    detect_objects,
    render_detection_overlay,
)


@get_plugin_registry().register(name="detect_objects")
class DetectObjectsProcessor(BaseProcessor):
    """Find foreground regions and store detection metadata + overlay preview."""

    processor_name = "detect_objects"

    @property
    def name(self) -> str:
        return self.processor_name

    def _execute(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        cache_root = kwargs.get("cache_dir")
        if cache_root is None:
            raise ValueError("cache_dir é obrigatório para DetectObjectsProcessor")

        method: DetectMethod = kwargs.get("method", "contours")  # type: ignore[assignment]
        min_area = float(kwargs.get("min_area", 64.0))
        max_objects = int(kwargs.get("max_objects", 64))

        source = resolve_working_image(project.original_image_path, project.processed_image_path)
        rgba = load_rgba(source)
        objects = detect_objects(
            rgba,
            method=method,
            min_area=min_area,
            max_objects=max_objects,
        )

        out_dir = project_cache_dir(cache_root, project.id) / "detections"
        out_dir.mkdir(parents=True, exist_ok=True)

        detections_meta: list[dict[str, Any]] = []
        for obj in objects:
            mask_path = out_dir / f"mask_{obj.index:02d}.png"
            # Save mask as L
            from PIL import Image

            Image.fromarray(obj.mask, mode="L").save(mask_path)
            detections_meta.append(obj.to_metadata_dict(mask_path=str(mask_path)))

        overlay = render_detection_overlay(rgba, objects)
        overlay_path = project_cache_dir(cache_root, project.id) / "detections_overlay.png"
        save_rgba(overlay_path, overlay)

        return project.model_copy(
            update={
                "processed_image_path": overlay_path,
                "stage": PipelineStage.OBJECTS_DETECTED,
                "metadata": {
                    **project.metadata,
                    "detections": detections_meta,
                    "detection_method": method,
                    "detection_count": len(objects),
                },
            }
        )

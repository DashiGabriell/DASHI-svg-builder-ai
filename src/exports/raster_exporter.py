"""Raster exporters (PNG / WEBP) from SVG or layer composites."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from src.core.exceptions import ProcessorError
from src.core.interfaces import Exporter
from src.exports.base import ExportFormat
from src.models.project import ProjectDocument
from src.utils.svg_builder import build_svg_document

logger = logging.getLogger(__name__)

RasterFmt = Literal["PNG", "WEBP"]


def render_project_raster(project: ProjectDocument) -> Image.Image:
    """Rasterize the project for PNG/WEBP export.

    Prefer CairoSVG when available; otherwise composite layer rasters /
    processed preview with Pillow.
    """
    svg = project.svg_content or build_svg_document(project, pretty=False)
    if svg.strip():
        rendered = _try_cairosvg(svg, project.width, project.height)
        if rendered is not None:
            return rendered

    composited = _composite_from_layers(project)
    if composited is not None:
        return composited

    if project.processed_image_path and Path(project.processed_image_path).exists():
        return Image.open(project.processed_image_path).convert("RGBA")

    if project.original_image_path and Path(project.original_image_path).exists():
        return Image.open(project.original_image_path).convert("RGBA")

    raise ProcessorError("Não foi possível rasterizar o projeto para exportação.")


def _try_cairosvg(svg: str, width: int, height: int) -> Image.Image | None:
    try:
        import cairosvg  # type: ignore[import-untyped]
        from io import BytesIO

        png_bytes = cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            output_width=width or None,
            output_height=height or None,
        )
        return Image.open(BytesIO(png_bytes)).convert("RGBA")
    except Exception:  # noqa: BLE001 — cairo often missing on Windows
        logger.info("cairosvg unavailable; using Pillow composite fallback")
        return None


def _composite_from_layers(project: ProjectDocument) -> Image.Image | None:
    width = project.width or 1
    height = project.height or 1
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    painted = False
    for layer in sorted(project.layers, key=lambda item: item.z_index):
        if not layer.visible:
            continue
        raster = layer.metadata.get("raster_path")
        if not raster or not Path(str(raster)).exists():
            continue
        overlay = Image.open(str(raster)).convert("RGBA")
        if overlay.size != canvas.size:
            overlay = overlay.resize(canvas.size, Image.Resampling.LANCZOS)
        canvas = Image.alpha_composite(canvas, overlay)
        painted = True
    return canvas if painted else None


class _RasterExporterBase(Exporter):
    """Shared PNG/WEBP write logic."""

    format_name: RasterFmt = "PNG"

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        image = render_project_raster(project)
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        save_kwargs: dict[str, Any] = {}
        if self.format_name == "WEBP":
            save_kwargs["quality"] = int(kwargs.get("quality", 90))
            save_kwargs["method"] = 6
        image.save(path, format=self.format_name, **save_kwargs)
        return str(path.resolve())


class PngExporter(_RasterExporterBase):
    """Export a PNG raster of the project."""

    format_name: RasterFmt = "PNG"

    @property
    def format_id(self) -> str:
        return ExportFormat.PNG.value


class WebpExporter(_RasterExporterBase):
    """Export a WEBP raster of the project."""

    format_name: RasterFmt = "WEBP"

    @property
    def format_id(self) -> str:
        return ExportFormat.WEBP.value

"""SVG exporters (raw and optimized)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.exceptions import ProcessorError
from src.core.interfaces import Exporter
from src.exports.base import ExportFormat
from src.models.project import ProjectDocument
from src.utils.svg_builder import build_svg_document, save_svg
from src.utils.svg_optimizer import optimize_svg


class SvgExporter(Exporter):
    """Export the current (or rebuilt) SVG document."""

    @property
    def format_id(self) -> str:
        return ExportFormat.SVG.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        svg = project.svg_content or build_svg_document(project, pretty=True)
        if not svg.strip():
            raise ProcessorError("SVG vazio — vetorize antes de exportar.")
        path = Path(destination)
        save_svg(str(path), svg)
        return str(path.resolve())


class OptimizedSvgExporter(Exporter):
    """Export a freshly optimized SVG (even if optimize stage was skipped)."""

    @property
    def format_id(self) -> str:
        return ExportFormat.SVG_OPTIMIZED.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        precision = int(kwargs.get("precision", 2))
        source = project.svg_content or build_svg_document(project, pretty=False)
        if not source.strip():
            raise ProcessorError("SVG vazio — vetorize antes de exportar.")
        result = optimize_svg(source, precision=precision, minify=True)
        path = Path(destination)
        save_svg(str(path), result.svg)
        return str(path.resolve())

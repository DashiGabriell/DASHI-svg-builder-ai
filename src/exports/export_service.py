"""Orchestrates format Strategy exporters."""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.exceptions import ProcessorError
from src.core.interfaces import Exporter
from src.exports.base import ExportFormat
from src.exports.frameworks import (
    AngularExporter,
    AnimatedSvgExporter,
    FlutterExporter,
    GodotExporter,
    ReactExporter,
    UnityExporter,
    VueExporter,
)
from src.exports.json_exporter import JsonExporter
from src.exports.raster_exporter import PngExporter, WebpExporter
from src.exports.svg_exporter import OptimizedSvgExporter, SvgExporter
from src.models.project import PipelineStage, ProjectDocument

logger = logging.getLogger(__name__)


class ExportService:
    """Facade that resolves and runs the correct Exporter Strategy."""

    def __init__(self, *, exports_dir: Path) -> None:
        self._exports_dir = exports_dir
        self._exporters: dict[ExportFormat, Exporter] = {
            ExportFormat.SVG: SvgExporter(),
            ExportFormat.SVG_OPTIMIZED: OptimizedSvgExporter(),
            ExportFormat.SVG_ANIMATED: AnimatedSvgExporter(),
            ExportFormat.JSON: JsonExporter(),
            ExportFormat.PNG: PngExporter(),
            ExportFormat.WEBP: WebpExporter(),
            ExportFormat.REACT: ReactExporter(),
            ExportFormat.VUE: VueExporter(),
            ExportFormat.ANGULAR: AngularExporter(),
            ExportFormat.FLUTTER: FlutterExporter(),
            ExportFormat.GODOT: GodotExporter(),
            ExportFormat.UNITY: UnityExporter(),
        }

    @property
    def exports_dir(self) -> Path:
        return self._exports_dir

    def available_formats(self) -> list[ExportFormat]:
        return list(self._exporters.keys())

    def export(
        self,
        project: ProjectDocument,
        fmt: ExportFormat | str,
        destination: str | Path | None = None,
        **kwargs: object,
    ) -> Path:
        """Export ``project`` to ``destination`` (or auto path under exports/)."""
        format_id = ExportFormat(fmt) if not isinstance(fmt, ExportFormat) else fmt
        exporter = self._exporters.get(format_id)
        if exporter is None:
            raise ProcessorError(f"Formato de exportação não suportado: {format_id}")

        self._exports_dir.mkdir(parents=True, exist_ok=True)
        if destination is None:
            stem = project.name or project.id or "export"
            safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in stem)
            destination = self._exports_dir / f"{safe}{format_id.extension}"

        path = Path(destination)
        written = Path(exporter.export(project, str(path), **kwargs))
        logger.info("Exported %s → %s", format_id.value, written)
        return written

    def mark_exported(self, project: ProjectDocument, path: Path) -> ProjectDocument:
        """Return a copy of the project advanced to EXPORTED stage."""
        return project.model_copy(
            update={
                "stage": PipelineStage.EXPORTED,
                "metadata": {
                    **project.metadata,
                    "last_export_path": str(path),
                },
            }
        )

"""JSON layer export."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.core.exceptions import ProcessorError
from src.core.interfaces import Exporter
from src.exports.base import ExportFormat
from src.models.project import ProjectDocument


class JsonExporter(Exporter):
    """Export ``ProjectDocument.to_layers_json()`` as pretty JSON."""

    @property
    def format_id(self) -> str:
        return ExportFormat.JSON.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        if not project.layers:
            raise ProcessorError("Nenhuma camada para exportar em JSON.")
        payload = project.to_layers_json()
        # Ensure path field matches spec example
        for layer_dict in payload.get("layers", []):
            layer_dict.setdefault("path", layer_dict.get("path", ""))
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return str(path.resolve())

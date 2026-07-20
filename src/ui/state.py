"""Mutable application UI state held by the desktop controller."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from src.models.project import PipelineStage, ProjectDocument


@dataclass
class AppState:
    """In-memory UI state synchronized via the EventBus."""

    project: ProjectDocument = field(default_factory=ProjectDocument)
    status_message: str = "Pronto"
    busy: bool = False
    last_export_path: Path | None = None
    selected_layer_id: str | None = None

    @property
    def has_image(self) -> bool:
        """True when an original image has been loaded."""
        return self.project.original_image_path is not None

    @property
    def stage_label(self) -> str:
        """Human-readable pipeline stage."""
        labels: dict[PipelineStage, str] = {
            PipelineStage.EMPTY: "Vazio",
            PipelineStage.LOADED: "Imagem carregada",
            PipelineStage.UPSCALE: "Resolução melhorada",
            PipelineStage.BACKGROUND_REMOVED: "Fundo removido",
            PipelineStage.OBJECTS_DETECTED: "Objetos detectados",
            PipelineStage.LAYERS_SEPARATED: "Camadas separadas",
            PipelineStage.VECTORIZED: "Vetorizado",
            PipelineStage.OPTIMIZED: "SVG otimizado",
            PipelineStage.EXPORTED: "Exportado",
        }
        return labels.get(self.project.stage, self.project.stage.value)

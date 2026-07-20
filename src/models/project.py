"""In-memory project document that flows through the processing pipeline."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.models.layer import Layer


class PipelineStage(StrEnum):
    """Stages of the image → SVG pipeline."""

    EMPTY = "empty"
    LOADED = "loaded"
    UPSCALE = "upscale"
    BACKGROUND_REMOVED = "background_removed"
    OBJECTS_DETECTED = "objects_detected"
    LAYERS_SEPARATED = "layers_separated"
    VECTORIZED = "vectorized"
    OPTIMIZED = "optimized"
    EXPORTED = "exported"


class ProjectDocument(BaseModel):
    """Central aggregate root representing the current working project.

    Processors receive and return a ``ProjectDocument``, keeping the
    pipeline pure and easy to test.
    """

    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = Field(default="Untitled Project")
    source_path: Path | None = Field(default=None)
    original_image_path: Path | None = Field(default=None)
    processed_image_path: Path | None = Field(default=None)
    svg_content: str = Field(default="")
    stage: PipelineStage = Field(default=PipelineStage.EMPTY)
    layers: list[Layer] = Field(default_factory=list)
    width: int = Field(default=0, ge=0)
    height: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    ai_notes: list[str] = Field(
        default_factory=list,
        description="Suggestions / classifications produced by AIService",
    )

    def get_layer(self, layer_id: str) -> Layer | None:
        """Find a layer by id."""
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def replace_layers(self, layers: list[Layer]) -> ProjectDocument:
        """Return a copy with a new layer list."""
        return self.model_copy(update={"layers": layers})

    def advance_stage(self, stage: PipelineStage) -> ProjectDocument:
        """Return a copy advanced to the given pipeline stage."""
        return self.model_copy(update={"stage": stage})

    def to_layers_json(self) -> dict[str, Any]:
        """Build the exportable JSON structure described in the product spec."""
        return {
            "project_id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "stage": self.stage.value,
            "layers": [layer.to_export_dict() for layer in self.layers],
            "ai_notes": list(self.ai_notes),
        }

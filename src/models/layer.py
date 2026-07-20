"""Layer domain model — one SVG group / semantic object."""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from src.models.bounds import Bounds


class LayerType(StrEnum):
    """Semantic classification of a layer / object.

    Extended by AI classification (OpenRouter) and by user overrides.
    """

    UNKNOWN = "unknown"
    BUILDING = "building"
    TREE = "tree"
    LAMP = "lamp"
    PANEL = "panel"
    NEON = "neon"
    ROAD = "road"
    VEHICLE = "vehicle"
    PERSON = "person"
    SKY = "sky"
    SMOKE = "smoke"
    WINDOW = "window"
    LIGHT = "light"
    BACKGROUND = "background"
    FOREGROUND = "foreground"
    TEXT = "text"
    ICON = "icon"
    OTHER = "other"


class Layer(BaseModel):
    """A single editable SVG layer produced by object separation.

    Each layer maps to an SVG ``<g id="...">`` group and is vectorized
    independently — never as part of a single monolithic path.
    """

    id: str = Field(
        default_factory=lambda: f"layer_{uuid4().hex[:8]}",
        description="Stable unique id (e.g. building_01)",
    )
    name: str = Field(default="Untitled Layer")
    layer_type: LayerType = Field(default=LayerType.UNKNOWN)
    color: str = Field(default="#808080", description="Primary fill HEX color")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    visible: bool = Field(default=True)
    locked: bool = Field(default=False)
    z_index: int = Field(default=0, description="Stacking order (lower = behind)")
    bounds: Bounds = Field(default_factory=Bounds)
    path_data: str = Field(default="", description="SVG path `d` attribute")
    svg_group: str = Field(default="", description="Raw SVG <g> markup (optional cache)")
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_mask_path: str | None = Field(
        default=None,
        description="Optional path to raster mask used for this layer",
    )

    def to_export_dict(self) -> dict[str, Any]:
        """Serialize for JSON export payloads."""
        return {
            "id": self.id,
            "type": self.layer_type.value,
            "name": self.name,
            "color": self.color,
            "opacity": self.opacity,
            "visible": self.visible,
            "bounds": self.bounds.as_dict(),
            "path": self.path_data,
            "z_index": self.z_index,
            "metadata": self.metadata,
        }

    def with_semantic_id(self, index: int) -> Layer:
        """Return a copy with an auto-generated semantic id like ``building_01``."""
        semantic = f"{self.layer_type.value}_{index:02d}"
        return self.model_copy(update={"id": semantic, "name": self.name or semantic})

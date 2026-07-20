"""Axis-aligned bounding box used by layers and exporters."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class Bounds(BaseModel):
    """Rectangle in image / SVG coordinate space."""

    x: float = Field(default=0.0, description="Left edge")
    y: float = Field(default=0.0, description="Top edge")
    width: float = Field(default=0.0, ge=0.0, description="Width")
    height: float = Field(default=0.0, ge=0.0, description="Height")

    @model_validator(mode="after")
    def validate_dimensions(self) -> Bounds:
        """Ensure non-negative geometry (already constrained by Field)."""
        return self

    @property
    def right(self) -> float:
        """Right edge (x + width)."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Bottom edge (y + height)."""
        return self.y + self.height

    def as_dict(self) -> dict[str, float]:
        """Serialize to a plain dict for JSON export."""
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

"""Shared helpers for framework code generation."""

from __future__ import annotations

import re

from src.models.layer import Layer
from src.models.project import ProjectDocument


def to_pascal_case(identifier: str) -> str:
    """Convert ``building_01`` / ``road-02`` into ``Building01`` / ``Road02``."""
    parts = re.split(r"[_\-\s]+", identifier.strip())
    return "".join(part[:1].upper() + part[1:] for part in parts if part) or "Layer"


def to_camel_case(identifier: str) -> str:
    """Convert identifier to camelCase (``building01``)."""
    pascal = to_pascal_case(identifier)
    return pascal[:1].lower() + pascal[1:] if pascal else "layer"


def safe_filename(stem: str, *, ext: str) -> str:
    """Sanitize a filename stem and append extension (with leading dot)."""
    clean = re.sub(r"[^\w\-]+", "_", stem.strip()) or "export"
    if not ext.startswith("."):
        ext = f".{ext}"
    return f"{clean}{ext}"


def visible_layers(project: ProjectDocument) -> list[Layer]:
    """Return visible layers sorted by z-index."""
    return sorted(
        (layer for layer in project.layers if layer.visible),
        key=lambda item: item.z_index,
    )


def layer_component_name(layer: Layer) -> str:
    """React/Vue-friendly component name for a layer."""
    return to_pascal_case(layer.id)

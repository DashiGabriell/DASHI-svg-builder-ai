"""Pydantic schemas for AI request / response payloads."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ChatRole(StrEnum):
    """OpenAI-compatible chat roles (used by OpenRouter)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Single chat message in an OpenRouter conversation."""

    role: ChatRole
    content: str | list[dict[str, Any]]

    def to_api_dict(self) -> dict[str, Any]:
        """Serialize for the OpenRouter chat completions API."""
        return {"role": self.role.value, "content": self.content}


class ObjectLabel(BaseModel):
    """Semantic label assigned to a detected region / layer."""

    label: str = Field(description="Normalized type, e.g. 'building'")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    suggested_id: str | None = Field(default=None, description="e.g. building_01")
    description: str = Field(default="")


class ClassificationResult(BaseModel):
    """Result of semantic classification over detected objects."""

    labels: list[ObjectLabel] = Field(default_factory=list)
    raw_text: str = Field(default="", description="Raw model response for debugging")
    model: str = Field(default="")


class StructureSuggestion(BaseModel):
    """High-level structural advice from the model (never applied blindly)."""

    summary: str = Field(default="")
    improvements: list[str] = Field(default_factory=list)
    grouping_hints: list[str] = Field(default_factory=list)
    model: str = Field(default="")
    raw_text: str = Field(default="")

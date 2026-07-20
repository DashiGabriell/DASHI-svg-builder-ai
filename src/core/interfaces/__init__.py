"""Shared Protocol / ABC interfaces used across layers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from src.models.layer import Layer
from src.models.project import ProjectDocument


@runtime_checkable
class AIClientProtocol(Protocol):
    """Contract for any AI HTTP gateway (OpenRouter today)."""

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request and return the raw JSON body."""
        ...


class Processor(ABC):
    """Strategy interface for image/SVG processors and plugins.

    Concrete processors live under `src/processors/` and are discovered
    via the PluginRegistry without modifying core code.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique processor id (e.g. 'remove_background')."""

    @property
    def description(self) -> str:
        """Short human-readable summary."""
        return self.__class__.__doc__ or self.name

    @abstractmethod
    def process(self, project: ProjectDocument, **kwargs: Any) -> ProjectDocument:
        """Transform the project document and return the updated state."""


class Exporter(ABC):
    """Strategy interface for export targets (SVG, JSON, React, etc.)."""

    @property
    @abstractmethod
    def format_id(self) -> str:
        """Exporter format key (e.g. 'svg', 'react')."""

    @abstractmethod
    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        """Export the project and return the written path."""


class LayerRepository(ABC):
    """Repository pattern for layer persistence / querying."""

    @abstractmethod
    def list_layers(self) -> list[Layer]:
        """Return all layers in order."""

    @abstractmethod
    def get_by_id(self, layer_id: str) -> Layer | None:
        """Fetch a single layer by id."""

    @abstractmethod
    def add(self, layer: Layer) -> None:
        """Insert a layer."""

    @abstractmethod
    def remove(self, layer_id: str) -> bool:
        """Delete a layer. Returns True if it existed."""

    @abstractmethod
    def update(self, layer: Layer) -> None:
        """Replace an existing layer."""

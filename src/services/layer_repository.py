"""Layer helpers: semantic IDs, type parsing, repository."""

from __future__ import annotations

from src.core.interfaces import LayerRepository
from src.models.layer import Layer, LayerType


def parse_layer_type(label: str) -> LayerType:
    """Map a free-form / AI label to ``LayerType``."""
    normalized = label.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "car": LayerType.VEHICLE,
        "truck": LayerType.VEHICLE,
        "auto": LayerType.VEHICLE,
        "human": LayerType.PERSON,
        "people": LayerType.PERSON,
        "plant": LayerType.TREE,
        "vegetation": LayerType.TREE,
        "streetlight": LayerType.LAMP,
        "sign": LayerType.PANEL,
        "cloud": LayerType.SKY,
        "fog": LayerType.SMOKE,
    }
    if normalized in aliases:
        return aliases[normalized]
    try:
        return LayerType(normalized)
    except ValueError:
        return LayerType.OTHER


def assign_semantic_ids(layers: list[Layer]) -> list[Layer]:
    """Assign ids like ``building_01``, ``tree_02`` per type counter."""
    counters: dict[str, int] = {}
    result: list[Layer] = []
    for layer in layers:
        key = layer.layer_type.value
        counters[key] = counters.get(key, 0) + 1
        idx = counters[key]
        semantic = f"{key}_{idx:02d}"
        result.append(
            layer.model_copy(
                update={
                    "id": semantic,
                    "name": layer.name if layer.name and not layer.name.startswith("Layer") else semantic,
                }
            )
        )
    return result


class InMemoryLayerRepository(LayerRepository):
    """Repository Pattern over an in-memory ordered layer list."""

    def __init__(self, layers: list[Layer] | None = None) -> None:
        self._layers: list[Layer] = list(layers or [])

    def list_layers(self) -> list[Layer]:
        return sorted(self._layers, key=lambda layer: layer.z_index)

    def get_by_id(self, layer_id: str) -> Layer | None:
        for layer in self._layers:
            if layer.id == layer_id:
                return layer
        return None

    def add(self, layer: Layer) -> None:
        self._layers = [item for item in self._layers if item.id != layer.id]
        self._layers.append(layer)

    def remove(self, layer_id: str) -> bool:
        before = len(self._layers)
        self._layers = [layer for layer in self._layers if layer.id != layer_id]
        return len(self._layers) < before

    def update(self, layer: Layer) -> None:
        self.add(layer)

    def replace_all(self, layers: list[Layer]) -> None:
        """Replace the entire collection."""
        self._layers = list(layers)

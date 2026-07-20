"""Undoable layer-edit commands (Command Pattern)."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from src.core.commands import Command
from src.models.bounds import Bounds
from src.models.layer import Layer
from src.models.project import ProjectDocument


class _ProjectMutationCommand(Command):
    """Base helper that swaps project layers through a mutator callback."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        *,
        description: str,
    ) -> None:
        self._get = get_project
        self._set = set_project
        self._description = description
        self._before: list[Layer] | None = None
        self._after: list[Layer] | None = None

    @property
    def description(self) -> str:
        return self._description

    def _snapshot(self) -> list[Layer]:
        return [layer.model_copy(deep=True) for layer in self._get().layers]

    def execute(self) -> None:
        if self._after is not None:
            self._set(self._get().model_copy(update={"layers": self._after}))
            return
        self._before = self._snapshot()
        mutated = self._apply([layer.model_copy(deep=True) for layer in self._before])
        self._after = mutated
        self._set(self._get().model_copy(update={"layers": mutated}))

    def undo(self) -> None:
        if self._before is None:
            return
        self._set(self._get().model_copy(update={"layers": self._before}))

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        raise NotImplementedError


class ToggleVisibilityCommand(_ProjectMutationCommand):
    """Toggle ``visible`` on a layer."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Toggle visibility {layer_id}")
        self._layer_id = layer_id

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        result: list[Layer] = []
        for layer in layers:
            if layer.id == self._layer_id:
                result.append(layer.model_copy(update={"visible": not layer.visible}))
            else:
                result.append(layer)
        return result


class SetColorCommand(_ProjectMutationCommand):
    """Change layer fill color."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
        color: str,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Set color {layer_id}")
        self._layer_id = layer_id
        self._color = color

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        return [
            layer.model_copy(update={"color": self._color})
            if layer.id == self._layer_id
            else layer
            for layer in layers
        ]


class SetOpacityCommand(_ProjectMutationCommand):
    """Change layer opacity (0–1)."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
        opacity: float,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Set opacity {layer_id}")
        self._layer_id = layer_id
        self._opacity = max(0.0, min(1.0, opacity))

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        return [
            layer.model_copy(update={"opacity": self._opacity})
            if layer.id == self._layer_id
            else layer
            for layer in layers
        ]


class MoveLayerCommand(_ProjectMutationCommand):
    """Change z-index by delta (+1 forward / -1 backward)."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
        delta: int,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Move layer {layer_id}")
        self._layer_id = layer_id
        self._delta = delta

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        ordered = sorted(layers, key=lambda item: item.z_index)
        index = next((i for i, layer in enumerate(ordered) if layer.id == self._layer_id), -1)
        if index < 0:
            return layers
        new_index = max(0, min(len(ordered) - 1, index + self._delta))
        if new_index == index:
            return layers
        item = ordered.pop(index)
        ordered.insert(new_index, item)
        return [
            layer.model_copy(update={"z_index": i}) for i, layer in enumerate(ordered)
        ]


class DeleteLayerCommand(_ProjectMutationCommand):
    """Remove a layer from the project."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Delete {layer_id}")
        self._layer_id = layer_id

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        remaining = [layer for layer in layers if layer.id != self._layer_id]
        return [
            layer.model_copy(update={"z_index": i}) for i, layer in enumerate(remaining)
        ]


class DuplicateLayerCommand(_ProjectMutationCommand):
    """Duplicate a layer with a new id and slight offset."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Duplicate {layer_id}")
        self._layer_id = layer_id

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        source = next((layer for layer in layers if layer.id == self._layer_id), None)
        if source is None:
            return layers
        max_z = max((layer.z_index for layer in layers), default=0)
        new_id = f"{source.layer_type.value}_{uuid4().hex[:6]}"
        bounds = source.bounds
        offset = Bounds(
            x=bounds.x + 8,
            y=bounds.y + 8,
            width=bounds.width,
            height=bounds.height,
        )
        clone = source.model_copy(
            deep=True,
            update={
                "id": new_id,
                "name": f"{source.name}_copy",
                "z_index": max_z + 1,
                "bounds": offset,
            },
        )
        return [*layers, clone]


class TranslateLayerCommand(_ProjectMutationCommand):
    """Move a layer's bounds by (dx, dy) in image space."""

    def __init__(
        self,
        get_project: Callable[[], ProjectDocument],
        set_project: Callable[[ProjectDocument], None],
        layer_id: str,
        dx: float,
        dy: float,
    ) -> None:
        super().__init__(get_project, set_project, description=f"Translate {layer_id}")
        self._layer_id = layer_id
        self._dx = dx
        self._dy = dy

    def _apply(self, layers: list[Layer]) -> list[Layer]:
        result: list[Layer] = []
        for layer in layers:
            if layer.id != self._layer_id:
                result.append(layer)
                continue
            b = layer.bounds
            result.append(
                layer.model_copy(
                    update={
                        "bounds": Bounds(
                            x=b.x + self._dx,
                            y=b.y + self._dy,
                            width=b.width,
                            height=b.height,
                        )
                    }
                )
            )
        return result

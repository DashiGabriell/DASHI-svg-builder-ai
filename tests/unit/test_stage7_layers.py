"""Unit tests for Stage 7 interactive layer editing (Command Pattern)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.core.commands import CommandHistory
from src.core.commands.layer_commands import (
    DeleteLayerCommand,
    DuplicateLayerCommand,
    SetColorCommand,
    ToggleVisibilityCommand,
)
from src.core.events import EventBus
from src.models.bounds import Bounds
from src.models.layer import Layer, LayerType
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.services.pipeline_service import PipelineService
from src.ui.controller import AppController


@pytest.fixture()
def layered_project() -> ProjectDocument:
    return ProjectDocument(
        name="edit",
        width=100,
        height=80,
        stage=PipelineStage.LAYERS_SEPARATED,
        original_image_path=Path("dummy.png"),
        layers=[
            Layer(
                id="building_01",
                layer_type=LayerType.BUILDING,
                color="#111111",
                opacity=1.0,
                visible=True,
                z_index=0,
                bounds=Bounds(x=10, y=10, width=30, height=40),
                path_data="M10,10 L40,10 L40,50 L10,50 Z",
            ),
            Layer(
                id="tree_01",
                layer_type=LayerType.TREE,
                color="#228822",
                opacity=0.8,
                visible=True,
                z_index=1,
                bounds=Bounds(x=50, y=20, width=20, height=30),
                path_data="M50,20 L70,20 L60,50 Z",
            ),
        ],
    )


@pytest.mark.unit
def test_toggle_visibility_command(layered_project: ProjectDocument) -> None:
    box = {"project": layered_project}

    def get_p() -> ProjectDocument:
        return box["project"]

    def set_p(project: ProjectDocument) -> None:
        box["project"] = project

    history = CommandHistory()
    history.execute(ToggleVisibilityCommand(get_p, set_p, "building_01"))
    assert box["project"].get_layer("building_01") is not None
    assert box["project"].get_layer("building_01").visible is False  # type: ignore[union-attr]
    history.undo()
    assert box["project"].get_layer("building_01").visible is True  # type: ignore[union-attr]


@pytest.mark.unit
def test_set_color_and_duplicate(layered_project: ProjectDocument) -> None:
    box = {"project": layered_project}

    def get_p() -> ProjectDocument:
        return box["project"]

    def set_p(project: ProjectDocument) -> None:
        box["project"] = project

    history = CommandHistory()
    history.execute(SetColorCommand(get_p, set_p, "tree_01", "#00ffaa"))
    assert box["project"].get_layer("tree_01").color == "#00ffaa"  # type: ignore[union-attr]
    history.execute(DuplicateLayerCommand(get_p, set_p, "tree_01"))
    assert len(box["project"].layers) == 3
    history.execute(DeleteLayerCommand(get_p, set_p, "building_01"))
    assert box["project"].get_layer("building_01") is None
    history.undo()
    assert box["project"].get_layer("building_01") is not None


@pytest.mark.unit
def test_controller_layer_edits(tmp_path: Path) -> None:
    import src.processors  # noqa: F401

    img = Image.new("RGBA", (80, 60), (255, 255, 255, 255))
    px = img.load()
    assert px is not None
    for y in range(10, 40):
        for x in range(15, 50):
            px[x, y] = (200, 40, 40, 255)
    source = tmp_path / "edit.png"
    img.save(source)

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    controller = AppController(
        EventBus(), pipeline=pipeline, history=CommandHistory()
    )
    controller.import_image(source)
    # Bypass CV: inject layers directly for speed
    controller.state.project = controller.state.project.model_copy(
        update={
            "layers": [
                Layer(
                    id="other_01",
                    layer_type=LayerType.OTHER,
                    color="#aaaaaa",
                    bounds=Bounds(x=15, y=10, width=35, height=30),
                    path_data="M15,10 L50,10 L50,40 L15,40 Z",
                    z_index=0,
                )
            ],
            "stage": PipelineStage.LAYERS_SEPARATED,
            "width": 80,
            "height": 60,
        }
    )

    controller.select_layer("other_01")
    assert controller.state.selected_layer_id == "other_01"
    controller.set_layer_color("other_01", "#ff0000")
    assert controller.state.project.get_layer("other_01").color == "#ff0000"  # type: ignore[union-attr]
    controller.set_layer_opacity("other_01", 0.5)
    assert controller.state.project.get_layer("other_01").opacity == 0.5  # type: ignore[union-attr]
    controller.toggle_layer_visibility("other_01")
    assert controller.state.project.get_layer("other_01").visible is False  # type: ignore[union-attr]
    controller.duplicate_layer("other_01")
    assert len(controller.state.project.layers) == 2
    controller.undo()
    assert len(controller.state.project.layers) == 1
    controller.redo()
    assert len(controller.state.project.layers) == 2
    lid = controller.state.project.layers[0].id
    layer_before = controller.state.project.get_layer(lid)
    assert layer_before is not None
    bx, by = layer_before.bounds.x, layer_before.bounds.y
    controller.translate_layer(lid, 5, -3)
    layer_after = controller.state.project.get_layer(lid)
    assert layer_after is not None
    assert layer_after.bounds.x == bx + 5
    assert layer_after.bounds.y == by - 3

"""Unit tests for Stage 4 object detection and layer separation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.core.events import EventBus
from src.models.layer import Layer, LayerType
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.services.layer_repository import (
    InMemoryLayerRepository,
    assign_semantic_ids,
    parse_layer_type,
)
from src.services.pipeline_service import PipelineService
from src.ui.controller import AppController
from src.utils.background import remove_background
from src.utils.segmentation import detect_objects


@pytest.fixture()
def two_blobs_png(tmp_path: Path) -> Path:
    """White canvas with two separated colored squares."""
    img = Image.new("RGBA", (120, 80), (255, 255, 255, 255))
    px = img.load()
    assert px is not None
    for y in range(10, 40):
        for x in range(10, 40):
            px[x, y] = (200, 40, 40, 255)
    for y in range(15, 55):
        for x in range(70, 105):
            px[x, y] = (40, 80, 200, 255)
    path = tmp_path / "two_blobs.png"
    img.save(path)
    return path


@pytest.mark.unit
def test_detect_objects_finds_two_contours(two_blobs_png: Path) -> None:
    rgba = np.asarray(Image.open(two_blobs_png).convert("RGBA"))
    cut = remove_background(rgba, method="flood_fill", tolerance=25)
    objects = detect_objects(cut, method="contours", min_area=50)
    assert len(objects) >= 2


@pytest.mark.unit
def test_parse_layer_type_aliases() -> None:
    assert parse_layer_type("Building") == LayerType.BUILDING
    assert parse_layer_type("car") == LayerType.VEHICLE
    assert parse_layer_type("weird_thing") == LayerType.OTHER


@pytest.mark.unit
def test_assign_semantic_ids() -> None:
    layers = [
        Layer(layer_type=LayerType.BUILDING),
        Layer(layer_type=LayerType.TREE),
        Layer(layer_type=LayerType.BUILDING),
    ]
    named = assign_semantic_ids(layers)
    assert named[0].id == "building_01"
    assert named[1].id == "tree_01"
    assert named[2].id == "building_02"


@pytest.mark.unit
def test_layer_repository() -> None:
    repo = InMemoryLayerRepository()
    layer = Layer(id="road_01", layer_type=LayerType.ROAD, z_index=1)
    repo.add(layer)
    assert repo.get_by_id("road_01") is not None
    assert repo.remove("road_01") is True
    assert repo.get_by_id("road_01") is None


@pytest.mark.unit
def test_pipeline_detect_and_separate(two_blobs_png: Path, tmp_path: Path) -> None:
    import src.processors  # noqa: F401

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    project = ProjectDocument(
        name="blobs",
        source_path=two_blobs_png,
        original_image_path=two_blobs_png,
        stage=PipelineStage.LOADED,
        width=120,
        height=80,
    )
    project = pipeline.normalize_loaded(project)
    project = pipeline.run("remove_background", project)
    project = pipeline.run("detect_objects", project, min_area=50)
    assert project.stage == PipelineStage.OBJECTS_DETECTED
    assert project.metadata.get("detection_count", 0) >= 2

    project = pipeline.run("separate_layers", project, min_area=50)
    assert project.stage == PipelineStage.LAYERS_SEPARATED
    assert len(project.layers) >= 2
    assert all(layer.id for layer in project.layers)
    assert all(layer.source_mask_path for layer in project.layers)
    # Semantic ids with type prefix
    assert all("_" in layer.id for layer in project.layers)


@pytest.mark.unit
def test_controller_separate_layers(two_blobs_png: Path, tmp_path: Path) -> None:
    import src.processors  # noqa: F401

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    controller = AppController(EventBus(), pipeline=pipeline)
    controller.import_image(two_blobs_png)
    controller.run_action("remove_background")
    controller.run_action("detect_objects", min_area=50)
    controller.run_action("separate_layers", min_area=50)
    assert controller.state.project.stage == PipelineStage.LAYERS_SEPARATED
    assert len(controller.state.project.layers) >= 2

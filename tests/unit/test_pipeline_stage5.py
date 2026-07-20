"""Unit tests for Stage 5 per-layer Potrace vectorization."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.core.events import EventBus
from src.models.layer import Layer, LayerType
from src.models.bounds import Bounds
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.services.pipeline_service import PipelineService
from src.ui.controller import AppController
from src.utils.potrace_trace import trace_mask_to_path
from src.utils.svg_builder import build_svg_document


@pytest.mark.unit
def test_trace_mask_produces_path() -> None:
    mask = np.zeros((80, 100), dtype=np.uint8)
    mask[20:60, 25:75] = 255
    result = trace_mask_to_path(mask)
    assert result.empty is False
    assert result.path_d.startswith("M")
    assert "Z" in result.path_d
    assert result.curve_count >= 1


@pytest.mark.unit
def test_trace_empty_mask() -> None:
    mask = np.zeros((40, 40), dtype=np.uint8)
    result = trace_mask_to_path(mask)
    assert result.empty is True
    assert result.path_d == ""


@pytest.mark.unit
def test_build_svg_has_per_layer_groups() -> None:
    project = ProjectDocument(name="t", width=100, height=80, stage=PipelineStage.VECTORIZED)
    layers = [
        Layer(
            id="building_01",
            layer_type=LayerType.BUILDING,
            color="#202020",
            path_data="M10,10 L40,10 L40,40 L10,40 Z",
            z_index=0,
        ),
        Layer(
            id="tree_01",
            layer_type=LayerType.TREE,
            color="#228822",
            path_data="M60,20 L80,20 L70,50 Z",
            z_index=1,
        ),
    ]
    svg = build_svg_document(project, layers)
    assert 'id="building_01"' in svg
    assert 'id="tree_01"' in svg
    assert "<path" in svg
    # Must be two independent groups, not one mega-path
    assert svg.count("<g ") + svg.count("<g>") >= 2


@pytest.mark.unit
def test_pipeline_vectorize(tmp_path: Path) -> None:
    import src.processors  # noqa: F401

    # Build a simple RGBA with two blobs, then run pipeline through vectorize
    img = Image.new("RGBA", (120, 80), (255, 255, 255, 255))
    px = img.load()
    assert px is not None
    for y in range(10, 40):
        for x in range(10, 40):
            px[x, y] = (180, 40, 40, 255)
    for y in range(20, 55):
        for x in range(70, 105):
            px[x, y] = (40, 100, 180, 255)
    source = tmp_path / "art.png"
    img.save(source)

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    project = ProjectDocument(
        name="art",
        source_path=source,
        original_image_path=source,
        stage=PipelineStage.LOADED,
        width=120,
        height=80,
    )
    project = pipeline.normalize_loaded(project)
    project = pipeline.run("remove_background", project)
    project = pipeline.run("detect_objects", project, min_area=50)
    project = pipeline.run("separate_layers", project, min_area=50)
    project = pipeline.run("vectorize", project)

    assert project.stage == PipelineStage.VECTORIZED
    assert project.svg_content
    assert project.metadata.get("vectorized_layers", 0) >= 1
    assert "<g" in project.svg_content
    for layer in project.layers:
        if layer.metadata.get("vectorized"):
            assert layer.path_data.startswith("M")
            assert f'id="{layer.id}"' in project.svg_content

    svg_path = Path(str(project.metadata["svg_path"]))
    assert svg_path.exists()


@pytest.mark.unit
def test_controller_vectorize(tmp_path: Path) -> None:
    import src.processors  # noqa: F401

    img = Image.new("RGBA", (60, 60), (255, 255, 255, 255))
    px = img.load()
    assert px is not None
    for y in range(15, 45):
        for x in range(15, 45):
            px[x, y] = (30, 30, 30, 255)
    path = tmp_path / "one.png"
    img.save(path)

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    controller = AppController(EventBus(), pipeline=pipeline)
    controller.import_image(path)
    controller.run_action("remove_background")
    controller.run_action("detect_objects", min_area=40)
    controller.run_action("separate_layers", min_area=40)
    controller.run_action("vectorize")
    assert controller.state.project.stage == PipelineStage.VECTORIZED
    assert controller.state.project.svg_content

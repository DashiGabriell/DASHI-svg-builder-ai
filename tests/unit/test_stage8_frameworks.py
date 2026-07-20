"""Unit tests for Stage 8 framework exporters and animations."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.exports.animation import AnimationOptions, AnimationPreset, build_animated_svg
from src.exports.base import ExportFormat
from src.exports.codegen import layer_component_name, to_pascal_case
from src.exports.export_service import ExportService
from src.models.bounds import Bounds
from src.models.layer import Layer, LayerType
from src.models.project import PipelineStage, ProjectDocument
from src.utils.svg_builder import build_svg_document


@pytest.fixture()
def sample_project() -> ProjectDocument:
    layers = [
        Layer(
            id="building_01",
            layer_type=LayerType.BUILDING,
            color="#202020",
            path_data="M10,10 L40,10 L40,40 L10,40 Z",
            bounds=Bounds(x=10, y=10, width=30, height=30),
            z_index=0,
        ),
        Layer(
            id="tree_01",
            layer_type=LayerType.TREE,
            color="#228822",
            path_data="M50,20 L70,20 L60,50 Z",
            bounds=Bounds(x=50, y=20, width=20, height=30),
            z_index=1,
        ),
    ]
    project = ProjectDocument(
        name="SceneDemo",
        width=100,
        height=80,
        stage=PipelineStage.VECTORIZED,
        layers=layers,
    )
    project = project.model_copy(
        update={"svg_content": build_svg_document(project, pretty=False)}
    )
    return project


@pytest.mark.unit
def test_pascal_component_names() -> None:
    assert to_pascal_case("building_01") == "Building01"
    assert layer_component_name(
        Layer(id="road_02", layer_type=LayerType.ROAD)
    ) == "Road02"


@pytest.mark.unit
def test_animated_svg_contains_animation(sample_project: ProjectDocument) -> None:
    svg = build_animated_svg(
        sample_project,
        options=AnimationOptions(preset=AnimationPreset.FADE_IN),
    )
    assert "fadeIn" in svg or "animate" in svg
    assert "building_01" in svg


@pytest.mark.unit
def test_export_react_tsx(sample_project: ProjectDocument, tmp_path: Path) -> None:
    service = ExportService(exports_dir=tmp_path)
    path = service.export(sample_project, ExportFormat.REACT, tmp_path / "Scene.tsx")
    text = path.read_text(encoding="utf-8")
    assert "export function Building01" in text
    assert "export function Tree01" in text
    assert "<Building01 />" in text
    assert "<Tree01 />" in text
    assert "export function Scene" in text


@pytest.mark.unit
def test_export_all_frameworks(sample_project: ProjectDocument, tmp_path: Path) -> None:
    service = ExportService(exports_dir=tmp_path)
    expectations = {
        ExportFormat.VUE: (".vue", "building_01"),
        ExportFormat.ANGULAR: (".ts", "SvgSceneComponent"),
        ExportFormat.FLUTTER: (".dart", "SvgScenePainter"),
        ExportFormat.GODOT: (".gd", "Polygon2D"),
        ExportFormat.UNITY: (".cs", "SvgSceneBehaviour"),
        ExportFormat.SVG_ANIMATED: (".svg", "layer-anim"),
    }
    for fmt, (ext, needle) in expectations.items():
        out = tmp_path / f"out_{fmt.value}{ext}"
        path = service.export(sample_project, fmt, out)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert needle in content

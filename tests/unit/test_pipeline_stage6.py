"""Unit tests for Stage 6 optimize + export."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from src.core.events import EventBus
from src.exports.base import ExportFormat
from src.exports.export_service import ExportService
from src.models.project import PipelineStage
from src.processors.base.plugin_registry import get_plugin_registry
from src.services.pipeline_service import PipelineService
from src.ui.controller import AppController
from src.utils.svg_optimizer import optimize_svg, simplify_path_d


@pytest.mark.unit
def test_simplify_path_rounds_decimals() -> None:
    d = "M10.12345,20.98765 L30.1,40.999 Z"
    out = simplify_path_d(d, precision=2)
    assert "10.12" in out or "10.123" not in out
    assert "20.99" in out or "20.98765" not in out


@pytest.mark.unit
def test_optimize_svg_removes_empty_and_duplicates() -> None:
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
      <g id="a"><path d="M0,0 L10,0 L10,10 Z" fill="#111"/></g>
      <g id="b"><path d="M0,0 L10,0 L10,10 Z" fill="#111"/></g>
      <g id="empty"></g>
      <g id="blank"><path d="" fill="#000"/></g>
    </svg>
    """
    result = optimize_svg(svg, precision=2, minify=True)
    assert result.stats.duplicate_paths_removed >= 1
    assert result.stats.empty_groups_removed >= 1
    assert result.stats.bytes_after <= result.stats.bytes_before


@pytest.fixture()
def vectorized_controller(tmp_path: Path) -> AppController:
    import src.processors  # noqa: F401

    img = Image.new("RGBA", (80, 60), (255, 255, 255, 255))
    px = img.load()
    assert px is not None
    for y in range(10, 40):
        for x in range(15, 45):
            px[x, y] = (40, 40, 180, 255)
    source = tmp_path / "box.png"
    img.save(source)

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    exports = ExportService(exports_dir=tmp_path / "exports")
    controller = AppController(EventBus(), pipeline=pipeline, export_service=exports)
    controller.import_image(source)
    controller.run_action("remove_background")
    controller.run_action("detect_objects", min_area=40)
    controller.run_action("separate_layers", min_area=40)
    controller.run_action("vectorize")
    return controller


@pytest.mark.unit
def test_optimize_pipeline(vectorized_controller: AppController) -> None:
    vectorized_controller.run_action("optimize_svg")
    project = vectorized_controller.state.project
    assert project.stage == PipelineStage.OPTIMIZED
    assert project.svg_content
    assert "optimize_stats" in project.metadata


@pytest.mark.unit
def test_export_json(vectorized_controller: AppController, tmp_path: Path) -> None:
    out = tmp_path / "layers.json"
    path = vectorized_controller.export_project(ExportFormat.JSON, out)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "layers" in data
    assert isinstance(data["layers"], list)
    assert data["layers"]
    assert "id" in data["layers"][0]
    assert "path" in data["layers"][0]
    assert vectorized_controller.state.project.stage == PipelineStage.EXPORTED


@pytest.mark.unit
def test_export_svg_and_png(vectorized_controller: AppController, tmp_path: Path) -> None:
    svg_path = vectorized_controller.export_project(
        ExportFormat.SVG, tmp_path / "out.svg"
    )
    assert svg_path.exists()
    assert "<svg" in svg_path.read_text(encoding="utf-8")

    opt = vectorized_controller.export_project(
        ExportFormat.SVG_OPTIMIZED, tmp_path / "out.min.svg"
    )
    assert opt.exists()

    png = vectorized_controller.export_project(ExportFormat.PNG, tmp_path / "out.png")
    assert png.exists()
    with Image.open(png) as img:
        assert img.size[0] > 0

    webp = vectorized_controller.export_project(ExportFormat.WEBP, tmp_path / "out.webp")
    assert webp.exists()

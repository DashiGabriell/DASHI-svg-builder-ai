"""Unit tests for Stage 3 raster utilities and processors."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from src.core.events import EventBus
from src.models.project import PipelineStage, ProjectDocument
from src.processors.base.plugin_registry import get_plugin_registry
from src.services.pipeline_service import PipelineService
from src.ui.controller import AppController
from src.utils.background import remove_background
from src.utils.super_resolution import upscale_image


@pytest.fixture()
def solid_subject_png(tmp_path: Path) -> Path:
    """White background with a dark red square in the center."""
    img = Image.new("RGB", (100, 80), color=(255, 255, 255))
    pixels = img.load()
    assert pixels is not None
    for y in range(20, 60):
        for x in range(25, 75):
            pixels[x, y] = (180, 30, 30)
    path = tmp_path / "subject.png"
    img.save(path)
    return path


@pytest.mark.unit
def test_upscale_doubles_resolution() -> None:
    rgba = np.zeros((40, 50, 4), dtype=np.uint8)
    rgba[:, :, :3] = 90
    rgba[:, :, 3] = 255
    out = upscale_image(rgba, scale=2.0, sharpen=True)
    assert out.shape[0] == 80
    assert out.shape[1] == 100
    assert out.shape[2] == 4


@pytest.mark.unit
def test_flood_fill_makes_corners_transparent(solid_subject_png: Path) -> None:
    rgba = np.asarray(Image.open(solid_subject_png).convert("RGBA"))
    cut = remove_background(rgba, method="flood_fill", tolerance=30)
    # Corners should be transparent
    assert cut[0, 0, 3] < 20
    assert cut[-1, -1, 3] < 20
    # Center of subject should stay opaque
    assert cut[40, 50, 3] > 200


@pytest.mark.unit
def test_pipeline_enhance_and_remove_background(
    solid_subject_png: Path, tmp_path: Path
) -> None:
    # Ensure processors are registered
    import src.processors  # noqa: F401

    registry = get_plugin_registry()
    assert "enhance_quality" in registry.available()
    assert "remove_background" in registry.available()

    pipeline = PipelineService(registry, cache_dir=tmp_path / "cache", ai_service=None)
    project = ProjectDocument(
        name="t",
        source_path=solid_subject_png,
        original_image_path=solid_subject_png,
        stage=PipelineStage.LOADED,
        width=100,
        height=80,
    )
    project = pipeline.normalize_loaded(project)
    assert project.stage == PipelineStage.LOADED
    assert project.processed_image_path is not None

    project = pipeline.run("enhance_quality", project, scale=2.0)
    assert project.stage == PipelineStage.UPSCALE
    assert project.width == 200
    assert project.height == 160
    assert project.processed_image_path is not None
    assert project.processed_image_path.exists()

    project = pipeline.run("remove_background", project, method="flood_fill")
    assert project.stage == PipelineStage.BACKGROUND_REMOVED
    assert project.processed_image_path is not None
    out = np.asarray(Image.open(project.processed_image_path).convert("RGBA"))
    assert out[0, 0, 3] < 30


@pytest.mark.unit
def test_controller_runs_enhance_quality(solid_subject_png: Path, tmp_path: Path) -> None:
    import src.processors  # noqa: F401

    pipeline = PipelineService(
        get_plugin_registry(), cache_dir=tmp_path / "cache", ai_service=None
    )
    controller = AppController(EventBus(), pipeline=pipeline)
    controller.import_image(solid_subject_png)
    controller.run_action("enhance_quality", scale=2.0)
    assert controller.state.project.stage == PipelineStage.UPSCALE
    assert controller.state.project.processed_image_path is not None


@pytest.mark.unit
def test_grabcut_method_runs(solid_subject_png: Path) -> None:
    rgba = np.asarray(Image.open(solid_subject_png).convert("RGBA"))
    cut = remove_background(rgba, method="grabcut")
    assert cut.shape == rgba.shape
    assert cut[:, :, 3].max() > 0

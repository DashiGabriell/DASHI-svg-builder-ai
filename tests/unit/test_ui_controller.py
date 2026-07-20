"""Unit tests for AppController (no GUI)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from src.core.events import EventBus
from src.models.project import PipelineStage
from src.ui import events as ui_events
from src.ui.controller import AppController


@pytest.fixture()
def controller() -> AppController:
    return AppController(EventBus())


@pytest.fixture()
def sample_png(tmp_path: Path) -> Path:
    path = tmp_path / "art.png"
    Image.new("RGB", (64, 48), color=(20, 40, 60)).save(path)
    return path


@pytest.mark.unit
def test_import_image_loads_project(controller: AppController, sample_png: Path) -> None:
    seen: list[str] = []
    controller._bus.subscribe(ui_events.PREVIEW_ORIGINAL, lambda e: seen.append(e.name))

    project = controller.import_image(sample_png)

    assert project.stage == PipelineStage.LOADED
    assert project.width == 64
    assert project.height == 48
    assert project.original_image_path == sample_png.resolve()
    assert controller.state.has_image is True
    assert ui_events.PREVIEW_ORIGINAL in seen


@pytest.mark.unit
def test_import_rejects_missing_file(controller: AppController, tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        controller.import_image(tmp_path / "missing.png")


@pytest.mark.unit
def test_import_rejects_unsupported_extension(
    controller: AppController, tmp_path: Path
) -> None:
    bad = tmp_path / "notes.txt"
    bad.write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="não suportado"):
        controller.import_image(bad)


@pytest.mark.unit
def test_export_action_prompts_for_format(controller: AppController) -> None:
    messages: list[str] = []
    controller._bus.subscribe(
        ui_events.STATUS_MESSAGE, lambda e: messages.append(str(e.payload["message"]))
    )
    controller.run_action("export")
    assert any("formato" in m.lower() for m in messages)


@pytest.mark.unit
def test_sidebar_actions_cover_pipeline() -> None:
    from src.ui.components.sidebar import PIPELINE_ACTIONS

    ids = {a.action_id for a in PIPELINE_ACTIONS}
    assert {
        "import",
        "remove_background",
        "enhance_quality",
        "detect_objects",
        "separate_layers",
        "vectorize",
        "optimize_svg",
        "export",
    } <= ids

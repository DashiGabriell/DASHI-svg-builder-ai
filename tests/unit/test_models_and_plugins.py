"""Unit tests for domain models and event bus."""

from __future__ import annotations

import pytest

from src.core.events import Event, EventBus
from src.models.layer import Layer, LayerType
from src.models.project import PipelineStage, ProjectDocument
from src.processors import PluginRegistry


@pytest.mark.unit
def test_layer_semantic_id() -> None:
    layer = Layer(layer_type=LayerType.BUILDING, name="Tower")
    renamed = layer.with_semantic_id(1)
    assert renamed.id == "building_01"


@pytest.mark.unit
def test_project_layers_json() -> None:
    project = ProjectDocument(
        name="Demo",
        width=100,
        height=80,
        stage=PipelineStage.LAYERS_SEPARATED,
        layers=[
            Layer(id="road_01", layer_type=LayerType.ROAD, color="#333333"),
        ],
    )
    payload = project.to_layers_json()
    assert payload["layers"][0]["id"] == "road_01"
    assert payload["layers"][0]["type"] == "road"


@pytest.mark.unit
def test_event_bus_publishes() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("layer.updated", lambda e: seen.append(e.name))
    bus.publish(Event(name="layer.updated", payload={"id": "building_01"}))
    assert seen == ["layer.updated"]


@pytest.mark.unit
def test_plugin_registry_register_and_create() -> None:
    from src.core.interfaces import Processor
    from src.models.project import ProjectDocument

    registry = PluginRegistry()

    class DummyProcessor(Processor):
        @property
        def name(self) -> str:
            return "dummy"

        def process(self, project: ProjectDocument, **kwargs):
            return project

    registry.register_factory("dummy", DummyProcessor)
    assert registry.available() == ["dummy"]
    assert registry.create("dummy").name == "dummy"

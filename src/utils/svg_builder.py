"""Assemble modular SVG documents from per-layer path data."""

from __future__ import annotations

import logging
from xml.etree import ElementTree as ET

import svgwrite
from svgwrite import Drawing

from src.models.layer import Layer
from src.models.project import ProjectDocument

logger = logging.getLogger(__name__)


def build_svg_document(
    project: ProjectDocument,
    layers: list[Layer] | None = None,
    *,
    pretty: bool = True,
) -> str:
    """Build an SVG string with one ``<g id="...">`` per visible layer.

    Never collapses the artwork into a single path — each layer is an
    independent group containing its own ``<path>`` elements.
    """
    items = layers if layers is not None else project.layers
    width = max(1, project.width)
    height = max(1, project.height)

    drawing = Drawing(
        size=(f"{width}px", f"{height}px"),
        viewBox=f"0 0 {width} {height}",
        profile="full",
        debug=False,
    )

    root_group = drawing.g(id="svg_builder_root")
    drawing.add(root_group)

    for layer in sorted(items, key=lambda item: item.z_index):
        if not layer.visible:
            continue
        if not layer.path_data.strip():
            logger.debug("Skipping empty path layer %s", layer.id)
            continue

        group = drawing.g(id=layer.id, opacity=layer.opacity)
        group["data-type"] = layer.layer_type.value
        if layer.name:
            group["data-name"] = layer.name

        path = drawing.path(
            d=layer.path_data,
            fill=layer.color or "#000000",
            stroke="none",
            fill_rule="evenodd",
        )
        group.add(path)
        root_group.add(group)
        layer.svg_group = _group_snippet(layer)

    svg_text = drawing.tostring()
    if pretty:
        svg_text = _pretty_xml(svg_text)
    logger.info("SVG built with %d layer group(s)", sum(1 for L in items if L.visible and L.path_data))
    return svg_text


def _group_snippet(layer: Layer) -> str:
    """Produce a standalone ``<g>`` fragment for the layer."""
    return (
        f'<g id="{layer.id}" data-type="{layer.layer_type.value}" '
        f'opacity="{layer.opacity}">'
        f'<path d="{layer.path_data}" fill="{layer.color}" stroke="none" '
        f'fill-rule="evenodd"/>'
        f"</g>"
    )


def _pretty_xml(svg_text: str) -> str:
    """Pretty-print SVG XML without ``ns0:`` prefixes."""
    try:
        ET.register_namespace("", "http://www.w3.org/2000/svg")
        element = ET.fromstring(svg_text)
        ET.indent(element, space="  ")
        return ET.tostring(element, encoding="unicode")
    except ET.ParseError:
        return svg_text


def save_svg(path: str, svg_content: str) -> None:
    """Write SVG text to disk (UTF-8)."""
    from pathlib import Path

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(svg_content, encoding="utf-8")

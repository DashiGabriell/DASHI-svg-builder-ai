"""SVG animation helpers (SMIL + CSS) — foundation for Stage 8+ motion."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from xml.etree import ElementTree as ET

from src.models.project import ProjectDocument
from src.utils.svg_builder import build_svg_document


class AnimationPreset(StrEnum):
    """Built-in animation presets applied per visible layer."""

    NONE = "none"
    FADE_IN = "fade_in"
    PULSE = "pulse"
    DRAW = "draw"  # stroke-dasharray reveal when stroke present


@dataclass(frozen=True, slots=True)
class AnimationOptions:
    """Options for animated SVG export."""

    preset: AnimationPreset = AnimationPreset.FADE_IN
    duration_seconds: float = 0.8
    stagger_seconds: float = 0.12


def build_animated_svg(
    project: ProjectDocument,
    *,
    options: AnimationOptions | None = None,
) -> str:
    """Build an SVG string with CSS/SMIL animations on each layer group.

    Vectorization remains the offline source of truth; animation is a
    presentation layer added at export time.
    """
    opts = options or AnimationOptions()
    base = project.svg_content or build_svg_document(project, pretty=False)
    if opts.preset == AnimationPreset.NONE or not base.strip():
        return base

    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.fromstring(base)

    style = ET.Element("style")
    style.text = _css_for_preset(opts)
    # Insert style as first child
    root.insert(0, style)

    index = 0
    for group in root.iter():
        tag = group.tag.rsplit("}", 1)[-1] if "}" in group.tag else group.tag
        if tag != "g":
            continue
        gid = group.get("id") or ""
        if gid in {"", "svg_builder_root"}:
            continue
        delay = index * opts.stagger_seconds
        group.set("class", f"layer-anim delay-{index}")
        group.set("style", f"animation-delay:{delay:.2f}s")
        if opts.preset == AnimationPreset.FADE_IN:
            # SMIL fallback for broader SVG viewers
            animate = ET.SubElement(
                group,
                "animate",
                attrib={
                    "attributeName": "opacity",
                    "from": "0",
                    "to": str(group.get("opacity") or "1"),
                    "dur": f"{opts.duration_seconds:.2f}s",
                    "begin": f"{delay:.2f}s",
                    "fill": "freeze",
                },
            )
            _ = animate
        index += 1

    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode")


def _css_for_preset(opts: AnimationOptions) -> str:
    dur = f"{opts.duration_seconds:.2f}s"
    if opts.preset == AnimationPreset.PULSE:
        return (
            ".layer-anim{transform-origin:center;animation:pulse "
            f"{dur} ease-in-out infinite alternate;}}"
            "@keyframes pulse{from{opacity:.55}to{opacity:1}}"
        )
    if opts.preset == AnimationPreset.DRAW:
        return (
            ".layer-anim path{stroke-dasharray:1000;stroke-dashoffset:1000;"
            f"animation:draw {dur} ease forwards;}}"
            "@keyframes draw{to{stroke-dashoffset:0}}"
        )
    # fade_in default
    return (
        ".layer-anim{opacity:0;animation:fadeIn "
        f"{dur} ease forwards;}}"
        "@keyframes fadeIn{to{opacity:1}}"
    )

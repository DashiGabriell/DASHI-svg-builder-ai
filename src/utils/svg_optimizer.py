"""SVG optimization: simplify paths, drop empties/duplicates, compress."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from xml.etree import ElementTree as ET

logger = logging.getLogger(__name__)

_NUM = re.compile(r"[-+]?(?:\d+\.\d+|\d+\.|\.\d+|\d+)(?:[eE][-+]?\d+)?")
_SVG_NS = "http://www.w3.org/2000/svg"


@dataclass(frozen=True, slots=True)
class OptimizeStats:
    """Counters describing what the optimizer changed."""

    path_nodes_before: int
    path_nodes_after: int
    empty_groups_removed: int
    duplicate_paths_removed: int
    bytes_before: int
    bytes_after: int

    @property
    def node_reduction_ratio(self) -> float:
        if self.path_nodes_before <= 0:
            return 0.0
        return 1.0 - (self.path_nodes_after / self.path_nodes_before)


@dataclass(frozen=True, slots=True)
class OptimizeResult:
    """Optimized SVG payload + stats."""

    svg: str
    stats: OptimizeStats


def optimize_svg(
    svg_content: str,
    *,
    precision: int = 2,
    minify: bool = True,
    remove_duplicates: bool = True,
) -> OptimizeResult:
    """Optimize an SVG document string.

    Operations:
        * Round path coordinates to ``precision`` decimals (fewer nodes/noise)
        * Remove empty ``<g>`` / empty ``<path d="">``
        * Drop duplicate paths (same ``d`` + fill)
        * Optionally minify whitespace
    """
    bytes_before = len(svg_content.encode("utf-8"))
    nodes_before = _count_path_numbers(svg_content)

    ET.register_namespace("", _SVG_NS)
    root = ET.fromstring(svg_content)

    empty_removed = 0
    dup_removed = 0
    seen_paths: set[tuple[str, str]] = set()

    # Work on a flat list of parents to safely remove children
    for parent in list(root.iter()):
        for child in list(parent):
            tag = _local(child.tag)
            if tag == "path":
                d = (child.get("d") or "").strip()
                if not d:
                    parent.remove(child)
                    empty_removed += 1
                    continue
                simplified = simplify_path_d(d, precision=precision)
                child.set("d", simplified)
                fill = (child.get("fill") or "").strip().lower()
                key = (simplified, fill)
                if remove_duplicates and key in seen_paths:
                    parent.remove(child)
                    dup_removed += 1
                else:
                    seen_paths.add(key)

    empty_removed += _remove_empty_groups(root)

    if minify:
        _strip_whitespace(root)
        svg_out = ET.tostring(root, encoding="unicode")
    else:
        ET.indent(root, space="  ")
        svg_out = ET.tostring(root, encoding="unicode")

    nodes_after = _count_path_numbers(svg_out)
    bytes_after = len(svg_out.encode("utf-8"))
    stats = OptimizeStats(
        path_nodes_before=nodes_before,
        path_nodes_after=nodes_after,
        empty_groups_removed=empty_removed,
        duplicate_paths_removed=dup_removed,
        bytes_before=bytes_before,
        bytes_after=bytes_after,
    )
    logger.info(
        "SVG optimized: nodes %d→%d, bytes %d→%d, empty=%d, dups=%d",
        nodes_before,
        nodes_after,
        bytes_before,
        bytes_after,
        empty_removed,
        dup_removed,
    )
    return OptimizeResult(svg=svg_out, stats=stats)


def simplify_path_d(path_d: str, *, precision: int = 2) -> str:
    """Round numeric tokens in a path ``d`` attribute and compress spaces."""

    def _round(match: re.Match[str]) -> str:
        value = float(match.group(0))
        rounded = round(value, precision)
        if rounded == int(rounded):
            return str(int(rounded))
        text = f"{rounded:.{precision}f}".rstrip("0").rstrip(".")
        return text or "0"

    simplified = _NUM.sub(_round, path_d)
    simplified = re.sub(r"\s+", " ", simplified).strip()
    simplified = re.sub(r"\s*,\s*", ",", simplified)
    # Remove spaces between command letters and numbers where safe
    simplified = re.sub(r"([MmLlHhVvCcSsQqTtAaZz])\s+", r"\1", simplified)
    simplified = re.sub(r"\s+([MmLlHhVvCcSsQqTtAaZz])", r"\1", simplified)
    return simplified


def optimize_layer_paths(
    path_data: str,
    *,
    precision: int = 2,
) -> str:
    """Optimize a single layer path string."""
    if not path_data.strip():
        return ""
    return simplify_path_d(path_data, precision=precision)


def _count_path_numbers(svg_or_d: str) -> int:
    return len(_NUM.findall(svg_or_d))


def _local(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", 1)[-1]
    return tag


def _remove_empty_groups(root: ET.Element) -> int:
    """Recursively remove empty ``<g>`` elements. Returns count removed."""
    removed = 0
    changed = True
    while changed:
        changed = False
        for parent in list(root.iter()):
            for child in list(parent):
                if _local(child.tag) != "g":
                    continue
                # empty or only whitespace text
                if len(child) == 0 and not (child.text and child.text.strip()):
                    parent.remove(child)
                    removed += 1
                    changed = True
    return removed


def _strip_whitespace(element: ET.Element) -> None:
    element.text = None if element.text is None else element.text.strip() or None
    element.tail = None if element.tail is None else element.tail.strip() or None
    for child in element:
        _strip_whitespace(child)

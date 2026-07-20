"""Potrace-based bitmap tracing (per-layer silhouettes).

Uses ``potracer`` (pure-Python port of Peter Selinger's Potrace). The
legacy ``potrace`` / ``pypotrace`` wheels are unavailable on many modern
Python/Windows combos; ``potracer`` exposes the same ``potrace.Bitmap`` API.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageOps
from potrace import (  # type: ignore[import-untyped]  # package: potracer
    POTRACE_TURNPOLICY_MINORITY,
    Bitmap,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TraceResult:
    """Result of tracing a single binary mask."""

    path_d: str
    curve_count: int
    empty: bool = False


def trace_mask_to_path(
    mask: np.ndarray,
    *,
    turdsize: int = 2,
    alphamax: float = 1.0,
    opttolerance: float = 0.2,
    opticurve: bool = True,
    blacklevel: float = 0.5,
) -> TraceResult:
    """Vectorize a binary mask (255 = foreground) into an SVG path ``d``.

    Potrace treats *dark* pixels as foreground, so the mask is inverted
    before tracing (white silhouette → black blob).

    Args:
        mask: 2D uint8 array (0 background, >0 / 255 foreground).
        turdsize: Suppress speckles up to this size.
        alphamax: Corner threshold.
        opttolerance: Curve optimization tolerance.
        opticurve: Enable curve optimization.
        blacklevel: Bitmap threshold after invert.
    """
    if mask.ndim != 2:
        raise ValueError(f"Mask must be 2D, got shape {mask.shape}")

    binary = np.where(mask > 0, 255, 0).astype(np.uint8)
    if not np.any(binary):
        return TraceResult(path_d="", curve_count=0, empty=True)

    image = Image.fromarray(binary, mode="L")
    # Dark = foreground for Potrace
    inverted = ImageOps.invert(image)
    bitmap = Bitmap(inverted, blacklevel=blacklevel)
    curves = bitmap.trace(
        turdsize=turdsize,
        turnpolicy=POTRACE_TURNPOLICY_MINORITY,
        alphamax=alphamax,
        opticurve=opticurve,
        opttolerance=opttolerance,
    )
    path_d = curves_to_path_d(curves)
    count = path_d.count("M")
    logger.debug("Traced mask → %d subpath(s), d_len=%d", count, len(path_d))
    return TraceResult(path_d=path_d, curve_count=count, empty=not path_d)


def curves_to_path_d(curves: object) -> str:
    """Convert a Potrace path list into a compact SVG path data string."""
    parts: list[str] = []
    for curve in curves:  # type: ignore[attr-defined]
        start = curve.start_point
        parts.append(f"M{_fmt(start.x)},{_fmt(start.y)}")
        for segment in curve.segments:
            if segment.is_corner:
                a = segment.c
                b = segment.end_point
                parts.append(f"L{_fmt(a.x)},{_fmt(a.y)}L{_fmt(b.x)},{_fmt(b.y)}")
            else:
                a = segment.c1
                b = segment.c2
                c = segment.end_point
                parts.append(
                    f"C{_fmt(a.x)},{_fmt(a.y)} {_fmt(b.x)},{_fmt(b.y)} {_fmt(c.x)},{_fmt(c.y)}"
                )
        parts.append("Z")
    return "".join(parts)


def _fmt(value: float) -> str:
    """Format a coordinate with trim of trailing zeros."""
    return f"{value:.3f}".rstrip("0").rstrip(".")


def load_mask_array(mask_path: str) -> np.ndarray:
    """Load a mask PNG/L image as a 2D uint8 numpy array."""
    with Image.open(mask_path) as img:
        return np.asarray(img.convert("L")).copy()

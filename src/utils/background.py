"""Traditional background-removal algorithms (offline)."""

from __future__ import annotations

import logging
from typing import Literal

import cv2
import numpy as np

logger = logging.getLogger(__name__)

BgMethod = Literal["flood_fill", "grabcut", "threshold"]


def remove_background(
    rgba: np.ndarray,
    *,
    method: BgMethod = "flood_fill",
    tolerance: int = 28,
) -> np.ndarray:
    """Remove background and return RGBA with transparent backdrop.

    Args:
        rgba: Input image RGBA.
        method: ``flood_fill`` (default — illustrations), ``grabcut`` (photos),
            or ``threshold`` (high-contrast silhouettes).
        tolerance: Color distance for flood-fill seed matching.
    """
    if method == "flood_fill":
        alpha = _mask_flood_fill(rgba, tolerance=tolerance)
    elif method == "grabcut":
        alpha = _mask_grabcut(rgba)
    elif method == "threshold":
        alpha = _mask_threshold(rgba)
    else:
        raise ValueError(f"Método de remoção de fundo inválido: {method}")

    # Feather edges slightly for cleaner cutouts
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    out = rgba.copy()
    out[:, :, 3] = alpha
    logger.debug("Background removed via %s", method)
    return out


def _mask_flood_fill(rgba: np.ndarray, *, tolerance: int) -> np.ndarray:
    """Mark background by flooding from the four corners (illustration-friendly)."""
    h, w = rgba.shape[:2]
    bgr = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
    # Work on a padded copy — floodFill requires a mask sized (h+2, w+2)
    working = bgr.copy()
    mask = np.zeros((h + 2, w + 2), dtype=np.uint8)
    lo = (tolerance,) * 3
    hi = (tolerance,) * 3
    flags = 4 | (255 << 8) | cv2.FLOODFILL_MASK_ONLY

    seeds = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]
    # Also seed along border midpoints for irregular backgrounds
    seeds.extend([(w // 2, 0), (w // 2, h - 1), (0, h // 2), (w - 1, h // 2)])

    for x, y in seeds:
        if mask[y + 1, x + 1] != 0:
            continue
        cv2.floodFill(working, mask, (x, y), (0, 0, 0), lo, hi, flags)

    # mask[1:-1,1:-1] == 255 → background
    bg = mask[1:-1, 1:-1] == 255
    alpha = np.where(bg, 0, 255).astype(np.uint8)

    # If nearly everything was flagged as bg, fall back to threshold
    if alpha.mean() < 5:
        logger.warning("Flood-fill emptied image; falling back to threshold")
        return _mask_threshold(rgba)
    return alpha


def _mask_grabcut(rgba: np.ndarray) -> np.ndarray:
    """GrabCut with an inset rectangle — better for centered photo subjects."""
    h, w = rgba.shape[:2]
    bgr = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2BGR)
    margin_x, margin_y = max(1, w // 20), max(1, h // 20)
    rect = (margin_x, margin_y, max(1, w - 2 * margin_x), max(1, h - 2 * margin_y))
    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(bgr, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    foreground = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(
        np.uint8
    )
    return foreground


def _mask_threshold(rgba: np.ndarray) -> np.ndarray:
    """Otsu threshold on luminance — high-contrast silhouettes / icons."""
    gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
    # If corners are bright, treat bright as background; else dark
    corners = np.array(
        [gray[0, 0], gray[0, -1], gray[-1, 0], gray[-1, -1]], dtype=np.float32
    )
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    if corners.mean() > 127:
        # bright background → keep dark/opaque as foreground
        alpha = cv2.bitwise_not(binary)
    else:
        alpha = binary
    # Keep existing alpha if already informative
    existing = rgba[:, :, 3]
    if existing.mean() < 250:
        alpha = cv2.bitwise_and(alpha, existing)
    return alpha

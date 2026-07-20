"""Contour / connected-component object detection (offline)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

import cv2
import numpy as np

from src.models.bounds import Bounds

logger = logging.getLogger(__name__)

DetectMethod = Literal["contours", "connected_components"]


@dataclass(slots=True)
class DetectedObject:
    """A single foreground region found by CV segmentation."""

    index: int
    bounds: Bounds
    area: float
    color_hex: str
    mask: np.ndarray  # uint8 0/255, full image size
    contour: np.ndarray  # shape (N, 1, 2)
    centroid: tuple[float, float]
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_metadata_dict(self, *, mask_path: str | None = None) -> dict[str, Any]:
        """Serialize detection (without ndarray) for ProjectDocument.metadata."""
        return {
            "index": self.index,
            "bounds": self.bounds.as_dict(),
            "area": self.area,
            "color": self.color_hex,
            "centroid": {"x": self.centroid[0], "y": self.centroid[1]},
            "description": self.description,
            "mask_path": mask_path,
            "metadata": self.metadata,
        }


def build_foreground_mask(rgba: np.ndarray, *, alpha_threshold: int = 10) -> np.ndarray:
    """Build a binary foreground mask from alpha or luminance fallback."""
    h, w = rgba.shape[:2]
    alpha = rgba[:, :, 3]
    if float(alpha.mean()) < 250:
        mask = (alpha > alpha_threshold).astype(np.uint8) * 255
    else:
        # Fully opaque (no BG removal yet): treat near-white / near-black corners heuristic
        gray = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2GRAY)
        corners = np.array(
            [gray[0, 0], gray[0, -1], gray[-1, 0], gray[-1, -1]], dtype=np.float32
        )
        if corners.mean() > 127:
            # bright background → foreground is darker / saturated regions
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        else:
            _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def detect_objects(
    rgba: np.ndarray,
    *,
    method: DetectMethod = "contours",
    min_area: float = 64.0,
    max_objects: int = 64,
) -> list[DetectedObject]:
    """Detect distinct objects using contours or connected components.

    Args:
        rgba: Source RGBA image.
        method: ``contours`` (default) or ``connected_components``.
        min_area: Discard regions smaller than this (pixels).
        max_objects: Cap the number of returned objects (largest first).
    """
    fg = build_foreground_mask(rgba)
    if method == "connected_components":
        objects = _detect_via_components(rgba, fg, min_area=min_area)
    else:
        objects = _detect_via_contours(rgba, fg, min_area=min_area)

    objects.sort(key=lambda o: o.area, reverse=True)
    objects = objects[:max_objects]
    # Re-index after sort
    for i, obj in enumerate(objects):
        obj.index = i
        obj.description = (
            f"region#{i + 1} area={obj.area:.0f} color={obj.color_hex} "
            f"bounds=({obj.bounds.x:.0f},{obj.bounds.y:.0f},{obj.bounds.width:.0f}x{obj.bounds.height:.0f})"
        )
    logger.info("Detected %d object(s) via %s", len(objects), method)
    return objects


def render_detection_overlay(rgba: np.ndarray, objects: list[DetectedObject]) -> np.ndarray:
    """Draw contour outlines on a darkened copy for preview."""
    base = rgba[:, :, :3].astype(np.float32) * 0.35
    canvas = np.clip(base, 0, 255).astype(np.uint8)
    palette = [
        (0, 212, 170),
        (255, 176, 32),
        (90, 160, 255),
        (255, 92, 122),
        (180, 120, 255),
        (120, 220, 90),
    ]
    for obj in objects:
        color = palette[obj.index % len(palette)]
        cv2.drawContours(canvas, [obj.contour], -1, color, 2)
        x, y = int(obj.bounds.x), int(obj.bounds.y)
        cv2.putText(
            canvas,
            f"#{obj.index + 1}",
            (x + 2, max(12, y + 14)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            color,
            1,
            cv2.LINE_AA,
        )
    alpha = np.full(canvas.shape[:2], 255, dtype=np.uint8)
    return np.dstack([canvas, alpha])


def extract_object_rgba(rgba: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Return full-size RGBA with only the masked object visible."""
    out = rgba.copy()
    out[:, :, 3] = np.minimum(out[:, :, 3], mask)
    return out


def dominant_color_hex(rgba: np.ndarray, mask: np.ndarray) -> str:
    """Average RGB of opaque masked pixels as #RRGGBB."""
    sel = mask > 0
    if not np.any(sel):
        return "#808080"
    pixels = rgba[:, :, :3][sel]
    mean = pixels.mean(axis=0)
    r, g, b = (int(round(c)) for c in mean)
    return f"#{r:02x}{g:02x}{b:02x}"


def _detect_via_contours(
    rgba: np.ndarray,
    fg: np.ndarray,
    *,
    min_area: float,
) -> list[DetectedObject]:
    contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    objects: list[DetectedObject] = []
    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        mask = np.zeros(fg.shape, dtype=np.uint8)
        cv2.drawContours(mask, [contour], -1, 255, thickness=cv2.FILLED)
        m = cv2.moments(contour)
        if m["m00"] > 0:
            cx, cy = m["m10"] / m["m00"], m["m01"] / m["m00"]
        else:
            cx, cy = x + w / 2, y + h / 2
        objects.append(
            DetectedObject(
                index=len(objects),
                bounds=Bounds(x=float(x), y=float(y), width=float(w), height=float(h)),
                area=area,
                color_hex=dominant_color_hex(rgba, mask),
                mask=mask,
                contour=contour,
                centroid=(float(cx), float(cy)),
                metadata={"method": "contours"},
            )
        )
    return objects


def _detect_via_components(
    rgba: np.ndarray,
    fg: np.ndarray,
    *,
    min_area: float,
) -> list[DetectedObject]:
    count, labels, stats, centroids = cv2.connectedComponentsWithStats(fg, connectivity=8)
    objects: list[DetectedObject] = []
    for label_id in range(1, count):  # 0 = background
        area = float(stats[label_id, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[label_id, cv2.CC_STAT_LEFT])
        y = int(stats[label_id, cv2.CC_STAT_TOP])
        w = int(stats[label_id, cv2.CC_STAT_WIDTH])
        h = int(stats[label_id, cv2.CC_STAT_HEIGHT])
        mask = np.where(labels == label_id, 255, 0).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contour = contours[0] if contours else np.array([[[x, y]]], dtype=np.int32)
        cx, cy = float(centroids[label_id][0]), float(centroids[label_id][1])
        objects.append(
            DetectedObject(
                index=len(objects),
                bounds=Bounds(x=float(x), y=float(y), width=float(w), height=float(h)),
                area=area,
                color_hex=dominant_color_hex(rgba, mask),
                mask=mask,
                contour=contour,
                centroid=(cx, cy),
                metadata={"method": "connected_components", "label_id": label_id},
            )
        )
    return objects

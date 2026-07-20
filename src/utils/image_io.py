"""Image I/O helpers shared by raster processors (OpenCV + Pillow)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from src.core.exceptions import ProcessorError


def resolve_working_image(project_original: Path | None, processed: Path | None) -> Path:
    """Prefer the latest processed raster; fall back to the original."""
    if processed is not None and processed.exists():
        return processed
    if project_original is not None and project_original.exists():
        return project_original
    raise ProcessorError("Nenhuma imagem disponível no projeto.")


def load_rgba(path: Path) -> np.ndarray:
    """Load an image as RGBA uint8 array (H, W, 4)."""
    # Prefer Pillow for broader format support (webp, etc.), then convert.
    try:
        with Image.open(path) as img:
            rgba = img.convert("RGBA")
            return np.asarray(rgba).copy()
    except OSError as exc:
        raise ProcessorError(f"Falha ao carregar imagem: {path}") from exc


def load_bgr(path: Path) -> np.ndarray:
    """Load an image as BGR uint8 array (OpenCV convention)."""
    rgba = load_rgba(path)
    bgr = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)
    return bgr


def save_rgba(path: Path, image: np.ndarray) -> Path:
    """Persist an RGBA/RGB/gray array as PNG (keeps alpha when present)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if image.ndim == 2:
        pil = Image.fromarray(image, mode="L")
    elif image.shape[2] == 4:
        pil = Image.fromarray(image, mode="RGBA")
    elif image.shape[2] == 3:
        # Assume RGB
        pil = Image.fromarray(image, mode="RGB")
    else:
        raise ProcessorError(f"Shape de imagem inválido: {image.shape}")
    pil.save(path, format="PNG")
    return path


def bgr_to_rgba(bgr: np.ndarray, alpha: np.ndarray | None = None) -> np.ndarray:
    """Convert BGR to RGBA, optionally applying an alpha mask (0–255)."""
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    if alpha is None:
        alpha = np.full(bgr.shape[:2], 255, dtype=np.uint8)
    else:
        if alpha.dtype != np.uint8:
            alpha = alpha.astype(np.uint8)
    return np.dstack([rgb, alpha])


def project_cache_dir(cache_root: Path, project_id: str) -> Path:
    """Return (and create) a per-project cache directory."""
    directory = cache_root / project_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def image_stats_summary(rgba: np.ndarray) -> str:
    """Build a short CV-derived caption for optional AI analysis."""
    h, w = rgba.shape[:2]
    rgb = rgba[:, :, :3]
    alpha = rgba[:, :, 3] if rgba.shape[2] == 4 else np.full((h, w), 255, dtype=np.uint8)
    opaque = alpha > 10
    mean = rgb[opaque].mean(axis=0) if opaque.any() else rgb.mean(axis=0)
    return (
        f"size={w}x{h}; mean_rgb=({mean[0]:.0f},{mean[1]:.0f},{mean[2]:.0f}); "
        f"opaque_ratio={opaque.mean():.2f}"
    )

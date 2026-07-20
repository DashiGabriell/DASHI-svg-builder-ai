"""Local classical super-resolution / upscale (offline)."""

from __future__ import annotations

import logging

import cv2
import numpy as np
from skimage.transform import resize as sk_resize

logger = logging.getLogger(__name__)


def upscale_image(
    rgba: np.ndarray,
    *,
    scale: float = 2.0,
    sharpen: bool = True,
) -> np.ndarray:
    """Upscale an RGBA image using high-quality classical SR.

    Pipeline (fully offline):
        1. Mild denoise on RGB
        2. Lanczos / scikit-image resize by ``scale``
        3. Optional unsharp mask for edge clarity

    DNN models (EDSR/ESPCN) can be plugged in later without changing callers.
    """
    if scale <= 1.0:
        return rgba.copy()

    rgb = rgba[:, :, :3].astype(np.float32) / 255.0
    alpha = rgba[:, :, 3]

    # Light denoise — preserve edges for illustration art
    bgr = cv2.cvtColor((rgb * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
    denoised = cv2.bilateralFilter(bgr, d=5, sigmaColor=40, sigmaSpace=40)
    rgb_d = cv2.cvtColor(denoised, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

    h, w = rgb_d.shape[:2]
    new_h, new_w = int(round(h * scale)), int(round(w * scale))

    # skimage resize with anti-aliasing — higher quality than plain INTER_LINEAR
    up_rgb = sk_resize(
        rgb_d,
        (new_h, new_w),
        order=3,
        mode="reflect",
        anti_aliasing=True,
        preserve_range=True,
    )
    up_alpha = cv2.resize(alpha, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    if sharpen:
        up_rgb = _unsharp_mask(up_rgb, amount=0.6, radius=1.2)

    out = np.dstack(
        [
            np.clip(up_rgb * 255.0, 0, 255).astype(np.uint8),
            np.clip(up_alpha, 0, 255).astype(np.uint8),
        ]
    )
    logger.debug("Upscaled %sx%s → %sx%s (scale=%.2f)", w, h, new_w, new_h, scale)
    return out


def _unsharp_mask(rgb: np.ndarray, *, amount: float, radius: float) -> np.ndarray:
    """Apply unsharp mask on float RGB [0, 1]."""
    blurred = cv2.GaussianBlur(rgb, (0, 0), sigmaX=radius, sigmaY=radius)
    sharp = rgb + amount * (rgb - blurred)
    return np.clip(sharp, 0.0, 1.0)

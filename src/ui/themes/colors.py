"""Color tokens for the desktop shell."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ThemeColors:
    """Color palette for the desktop shell."""

    background: str = "#0B0F14"
    surface: str = "#121821"
    surface_alt: str = "#1A2330"
    border: str = "#243041"
    accent: str = "#00D4AA"
    accent_dim: str = "#0A8F76"
    text: str = "#E8EEF5"
    text_muted: str = "#8B9BB0"
    danger: str = "#FF5C7A"
    warning: str = "#FFB020"


DEFAULT_THEME = ThemeColors()

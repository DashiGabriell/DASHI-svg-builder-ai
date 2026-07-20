"""Theme tokens and CustomTkinter appearance helpers."""

from __future__ import annotations

import customtkinter as ctk

from src.ui.themes.colors import DEFAULT_THEME, ThemeColors


def apply_appearance(theme: ThemeColors = DEFAULT_THEME) -> None:
    """Configure global CustomTkinter dark appearance.

    Widgets are styled explicitly with ``ThemeColors`` so the teal-on-near-black
    palette stays consistent (no stock purple themes).
    """
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    _ = theme


def brand_font(*, size: int = 14, weight: str = "normal") -> ctk.CTkFont:
    """Primary UI font — Cascadia Code when available."""
    return ctk.CTkFont(family="Cascadia Code", size=size, weight=weight)


def display_font(*, size: int = 22, weight: str = "bold") -> ctk.CTkFont:
    """Larger display font for brand / section titles."""
    return ctk.CTkFont(family="Segoe UI Variable Display", size=size, weight=weight)

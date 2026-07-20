"""Bottom status bar for pipeline feedback."""

from __future__ import annotations

import customtkinter as ctk

from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font


class StatusBar(ctk.CTkFrame):
    """Footer showing status message, stage and AI readiness."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        theme: ThemeColors = DEFAULT_THEME,
        **kwargs: object,
    ) -> None:
        super().__init__(
            master,
            height=36,
            fg_color=theme.surface,
            corner_radius=0,
            **kwargs,  # type: ignore[arg-type]
        )
        self._theme = theme
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)

        self._dot = ctk.CTkLabel(
            self,
            text="●",
            font=brand_font(size=10),
            text_color=theme.accent,
            width=20,
        )
        self._dot.grid(row=0, column=0, padx=(14, 0), pady=6)

        self._message = ctk.CTkLabel(
            self,
            text="Pronto",
            font=brand_font(size=12),
            text_color=theme.text,
            anchor="w",
        )
        self._message.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        self._stage = ctk.CTkLabel(
            self,
            text="Estágio: Vazio",
            font=brand_font(size=11),
            text_color=theme.text_muted,
            anchor="e",
        )
        self._stage.grid(row=0, column=2, padx=(8, 8), pady=6)

        self._ai = ctk.CTkLabel(
            self,
            text="IA: —",
            font=brand_font(size=11),
            text_color=theme.text_muted,
            anchor="e",
        )
        self._ai.grid(row=0, column=3, padx=(0, 16), pady=6)

    def set_message(self, message: str) -> None:
        """Update the primary status text."""
        self._message.configure(text=message)

    def set_stage(self, stage_label: str) -> None:
        """Update pipeline stage label."""
        self._stage.configure(text=f"Estágio: {stage_label}")

    def set_ai_status(self, enabled: bool, model: str = "") -> None:
        """Update AI connectivity indicator."""
        if enabled:
            short = model.split("/")[-1] if model else "on"
            self._ai.configure(text=f"IA: {short}", text_color=self._theme.accent)
            self._dot.configure(text_color=self._theme.accent)
        else:
            self._ai.configure(text="IA: offline", text_color=self._theme.warning)
            self._dot.configure(text_color=self._theme.warning)

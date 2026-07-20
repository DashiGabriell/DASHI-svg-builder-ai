"""Export format picker dialog (CustomTkinter)."""

from __future__ import annotations

import customtkinter as ctk

from src.exports.base import ExportFormat
from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font, display_font


class ExportDialog(ctk.CTkToplevel):
    """Modal dialog to choose an export format (raster, SVG, frameworks)."""

    def __init__(
        self,
        master: ctk.CTk,
        *,
        theme: ThemeColors = DEFAULT_THEME,
    ) -> None:
        super().__init__(master)
        self.title("Exportar")
        self.geometry("420x520")
        self.resizable(False, False)
        self.configure(fg_color=theme.surface)
        self.transient(master)
        self.grab_set()

        self._theme = theme
        self._result: ExportFormat | None = None
        self._var = ctk.StringVar(value=ExportFormat.SVG.value)

        ctk.CTkLabel(
            self,
            text="Exportar assets",
            font=display_font(size=18, weight="bold"),
            text_color=theme.text,
        ).pack(anchor="w", padx=20, pady=(20, 6))

        ctk.CTkLabel(
            self,
            text="SVG · raster · frameworks",
            font=brand_font(size=12),
            text_color=theme.text_muted,
        ).pack(anchor="w", padx=20, pady=(0, 10))

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.background,
            corner_radius=8,
            height=340,
        )
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        for fmt in ExportFormat:
            ctk.CTkRadioButton(
                scroll,
                text=fmt.label,
                variable=self._var,
                value=fmt.value,
                font=brand_font(size=13),
                text_color=theme.text,
                fg_color=theme.accent,
                hover_color=theme.accent_dim,
            ).pack(anchor="w", padx=12, pady=4)

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=16)

        ctk.CTkButton(
            buttons,
            text="Cancelar",
            font=brand_font(size=13),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            width=120,
            command=self._cancel,
        ).pack(side="left")

        ctk.CTkButton(
            buttons,
            text="Continuar",
            font=brand_font(size=13, weight="bold"),
            fg_color=theme.accent,
            hover_color=theme.accent_dim,
            text_color=theme.background,
            width=120,
            command=self._confirm,
        ).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.focus_force()

    def _confirm(self) -> None:
        self._result = ExportFormat(self._var.get())
        self.destroy()

    def _cancel(self) -> None:
        self._result = None
        self.destroy()

    def show(self) -> ExportFormat | None:
        """Block until closed and return the selected format (or None)."""
        self.wait_window()
        return self._result

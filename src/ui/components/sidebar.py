"""Sidebar action panel for the processing pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import customtkinter as ctk

from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font, display_font


@dataclass(frozen=True, slots=True)
class SidebarAction:
    """Descriptor for a sidebar button."""

    action_id: str
    label: str
    primary: bool = False


PIPELINE_ACTIONS: tuple[SidebarAction, ...] = (
    SidebarAction("import", "Importar imagem", primary=True),
    SidebarAction("enhance_quality", "Melhorar qualidade"),
    SidebarAction("remove_background", "Remover fundo"),
    SidebarAction("detect_objects", "Detectar objetos"),
    SidebarAction("separate_layers", "Separar camadas"),
    SidebarAction("vectorize", "Vetorizar"),
    SidebarAction("optimize_svg", "Otimizar SVG"),
    SidebarAction("export", "Exportar", primary=True),
)


class Sidebar(ctk.CTkFrame):
    """Left navigation rail with pipeline actions."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        on_action: Callable[[str], None],
        theme: ThemeColors = DEFAULT_THEME,
        width: int = 240,
        **kwargs: object,
    ) -> None:
        super().__init__(
            master,
            width=width,
            fg_color=theme.surface,
            corner_radius=0,
            border_width=0,
            **kwargs,  # type: ignore[arg-type]
        )
        self._theme = theme
        self._on_action = on_action
        self._buttons: dict[str, ctk.CTkButton] = {}

        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)

        brand = ctk.CTkLabel(
            self,
            text="SVG Builder AI",
            font=display_font(size=18, weight="bold"),
            text_color=theme.accent,
            anchor="w",
        )
        brand.grid(row=0, column=0, padx=20, pady=(24, 4), sticky="ew")

        subtitle = ctk.CTkLabel(
            self,
            text="PIPELINE",
            font=brand_font(size=11, weight="bold"),
            text_color=theme.text_muted,
            anchor="w",
        )
        subtitle.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="ew")

        # Accent rule under brand
        rule = ctk.CTkFrame(self, height=2, fg_color=theme.accent_dim, corner_radius=0)
        rule.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="ew")

        row = 3
        for action in PIPELINE_ACTIONS:
            btn = self._build_button(action)
            btn.grid(row=row, column=0, padx=16, pady=5, sticky="ew")
            self._buttons[action.action_id] = btn
            row += 1

        spacer = ctk.CTkFrame(self, fg_color="transparent")
        spacer.grid(row=row, column=0, sticky="nsew")
        self.grid_rowconfigure(row, weight=1)

        footer = ctk.CTkLabel(
            self,
            text="Etapa 2 · Interface",
            font=brand_font(size=10),
            text_color=theme.text_muted,
            anchor="w",
        )
        footer.grid(row=row + 1, column=0, padx=20, pady=(8, 20), sticky="ew")

    def _build_button(self, action: SidebarAction) -> ctk.CTkButton:
        theme = self._theme
        if action.primary:
            return ctk.CTkButton(
                self,
                text=action.label,
                font=brand_font(size=13, weight="bold"),
                fg_color=theme.accent,
                hover_color=theme.accent_dim,
                text_color=theme.background,
                corner_radius=8,
                height=40,
                anchor="w",
                command=lambda a=action.action_id: self._on_action(a),
            )
        return ctk.CTkButton(
            self,
            text=action.label,
            font=brand_font(size=13),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            border_width=1,
            border_color=theme.border,
            corner_radius=8,
            height=38,
            anchor="w",
            command=lambda a=action.action_id: self._on_action(a),
        )

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable all action buttons."""
        state = "normal" if enabled else "disabled"
        for button in self._buttons.values():
            button.configure(state=state)

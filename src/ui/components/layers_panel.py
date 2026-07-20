"""Scrollable layer list with CRUD inspector controls."""

from __future__ import annotations

from collections.abc import Callable

import customtkinter as ctk

from src.models.layer import Layer
from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font


class LayersPanel(ctk.CTkFrame):
    """Layer list + inspector for visibility, color, opacity and stack order."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        on_select: Callable[[str], None] | None = None,
        on_toggle_visibility: Callable[[str], None] | None = None,
        on_set_color: Callable[[str, str], None] | None = None,
        on_set_opacity: Callable[[str, float], None] | None = None,
        on_move: Callable[[str, int], None] | None = None,
        on_delete: Callable[[str], None] | None = None,
        on_duplicate: Callable[[str], None] | None = None,
        on_undo: Callable[[], None] | None = None,
        on_redo: Callable[[], None] | None = None,
        theme: ThemeColors = DEFAULT_THEME,
        **kwargs: object,
    ) -> None:
        super().__init__(
            master,
            fg_color=theme.surface,
            corner_radius=12,
            border_width=1,
            border_color=theme.border,
            **kwargs,  # type: ignore[arg-type]
        )
        self._theme = theme
        self._on_select = on_select
        self._on_toggle = on_toggle_visibility
        self._on_color = on_set_color
        self._on_opacity = on_set_opacity
        self._on_move = on_move
        self._on_delete = on_delete
        self._on_duplicate = on_duplicate
        self._on_undo = on_undo
        self._on_redo = on_redo

        self._layers: list[Layer] = []
        self._selected_id: str | None = None
        self._rows: list[ctk.CTkFrame] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="CAMADAS",
            font=brand_font(size=12, weight="bold"),
            text_color=theme.accent,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        hist = ctk.CTkFrame(header, fg_color="transparent")
        hist.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            hist,
            text="Undo",
            width=48,
            height=24,
            font=brand_font(size=10),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            command=lambda: self._on_undo and self._on_undo(),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            hist,
            text="Redo",
            width=48,
            height=24,
            font=brand_font(size=10),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            command=lambda: self._on_redo and self._on_redo(),
        ).pack(side="left", padx=2)

        self._list = ctk.CTkScrollableFrame(
            self,
            fg_color=theme.background,
            corner_radius=8,
            height=120,
        )
        self._list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        self._list.grid_columnconfigure(0, weight=1)

        self._empty = ctk.CTkLabel(
            self._list,
            text="Nenhuma camada ainda.\nSepare camadas para editar.",
            font=brand_font(size=12),
            text_color=theme.text_muted,
            justify="left",
        )
        self._empty.grid(row=0, column=0, sticky="ew", padx=8, pady=12)

        # Inspector
        inspector = ctk.CTkFrame(self, fg_color=theme.background, corner_radius=8)
        inspector.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 8))
        inspector.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            inspector,
            text="Cor",
            font=brand_font(size=11),
            text_color=theme.text_muted,
        ).grid(row=0, column=0, padx=(10, 6), pady=8, sticky="w")
        self._color_entry = ctk.CTkEntry(
            inspector,
            placeholder_text="#RRGGBB",
            font=brand_font(size=12),
            width=100,
        )
        self._color_entry.grid(row=0, column=1, padx=4, pady=8, sticky="w")
        ctk.CTkButton(
            inspector,
            text="Aplicar",
            width=64,
            height=26,
            font=brand_font(size=11),
            fg_color=theme.accent,
            hover_color=theme.accent_dim,
            text_color=theme.background,
            command=self._apply_color,
        ).grid(row=0, column=2, padx=(4, 10), pady=8)

        ctk.CTkLabel(
            inspector,
            text="Opacidade",
            font=brand_font(size=11),
            text_color=theme.text_muted,
        ).grid(row=1, column=0, padx=(10, 6), pady=(0, 8), sticky="w")
        self._opacity = ctk.CTkSlider(
            inspector,
            from_=0,
            to=1,
            number_of_steps=20,
            command=self._on_opacity_slide,
        )
        self._opacity.set(1.0)
        self._opacity.grid(row=1, column=1, columnspan=2, padx=(4, 10), pady=(0, 8), sticky="ew")

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))
        for text, cmd in (
            ("Visível", self._toggle),
            ("↑", lambda: self._move(-1)),
            ("↓", lambda: self._move(1)),
            ("Duplicar", self._duplicate),
            ("Excluir", self._delete),
        ):
            ctk.CTkButton(
                actions,
                text=text,
                width=64 if text not in {"↑", "↓"} else 32,
                height=28,
                font=brand_font(size=11),
                fg_color=theme.surface_alt if text != "Excluir" else theme.danger,
                hover_color=theme.border if text != "Excluir" else "#C44860",
                text_color=theme.text if text != "Excluir" else theme.background,
                command=cmd,
            ).pack(side="left", padx=2)

        self._count = ctk.CTkLabel(
            self,
            text="0 layers",
            font=brand_font(size=10),
            text_color=theme.text_muted,
            anchor="w",
        )
        self._count.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))

    def set_layers(self, layers: list[Layer], *, selected_id: str | None = None) -> None:
        """Rebuild the list from the current project layers."""
        self._layers = list(layers)
        if selected_id is not None:
            self._selected_id = selected_id
        elif self._selected_id and not any(layer.id == self._selected_id for layer in layers):
            self._selected_id = None

        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._empty.grid_remove()

        if not layers:
            self._empty.grid()
            self._count.configure(text="0 layers")
            return

        for index, layer in enumerate(sorted(layers, key=lambda item: item.z_index)):
            selected = layer.id == self._selected_id
            row = ctk.CTkFrame(
                self._list,
                fg_color=self._theme.accent_dim if selected else self._theme.surface_alt,
                corner_radius=6,
            )
            row.grid(row=index, column=0, sticky="ew", padx=4, pady=3)
            row.grid_columnconfigure(1, weight=1)

            swatch = ctk.CTkFrame(
                row,
                width=16,
                height=16,
                fg_color=layer.color,
                corner_radius=3,
            )
            swatch.grid(row=0, column=0, padx=(8, 6), pady=8)
            swatch.grid_propagate(False)

            label = ctk.CTkLabel(
                row,
                text=f"{layer.id}  ·  {layer.layer_type.value}",
                font=brand_font(size=12),
                text_color=self._theme.background if selected else self._theme.text,
                anchor="w",
            )
            label.grid(row=0, column=1, sticky="ew", pady=8)

            visibility = "on" if layer.visible else "off"
            vis = ctk.CTkLabel(
                row,
                text=visibility,
                font=brand_font(size=11),
                text_color=self._theme.background if selected else self._theme.text_muted,
                width=24,
            )
            vis.grid(row=0, column=2, padx=(4, 8), pady=8)

            for widget in (row, label, swatch, vis):
                widget.bind("<Button-1>", lambda _e, lid=layer.id: self._select(lid))

            self._rows.append(row)

        self._count.configure(text=f"{len(layers)} layer(s)")
        self._sync_inspector()

    def set_selected(self, layer_id: str | None) -> None:
        """Update selection highlight without replacing the layer list data."""
        self._selected_id = layer_id
        self.set_layers(self._layers, selected_id=layer_id)

    def _select(self, layer_id: str) -> None:
        self._selected_id = layer_id
        self.set_layers(self._layers, selected_id=layer_id)
        if self._on_select:
            self._on_select(layer_id)

    def _selected(self) -> Layer | None:
        return next((layer for layer in self._layers if layer.id == self._selected_id), None)

    def _sync_inspector(self) -> None:
        layer = self._selected()
        if layer is None:
            self._color_entry.delete(0, "end")
            self._opacity.set(1.0)
            return
        self._color_entry.delete(0, "end")
        self._color_entry.insert(0, layer.color)
        self._opacity.set(layer.opacity)

    def _apply_color(self) -> None:
        layer = self._selected()
        if layer is None or not self._on_color:
            return
        color = self._color_entry.get().strip()
        if not color.startswith("#") or len(color) not in {4, 7}:
            return
        self._on_color(layer.id, color)

    def _on_opacity_slide(self, value: float) -> None:
        layer = self._selected()
        if layer is None or not self._on_opacity:
            return
        # Debounce-ish: only fire when rounded value changes meaningfully
        if abs(layer.opacity - float(value)) < 0.04:
            return
        self._on_opacity(layer.id, float(value))

    def _toggle(self) -> None:
        layer = self._selected()
        if layer and self._on_toggle:
            self._on_toggle(layer.id)

    def _move(self, delta: int) -> None:
        layer = self._selected()
        if layer and self._on_move:
            self._on_move(layer.id, delta)

    def _duplicate(self) -> None:
        layer = self._selected()
        if layer and self._on_duplicate:
            self._on_duplicate(layer.id)

    def _delete(self) -> None:
        layer = self._selected()
        if layer and self._on_delete:
            self._on_delete(layer.id)

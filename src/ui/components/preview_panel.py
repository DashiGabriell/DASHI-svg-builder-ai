"""Image / SVG preview panel with placeholder state."""

from __future__ import annotations

from pathlib import Path

import customtkinter as ctk
from PIL import Image

from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font


class PreviewPanel(ctk.CTkFrame):
    """Single preview slot (Original | Processed | SVG)."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        title: str,
        theme: ThemeColors = DEFAULT_THEME,
        placeholder: str = "Nenhum conteúdo",
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
        self._placeholder_text = placeholder
        self._ctk_image: ctk.CTkImage | None = None
        self._max_preview = (420, 280)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        header.grid_columnconfigure(0, weight=1)

        title_label = ctk.CTkLabel(
            header,
            text=title.upper(),
            font=brand_font(size=12, weight="bold"),
            text_color=theme.accent,
            anchor="w",
        )
        title_label.grid(row=0, column=0, sticky="w")

        self._meta_label = ctk.CTkLabel(
            header,
            text="",
            font=brand_font(size=10),
            text_color=theme.text_muted,
            anchor="e",
        )
        self._meta_label.grid(row=0, column=1, sticky="e")

        self._canvas_frame = ctk.CTkFrame(
            self,
            fg_color=theme.background,
            corner_radius=8,
        )
        self._canvas_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self._canvas_frame.grid_columnconfigure(0, weight=1)
        self._canvas_frame.grid_rowconfigure(0, weight=1)

        self._image_label = ctk.CTkLabel(
            self._canvas_frame,
            text=placeholder,
            font=brand_font(size=13),
            text_color=theme.text_muted,
        )
        self._image_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

    def clear(self, message: str | None = None) -> None:
        """Reset preview to placeholder state."""
        self._ctk_image = None
        self._image_label.configure(
            image=None,
            text=message or self._placeholder_text,
            text_color=self._theme.text_muted,
        )
        self._meta_label.configure(text="")

    def show_image(self, path: str | Path) -> None:
        """Load and display a raster image scaled to the preview box."""
        file_path = Path(path)
        with Image.open(file_path) as img:
            img = img.convert("RGBA")
            display = img.copy()

        display.thumbnail(self._max_preview, Image.Resampling.LANCZOS)
        self._ctk_image = ctk.CTkImage(
            light_image=display,
            dark_image=display,
            size=display.size,
        )
        self._image_label.configure(image=self._ctk_image, text="")
        with Image.open(file_path) as original:
            w, h = original.size
        self._meta_label.configure(text=f"{w}×{h} · {file_path.suffix.upper().lstrip('.')}")

    def show_text(self, content: str, *, meta: str = "") -> None:
        """Show plain / SVG text content inside the preview."""
        self._ctk_image = None
        preview = content.strip()
        if len(preview) > 400:
            preview = preview[:400] + "…"
        if not preview:
            self.clear("SVG ainda não gerado")
            return
        self._image_label.configure(
            image=None,
            text=preview,
            text_color=self._theme.text,
            justify="left",
            anchor="nw",
        )
        self._meta_label.configure(text=meta)

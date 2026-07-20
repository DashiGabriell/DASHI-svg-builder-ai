"""Interactive canvas — zoom, pan, grid and layer visualization."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image, ImageTk

from src.models.layer import Layer
from src.models.project import ProjectDocument
from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font

logger = logging.getLogger(__name__)


class InteractiveCanvas(ctk.CTkFrame):
    """Zoomable/pannable canvas that composites project layers in real time."""

    def __init__(
        self,
        master: ctk.CTk | ctk.CTkFrame,
        *,
        on_select: Callable[[str | None], None] | None = None,
        on_translate: Callable[[str, float, float], None] | None = None,
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
        self._on_translate = on_translate

        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._show_grid = True
        self._selected_id: str | None = None
        self._project: ProjectDocument | None = None
        self._base_image: Image.Image | None = None
        self._photo_cache: list[ImageTk.PhotoImage] = []

        self._panning = False
        self._pan_last = (0, 0)
        self._dragging_layer = False
        self._drag_start = (0.0, 0.0)
        self._drag_origin_bounds: tuple[float, float] | None = None

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(self, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(
            toolbar,
            text="CANVAS",
            font=brand_font(size=12, weight="bold"),
            text_color=theme.accent,
        ).pack(side="left")

        self._zoom_label = ctk.CTkLabel(
            toolbar,
            text="100%",
            font=brand_font(size=11),
            text_color=theme.text_muted,
            width=48,
        )
        self._zoom_label.pack(side="right", padx=(4, 0))

        ctk.CTkButton(
            toolbar,
            text="+",
            width=28,
            height=26,
            font=brand_font(size=14, weight="bold"),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            command=lambda: self.zoom_by(1.15),
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            toolbar,
            text="−",
            width=28,
            height=26,
            font=brand_font(size=14, weight="bold"),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            command=lambda: self.zoom_by(1 / 1.15),
        ).pack(side="right", padx=2)

        self._grid_btn = ctk.CTkButton(
            toolbar,
            text="Grid",
            width=52,
            height=26,
            font=brand_font(size=11),
            fg_color=theme.accent_dim,
            hover_color=theme.accent,
            text_color=theme.background,
            command=self.toggle_grid,
        )
        self._grid_btn.pack(side="right", padx=6)

        ctk.CTkButton(
            toolbar,
            text="Fit",
            width=40,
            height=26,
            font=brand_font(size=11),
            fg_color=theme.surface_alt,
            hover_color=theme.border,
            text_color=theme.text,
            command=self.fit_view,
        ).pack(side="right", padx=2)

        self._canvas = tk.Canvas(
            self,
            background=theme.background,
            highlightthickness=0,
            bd=0,
        )
        self._canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self._canvas.bind("<Configure>", lambda _e: self.redraw())
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind("<Button-4>", lambda e: self._on_mousewheel_linux(e, 1))
        self._canvas.bind("<Button-5>", lambda e: self._on_mousewheel_linux(e, -1))
        self._canvas.bind("<ButtonPress-1>", self._on_left_press)
        self._canvas.bind("<B1-Motion>", self._on_left_drag)
        self._canvas.bind("<ButtonRelease-1>", self._on_left_release)
        self._canvas.bind("<ButtonPress-2>", self._on_pan_start)
        self._canvas.bind("<B2-Motion>", self._on_pan_move)
        self._canvas.bind("<ButtonRelease-2>", self._on_pan_end)
        self._canvas.bind("<ButtonPress-3>", self._on_pan_start)
        self._canvas.bind("<B3-Motion>", self._on_pan_move)
        self._canvas.bind("<ButtonRelease-3>", self._on_pan_end)

    # ------------------------------------------------------------------ public

    def set_project(self, project: ProjectDocument | None) -> None:
        """Replace the displayed project and refresh."""
        self._project = project
        self._load_base_image()
        self.redraw()

    def set_selected(self, layer_id: str | None) -> None:
        """Highlight a layer by id."""
        self._selected_id = layer_id
        self.redraw()

    def toggle_grid(self) -> None:
        """Show / hide the background grid."""
        self._show_grid = not self._show_grid
        color = self._theme.accent_dim if self._show_grid else self._theme.surface_alt
        self._grid_btn.configure(fg_color=color)
        self.redraw()

    def zoom_by(self, factor: float, *, anchor: tuple[float, float] | None = None) -> None:
        """Multiply zoom by ``factor``, optionally keeping ``anchor`` (canvas px) stable."""
        old = self._scale
        new = max(0.1, min(8.0, old * factor))
        if abs(new - old) < 1e-6:
            return
        if anchor is not None:
            ax, ay = anchor
            # Keep world point under cursor fixed
            wx = (ax - self._offset_x) / old
            wy = (ay - self._offset_y) / old
            self._scale = new
            self._offset_x = ax - wx * new
            self._offset_y = ay - wy * new
        else:
            self._scale = new
        self._zoom_label.configure(text=f"{int(self._scale * 100)}%")
        self.redraw()

    def fit_view(self) -> None:
        """Fit the project bounds into the canvas."""
        if self._project is None:
            return
        w = max(1, self._project.width)
        h = max(1, self._project.height)
        cw = max(1, self._canvas.winfo_width())
        ch = max(1, self._canvas.winfo_height())
        pad = 24
        scale = min((cw - pad) / w, (ch - pad) / h, 4.0)
        self._scale = max(0.1, scale)
        self._offset_x = (cw - w * self._scale) / 2
        self._offset_y = (ch - h * self._scale) / 2
        self._zoom_label.configure(text=f"{int(self._scale * 100)}%")
        self.redraw()

    def redraw(self) -> None:
        """Repaint the canvas contents."""
        canvas = self._canvas
        canvas.delete("all")
        self._photo_cache.clear()

        cw = max(1, canvas.winfo_width())
        ch = max(1, canvas.winfo_height())

        # Checkerboard
        size = 12
        c1, c2 = "#141A22", "#1A222C"
        for y in range(0, ch, size):
            for x in range(0, cw, size):
                color = c1 if ((x // size) + (y // size)) % 2 == 0 else c2
                canvas.create_rectangle(x, y, x + size, y + size, fill=color, outline="")

        if self._show_grid and self._project is not None:
            self._draw_grid(cw, ch)

        if self._project is None:
            canvas.create_text(
                cw / 2,
                ch / 2,
                text="Canvas interativo\nSepare camadas para editar",
                fill=self._theme.text_muted,
                font=("Cascadia Code", 12),
                justify="center",
            )
            return

        # Base image (processed / original) under layers
        if self._base_image is not None:
            self._draw_pil(self._base_image, 0, 0, alpha_scale=0.35)

        for layer in sorted(self._project.layers, key=lambda item: item.z_index):
            if not layer.visible:
                continue
            self._draw_layer(layer)

        if self._selected_id:
            layer = next(
                (item for item in self._project.layers if item.id == self._selected_id),
                None,
            )
            if layer is not None:
                self._draw_selection(layer)

    # ----------------------------------------------------------------- drawing

    def _load_base_image(self) -> None:
        self._base_image = None
        if self._project is None:
            return
        for candidate in (
            self._project.processed_image_path,
            self._project.original_image_path,
            self._project.source_path,
        ):
            if candidate and Path(candidate).exists():
                try:
                    self._base_image = Image.open(candidate).convert("RGBA")
                    if self._project.width and self._project.height:
                        if self._base_image.size != (self._project.width, self._project.height):
                            self._base_image = self._base_image.resize(
                                (self._project.width, self._project.height),
                                Image.Resampling.LANCZOS,
                            )
                    return
                except OSError:
                    logger.debug("Could not load base image %s", candidate)

    def _draw_grid(self, cw: int, ch: int) -> None:
        step = max(8, int(20 * self._scale))
        color = "#243041"
        # Align to world origin
        start_x = int(self._offset_x) % step
        start_y = int(self._offset_y) % step
        for x in range(start_x, cw, step):
            self._canvas.create_line(x, 0, x, ch, fill=color)
        for y in range(start_y, ch, step):
            self._canvas.create_line(0, y, cw, y, fill=color)

    def _world_to_canvas(self, x: float, y: float) -> tuple[float, float]:
        return x * self._scale + self._offset_x, y * self._scale + self._offset_y

    def _canvas_to_world(self, x: float, y: float) -> tuple[float, float]:
        return (x - self._offset_x) / self._scale, (y - self._offset_y) / self._scale

    def _draw_pil(
        self,
        image: Image.Image,
        world_x: float,
        world_y: float,
        *,
        alpha_scale: float = 1.0,
    ) -> None:
        w = max(1, int(image.width * self._scale))
        h = max(1, int(image.height * self._scale))
        resized = image.resize((w, h), Image.Resampling.NEAREST)
        if alpha_scale < 1.0:
            r, g, b, a = resized.split()
            a = a.point(lambda p: int(p * alpha_scale))
            resized = Image.merge("RGBA", (r, g, b, a))
        photo = ImageTk.PhotoImage(resized)
        self._photo_cache.append(photo)
        cx, cy = self._world_to_canvas(world_x, world_y)
        self._canvas.create_image(cx, cy, image=photo, anchor="nw")

    def _draw_layer(self, layer: Layer) -> None:
        raster = layer.metadata.get("raster_path")
        if raster and Path(str(raster)).exists():
            try:
                img = Image.open(str(raster)).convert("RGBA")
                if layer.opacity < 1.0:
                    r, g, b, a = img.split()
                    a = a.point(lambda p: int(p * layer.opacity))
                    img = Image.merge("RGBA", (r, g, b, a))
                # Tint not applied here — color edits affect SVG/path fills;
                # for raster preview we keep original pixels but tint border
                self._draw_pil(img, 0, 0)
                return
            except OSError:
                logger.debug("Layer raster missing for %s", layer.id)

        # Fallback: filled bounds rectangle
        x1, y1 = self._world_to_canvas(layer.bounds.x, layer.bounds.y)
        x2, y2 = self._world_to_canvas(
            layer.bounds.x + layer.bounds.width,
            layer.bounds.y + layer.bounds.height,
        )
        self._canvas.create_rectangle(
            x1,
            y1,
            x2,
            y2,
            fill=layer.color,
            outline=self._theme.accent,
            stipple="gray50",
            width=1,
        )

    def _draw_selection(self, layer: Layer) -> None:
        x1, y1 = self._world_to_canvas(layer.bounds.x, layer.bounds.y)
        x2, y2 = self._world_to_canvas(
            layer.bounds.x + layer.bounds.width,
            layer.bounds.y + layer.bounds.height,
        )
        self._canvas.create_rectangle(
            x1 - 2,
            y1 - 2,
            x2 + 2,
            y2 + 2,
            outline=self._theme.accent,
            width=2,
            dash=(4, 2),
        )
        self._canvas.create_text(
            x1 + 4,
            y1 - 10,
            text=layer.id,
            anchor="sw",
            fill=self._theme.accent,
            font=("Cascadia Code", 9),
        )

    # ----------------------------------------------------------------- events

    def _on_mousewheel(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        factor = 1.1 if event.delta > 0 else 1 / 1.1
        self.zoom_by(factor, anchor=(event.x, event.y))

    def _on_mousewheel_linux(self, event: tk.Event, direction: int) -> None:  # type: ignore[type-arg]
        factor = 1.1 if direction > 0 else 1 / 1.1
        self.zoom_by(factor, anchor=(event.x, event.y))

    def _hit_test(self, canvas_x: float, canvas_y: float) -> Layer | None:
        if self._project is None:
            return None
        wx, wy = self._canvas_to_world(canvas_x, canvas_y)
        # Top-most first
        for layer in sorted(self._project.layers, key=lambda item: item.z_index, reverse=True):
            if not layer.visible:
                continue
            b = layer.bounds
            if b.x <= wx <= b.right and b.y <= wy <= b.bottom:
                return layer
        return None

    def _on_left_press(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        layer = self._hit_test(event.x, event.y)
        layer_id = layer.id if layer else None
        self._selected_id = layer_id
        if self._on_select:
            self._on_select(layer_id)
        if layer is not None:
            self._dragging_layer = True
            self._drag_start = self._canvas_to_world(event.x, event.y)
            self._drag_origin_bounds = (layer.bounds.x, layer.bounds.y)
        self.redraw()

    def _on_left_drag(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._dragging_layer or not self._selected_id or self._project is None:
            return
        wx, wy = self._canvas_to_world(event.x, event.y)
        dx = wx - self._drag_start[0]
        dy = wy - self._drag_start[1]
        # Preview only — commit on release
        layer = next(
            (item for item in self._project.layers if item.id == self._selected_id),
            None,
        )
        if layer is None or self._drag_origin_bounds is None:
            return
        # Temporary visual: shift bounds for redraw without committing
        ox, oy = self._drag_origin_bounds
        preview = layer.model_copy(
            update={
                "bounds": layer.bounds.model_copy(update={"x": ox + dx, "y": oy + dy})
            }
        )
        # Replace temporarily in a shallow copy for redraw
        layers = [
            preview if item.id == layer.id else item for item in self._project.layers
        ]
        self._project = self._project.model_copy(update={"layers": layers})
        self.redraw()

    def _on_left_release(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if self._dragging_layer and self._selected_id and self._drag_origin_bounds:
            wx, wy = self._canvas_to_world(event.x, event.y)
            dx = wx - self._drag_start[0]
            dy = wy - self._drag_start[1]
            if abs(dx) > 0.5 or abs(dy) > 0.5:
                # Restore origin then let controller apply command
                if self._project is not None:
                    ox, oy = self._drag_origin_bounds
                    restored = []
                    for item in self._project.layers:
                        if item.id == self._selected_id:
                            restored.append(
                                item.model_copy(
                                    update={
                                        "bounds": item.bounds.model_copy(
                                            update={"x": ox, "y": oy}
                                        )
                                    }
                                )
                            )
                        else:
                            restored.append(item)
                    self._project = self._project.model_copy(update={"layers": restored})
                if self._on_translate:
                    self._on_translate(self._selected_id, dx, dy)
        self._dragging_layer = False
        self._drag_origin_bounds = None
        self.redraw()

    def _on_pan_start(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        self._panning = True
        self._pan_last = (event.x, event.y)

    def _on_pan_move(self, event: tk.Event) -> None:  # type: ignore[type-arg]
        if not self._panning:
            return
        dx = event.x - self._pan_last[0]
        dy = event.y - self._pan_last[1]
        self._offset_x += dx
        self._offset_y += dy
        self._pan_last = (event.x, event.y)
        self.redraw()

    def _on_pan_end(self, _event: tk.Event) -> None:  # type: ignore[type-arg]
        self._panning = False

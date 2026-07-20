"""Main application window — sidebar + Original | Canvas | SVG + layers."""

from __future__ import annotations

import logging
import tkinter.filedialog as filedialog
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from src import __app_name__, __version__
from src.core.events import Event, EventBus
from src.ui import events as ui_events
from src.ui.components import LayersPanel, PreviewPanel, Sidebar, StatusBar
from src.ui.components.interactive_canvas import InteractiveCanvas
from src.ui.controller import AppController, SUPPORTED_IMAGE_EXTENSIONS
from src.ui.themes import DEFAULT_THEME, ThemeColors
from src.ui.themes.apply import brand_font, display_font

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Root CustomTkinter window for SVG Builder AI."""

    def __init__(
        self,
        controller: AppController,
        event_bus: EventBus,
        *,
        ai_enabled: bool = False,
        ai_model: str = "",
        theme: ThemeColors = DEFAULT_THEME,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._bus = event_bus
        self._theme = theme

        self.title(f"{__app_name__}  ·  v{__version__}")
        self.geometry("1360x860")
        self.minsize(1100, 720)
        self.configure(fg_color=theme.background)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._sidebar = Sidebar(self, on_action=self._on_sidebar_action, theme=theme)
        self._sidebar.grid(row=0, column=0, rowspan=2, sticky="nsw")

        workspace = ctk.CTkFrame(self, fg_color="transparent")
        workspace.grid(row=0, column=1, sticky="nsew", padx=(0, 16), pady=(16, 8))
        workspace.grid_columnconfigure(0, weight=1)
        workspace.grid_rowconfigure(1, weight=3)
        workspace.grid_rowconfigure(2, weight=2)

        header = ctk.CTkFrame(workspace, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text="Workspace",
            font=display_font(size=22, weight="bold"),
            text_color=theme.text,
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Original  →  Canvas  →  SVG Final   ·   scroll=zoom  RMB/MMB=pan",
            font=brand_font(size=12),
            text_color=theme.text_muted,
            anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        previews = ctk.CTkFrame(workspace, fg_color="transparent")
        previews.grid(row=1, column=0, sticky="nsew")
        previews.grid_columnconfigure(0, weight=1)
        previews.grid_columnconfigure(1, weight=2)
        previews.grid_columnconfigure(2, weight=1)
        previews.grid_rowconfigure(0, weight=1)

        self._preview_original = PreviewPanel(
            previews,
            title="Imagem Original",
            placeholder="Importe uma arte para começar",
            theme=theme,
        )
        self._preview_original.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._canvas = InteractiveCanvas(
            previews,
            on_select=self._on_canvas_select,
            on_translate=self._controller.translate_layer,
            theme=theme,
        )
        self._canvas.grid(row=0, column=1, sticky="nsew", padx=8)

        self._preview_svg = PreviewPanel(
            previews,
            title="SVG Final",
            placeholder="SVG ainda não gerado",
            theme=theme,
        )
        self._preview_svg.grid(row=0, column=2, sticky="nsew", padx=(8, 0))

        self._layers_panel = LayersPanel(
            workspace,
            on_select=lambda lid: self._controller.select_layer(lid),
            on_toggle_visibility=self._controller.toggle_layer_visibility,
            on_set_color=self._controller.set_layer_color,
            on_set_opacity=self._controller.set_layer_opacity,
            on_move=self._controller.move_layer,
            on_delete=self._controller.delete_layer,
            on_duplicate=self._controller.duplicate_layer,
            on_undo=self._controller.undo,
            on_redo=self._controller.redo,
            theme=theme,
        )
        self._layers_panel.grid(row=2, column=0, sticky="nsew", pady=(12, 0))

        self._status = StatusBar(self, theme=theme)
        self._status.grid(row=1, column=1, sticky="ew")
        self._status.set_ai_status(ai_enabled, ai_model)
        self._status.set_stage(controller.state.stage_label)

        self.bind_all("<Control-z>", lambda _e: self._controller.undo())
        self.bind_all("<Control-y>", lambda _e: self._controller.redo())

        self._subscribe_events()
        logger.info("MainWindow initialised")

    def _subscribe_events(self) -> None:
        self._bus.subscribe(ui_events.STATUS_MESSAGE, self._on_status_event)
        self._bus.subscribe(ui_events.PROJECT_UPDATED, self._on_project_event)
        self._bus.subscribe(ui_events.PREVIEW_ORIGINAL, self._on_preview_original)
        self._bus.subscribe(ui_events.PREVIEW_PROCESSED, self._on_preview_processed)
        self._bus.subscribe(ui_events.PREVIEW_SVG, self._on_preview_svg)
        self._bus.subscribe(ui_events.LAYERS_UPDATED, self._on_layers_updated)
        self._bus.subscribe(ui_events.LAYER_SELECTED, self._on_layer_selected_event)

    def _on_sidebar_action(self, action_id: str) -> None:
        if action_id == "import":
            self._open_import_dialog()
            return
        if action_id == "export":
            self._open_export_dialog()
            return
        self._controller.run_action(action_id)

    def _open_import_dialog(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_IMAGE_EXTENSIONS))
        path = filedialog.askopenfilename(
            parent=self,
            title="Importar imagem",
            filetypes=[
                ("Imagens", patterns),
                ("Todos os arquivos", "*.*"),
            ],
        )
        if not path:
            return
        try:
            self._controller.import_image(path)
            self._layers_panel.set_layers([])
            self._canvas.set_project(self._controller.state.project)
        except (OSError, ValueError) as exc:
            logger.warning("Import failed: %s", exc)
            messagebox.showerror("Falha ao importar", str(exc), parent=self)
            self._controller.set_status(f"Erro ao importar: {exc}")

    def _open_export_dialog(self) -> None:
        from src.ui.components.export_dialog import ExportDialog

        if not self._controller.state.has_image:
            messagebox.showinfo(
                "Exportar",
                "Importe e processe uma imagem antes de exportar.",
                parent=self,
            )
            return

        dialog = ExportDialog(self, theme=self._theme)
        fmt = dialog.show()
        if fmt is None:
            self._controller.set_status("Exportação cancelada.")
            return

        default_name = f"{self._controller.state.project.name or 'export'}{fmt.extension}"
        path = filedialog.asksaveasfilename(
            parent=self,
            title=f"Exportar {fmt.label}",
            defaultextension=fmt.extension,
            initialfile=default_name,
            filetypes=fmt.filetypes,
        )
        if not path:
            self._controller.set_status("Exportação cancelada.")
            return

        try:
            written = self._controller.export_project(fmt, path)
            messagebox.showinfo("Exportar", f"Arquivo salvo:\n{written}", parent=self)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Falha ao exportar", str(exc), parent=self)

    def _on_status_event(self, event: Event) -> None:
        self._status.set_message(str(event.payload.get("message", "")))

    def _on_project_event(self, event: Event) -> None:
        self._status.set_stage(self._controller.state.stage_label)
        name = event.payload.get("name", "")
        if name:
            self.title(f"{__app_name__}  ·  {name}")
        self._canvas.set_project(self._controller.state.project)

    def _on_preview_original(self, event: Event) -> None:
        path = event.payload.get("path")
        if not path:
            self._preview_original.clear()
            return
        try:
            self._preview_original.show_image(Path(str(path)))
        except OSError as exc:
            self._preview_original.clear(f"Erro ao exibir: {exc}")

    def _on_preview_processed(self, event: Event) -> None:
        # Canvas consumes project state; keep hook for pipeline compatibility
        self._canvas.set_project(self._controller.state.project)

    def _on_preview_svg(self, event: Event) -> None:
        content = str(event.payload.get("content", "") or "")
        self._preview_svg.show_text(content, meta="SVG" if content else "")

    def _on_layers_updated(self, event: Event) -> None:
        selected = event.payload.get("selected", self._controller.state.selected_layer_id)
        self._layers_panel.set_layers(
            self._controller.state.project.layers,
            selected_id=selected if isinstance(selected, str) else None,
        )
        self._canvas.set_project(self._controller.state.project)
        self._canvas.set_selected(
            selected if isinstance(selected, str) else self._controller.state.selected_layer_id
        )

    def _on_layer_selected_event(self, event: Event) -> None:
        layer_id = event.payload.get("layer_id")
        lid = layer_id if isinstance(layer_id, str) else None
        self._layers_panel.set_selected(lid)
        self._canvas.set_selected(lid)

    def _on_canvas_select(self, layer_id: str | None) -> None:
        self._controller.select_layer(layer_id)

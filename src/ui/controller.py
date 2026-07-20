"""Application controller — bridges UI actions to domain / pipeline / export."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from src.core.commands import CommandHistory
from src.core.commands.layer_commands import (
    DeleteLayerCommand,
    DuplicateLayerCommand,
    MoveLayerCommand,
    SetColorCommand,
    SetOpacityCommand,
    ToggleVisibilityCommand,
    TranslateLayerCommand,
)
from src.core.events import Event, EventBus
from src.core.exceptions import PluginError, ProcessorError
from src.exports.base import ExportFormat
from src.exports.export_service import ExportService
from src.models.project import PipelineStage, ProjectDocument
from src.services.pipeline_service import ACTION_PROCESSOR_MAP, PipelineService
from src.ui import events as ui_events
from src.ui.state import AppState
from src.utils.svg_builder import build_svg_document

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

# Remaining UI stubs (framework exporters arrive in later stages).
PENDING_ACTIONS: dict[str, str] = {}


class AppController:
    """Coordinates UI commands, project state and Observer notifications."""

    def __init__(
        self,
        event_bus: EventBus,
        *,
        pipeline: PipelineService | None = None,
        export_service: ExportService | None = None,
        history: CommandHistory | None = None,
        state: AppState | None = None,
    ) -> None:
        self._bus = event_bus
        self._pipeline = pipeline
        self._exports = export_service
        self._history = history or CommandHistory()
        self.state = state or AppState()

    def set_status(self, message: str) -> None:
        """Update status bar text and notify observers."""
        self.state.status_message = message
        self._bus.publish(Event(name=ui_events.STATUS_MESSAGE, payload={"message": message}))
        logger.info("Status: %s", message)

    def import_image(self, path: str | Path) -> ProjectDocument:
        """Load an image from disk into the project and refresh previews."""
        file_path = Path(path).expanduser().resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        suffix = file_path.suffix.lower()
        if suffix not in SUPPORTED_IMAGE_EXTENSIONS:
            raise ValueError(
                f"Formato não suportado: {suffix}. "
                f"Use: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}"
            )

        try:
            with Image.open(file_path) as img:
                img.load()
                width, height = img.size
                mode = img.mode
        except OSError as exc:
            raise ValueError(f"Não foi possível abrir a imagem: {exc}") from exc

        project = ProjectDocument(
            name=file_path.stem,
            source_path=file_path,
            original_image_path=file_path,
            processed_image_path=None,
            svg_content="",
            stage=PipelineStage.LOADED,
            layers=[],
            width=width,
            height=height,
            metadata={"mode": mode, "format": suffix.lstrip(".")},
        )

        if self._pipeline is not None:
            try:
                project = self._pipeline.normalize_loaded(project)
            except (ProcessorError, PluginError, ValueError) as exc:
                logger.warning("Normalize after import failed: %s", exc)

        self.state.project = project
        self.state.selected_layer_id = None
        preview_path = project.original_image_path or file_path
        self.set_status(f"Importado: {file_path.name} ({project.width}×{project.height})")
        self._publish_project()
        self._bus.publish(
            Event(
                name=ui_events.PREVIEW_ORIGINAL,
                payload={
                    "path": str(preview_path),
                    "width": project.width,
                    "height": project.height,
                },
            )
        )
        self._bus.publish(Event(name=ui_events.PREVIEW_PROCESSED, payload={"path": None}))
        self._bus.publish(Event(name=ui_events.PREVIEW_SVG, payload={"content": ""}))
        return project

    def run_action(self, action_id: str, **kwargs: object) -> None:
        """Dispatch a sidebar action by id.

        Note: ``export`` is opened via the MainWindow dialog, which then calls
        ``export_project``. Calling ``run_action("export")`` alone is a no-op hint.
        """
        self._bus.publish(Event(name=ui_events.ACTION_REQUESTED, payload={"action": action_id}))

        if action_id == "export":
            self.set_status("Escolha o formato de exportação…")
            return

        if action_id in ACTION_PROCESSOR_MAP:
            self._run_pipeline_action(action_id, **kwargs)
            return

        if action_id in PENDING_ACTIONS:
            if not self.state.has_image:
                self.set_status("Importe uma imagem antes de continuar.")
                return
            message = PENDING_ACTIONS[action_id]
            self.set_status(message)
            self._bus.publish(
                Event(
                    name=ui_events.ACTION_COMPLETED,
                    payload={"action": action_id, "pending": True, "message": message},
                )
            )
            return

        self.set_status(f"Ação desconhecida: {action_id}")
        self._bus.publish(Event(name=ui_events.ACTION_FAILED, payload={"action": action_id}))

    def export_project(
        self,
        fmt: ExportFormat | str,
        destination: str | Path,
    ) -> Path:
        """Export the current project to ``destination`` in the given format."""
        if self._exports is None:
            raise ProcessorError("Serviço de exportação não configurado.")
        if not self.state.has_image:
            raise ProcessorError("Importe uma imagem antes de exportar.")

        self.set_status(f"Exportando ({fmt})…")
        try:
            path = self._exports.export(self.state.project, fmt, destination)
            self.state.project = self._exports.mark_exported(self.state.project, path)
            self.state.last_export_path = path
            self._publish_project()
            if self.state.project.svg_content:
                self._bus.publish(
                    Event(
                        name=ui_events.PREVIEW_SVG,
                        payload={"content": self.state.project.svg_content},
                    )
                )
            self.set_status(f"Exportado: {path.name}")
            self._bus.publish(
                Event(
                    name=ui_events.ACTION_COMPLETED,
                    payload={"action": "export", "path": str(path), "format": str(fmt)},
                )
            )
            return path
        except (ProcessorError, OSError, ValueError) as exc:
            logger.exception("Export failed")
            self.set_status(f"Erro ao exportar: {exc}")
            self._bus.publish(
                Event(
                    name=ui_events.ACTION_FAILED,
                    payload={"action": "export", "error": str(exc)},
                )
            )
            raise

    def _run_pipeline_action(self, action_id: str, **kwargs: object) -> None:
        if self._pipeline is None:
            self.set_status("Pipeline não configurado.")
            self._bus.publish(
                Event(name=ui_events.ACTION_FAILED, payload={"action": action_id})
            )
            return

        if not self.state.has_image:
            self.set_status("Importe uma imagem antes de continuar.")
            return

        labels = {
            "enhance_quality": "Melhorando qualidade…",
            "remove_background": "Removendo fundo…",
            "detect_objects": "Detectando objetos…",
            "separate_layers": "Separando camadas…",
            "vectorize": "Vetorizando camadas…",
            "optimize_svg": "Otimizando SVG…",
        }
        self.state.busy = True
        self.set_status(labels.get(action_id, f"Processando {action_id}…"))

        try:
            result = self._pipeline.run(action_id, self.state.project, **kwargs)
            self.state.project = result
            processed = result.processed_image_path
            self._publish_project()
            if processed is not None:
                self._bus.publish(
                    Event(
                        name=ui_events.PREVIEW_PROCESSED,
                        payload={"path": str(processed)},
                    )
                )
            if action_id in {"detect_objects", "separate_layers", "vectorize", "optimize_svg"}:
                self._bus.publish(
                    Event(
                        name=ui_events.LAYERS_UPDATED,
                        payload={
                            "count": len(result.layers),
                            "layer_ids": [layer.id for layer in result.layers],
                        },
                    )
                )
            if action_id in {"vectorize", "optimize_svg"} and result.svg_content:
                self._bus.publish(
                    Event(
                        name=ui_events.PREVIEW_SVG,
                        payload={"content": result.svg_content},
                    )
                )
            note = ""
            if result.ai_notes:
                note = f" · IA: {result.ai_notes[-1][:80]}"
            extra = ""
            if action_id == "detect_objects":
                extra = f" · {result.metadata.get('detection_count', 0)} objeto(s)"
            elif action_id == "separate_layers":
                extra = f" · {len(result.layers)} camada(s)"
            elif action_id == "vectorize":
                extra = f" · {result.metadata.get('vectorized_layers', 0)} path(s)"
            elif action_id == "optimize_svg":
                stats = result.metadata.get("optimize_stats", {})
                extra = (
                    f" · {stats.get('bytes_before', '?')}→{stats.get('bytes_after', '?')} bytes"
                )
            self.set_status(
                f"Concluído: {action_id.replace('_', ' ')} "
                f"({result.width}×{result.height}){extra}{note}"
            )
            self._bus.publish(
                Event(
                    name=ui_events.ACTION_COMPLETED,
                    payload={"action": action_id, "pending": False},
                )
            )
        except (ProcessorError, PluginError, ValueError) as exc:
            logger.exception("Pipeline action '%s' failed", action_id)
            self.set_status(f"Erro: {exc}")
            self._bus.publish(
                Event(
                    name=ui_events.ACTION_FAILED,
                    payload={"action": action_id, "error": str(exc)},
                )
            )
        finally:
            self.state.busy = False

    # ------------------------------------------------------------------ layers

    def select_layer(self, layer_id: str | None) -> None:
        """Set the currently selected layer and notify observers."""
        self.state.selected_layer_id = layer_id
        self._bus.publish(
            Event(name=ui_events.LAYER_SELECTED, payload={"layer_id": layer_id})
        )
        if layer_id:
            self.set_status(f"Camada selecionada: {layer_id}")

    def toggle_layer_visibility(self, layer_id: str) -> None:
        self._run_layer_command(
            ToggleVisibilityCommand(self._get_project, self._set_project, layer_id)
        )

    def set_layer_color(self, layer_id: str, color: str) -> None:
        self._run_layer_command(
            SetColorCommand(self._get_project, self._set_project, layer_id, color)
        )

    def set_layer_opacity(self, layer_id: str, opacity: float) -> None:
        self._run_layer_command(
            SetOpacityCommand(self._get_project, self._set_project, layer_id, opacity)
        )

    def move_layer(self, layer_id: str, delta: int) -> None:
        self._run_layer_command(
            MoveLayerCommand(self._get_project, self._set_project, layer_id, delta)
        )

    def delete_layer(self, layer_id: str) -> None:
        self._run_layer_command(
            DeleteLayerCommand(self._get_project, self._set_project, layer_id)
        )
        if self.state.selected_layer_id == layer_id:
            self.select_layer(None)

    def duplicate_layer(self, layer_id: str) -> None:
        self._run_layer_command(
            DuplicateLayerCommand(self._get_project, self._set_project, layer_id)
        )

    def translate_layer(self, layer_id: str, dx: float, dy: float) -> None:
        self._run_layer_command(
            TranslateLayerCommand(
                self._get_project, self._set_project, layer_id, dx, dy
            )
        )

    def undo(self) -> None:
        if self._history.undo():
            self._after_layer_edit("Undo")
        else:
            self.set_status("Nada para desfazer.")

    def redo(self) -> None:
        if self._history.redo():
            self._after_layer_edit("Redo")
        else:
            self.set_status("Nada para refazer.")

    def _get_project(self) -> ProjectDocument:
        return self.state.project

    def _set_project(self, project: ProjectDocument) -> None:
        self.state.project = project

    def _run_layer_command(self, command: object) -> None:
        from src.core.commands import Command

        assert isinstance(command, Command)
        self._history.execute(command)
        self._after_layer_edit(command.description)

    def _after_layer_edit(self, label: str) -> None:
        # Refresh SVG preview when vector paths exist
        if any(layer.path_data for layer in self.state.project.layers):
            try:
                svg = build_svg_document(self.state.project, pretty=False)
                self.state.project = self.state.project.model_copy(update={"svg_content": svg})
                self._bus.publish(
                    Event(name=ui_events.PREVIEW_SVG, payload={"content": svg})
                )
            except Exception:  # noqa: BLE001
                logger.exception("Failed to rebuild SVG after layer edit")

        self._publish_project()
        self._bus.publish(
            Event(
                name=ui_events.LAYERS_UPDATED,
                payload={
                    "count": len(self.state.project.layers),
                    "layer_ids": [layer.id for layer in self.state.project.layers],
                    "selected": self.state.selected_layer_id,
                },
            )
        )
        self.set_status(label)

    def _publish_project(self) -> None:
        self._bus.publish(
            Event(
                name=ui_events.PROJECT_UPDATED,
                payload={
                    "project_id": self.state.project.id,
                    "name": self.state.project.name,
                    "stage": self.state.project.stage.value,
                    "width": self.state.project.width,
                    "height": self.state.project.height,
                    "layers": len(self.state.project.layers),
                },
            )
        )

"""Export format identifiers and shared helpers."""

from __future__ import annotations

from enum import StrEnum


class ExportFormat(StrEnum):
    """Supported export targets (Stages 6–8)."""

    SVG = "svg"
    SVG_OPTIMIZED = "svg_optimized"
    SVG_ANIMATED = "svg_animated"
    JSON = "json"
    PNG = "png"
    WEBP = "webp"
    REACT = "react"
    VUE = "vue"
    ANGULAR = "angular"
    FLUTTER = "flutter"
    GODOT = "godot"
    UNITY = "unity"

    @property
    def label(self) -> str:
        """Human-readable label for dialogs."""
        return {
            ExportFormat.SVG: "SVG",
            ExportFormat.SVG_OPTIMIZED: "SVG otimizado",
            ExportFormat.SVG_ANIMATED: "SVG animado",
            ExportFormat.JSON: "JSON (layers)",
            ExportFormat.PNG: "PNG",
            ExportFormat.WEBP: "WEBP",
            ExportFormat.REACT: "React (.tsx)",
            ExportFormat.VUE: "Vue (.vue)",
            ExportFormat.ANGULAR: "Angular (.ts)",
            ExportFormat.FLUTTER: "Flutter (.dart)",
            ExportFormat.GODOT: "Godot (.gd)",
            ExportFormat.UNITY: "Unity (.cs)",
        }[self]

    @property
    def extension(self) -> str:
        """File extension including the dot."""
        return {
            ExportFormat.SVG: ".svg",
            ExportFormat.SVG_OPTIMIZED: ".svg",
            ExportFormat.SVG_ANIMATED: ".svg",
            ExportFormat.JSON: ".json",
            ExportFormat.PNG: ".png",
            ExportFormat.WEBP: ".webp",
            ExportFormat.REACT: ".tsx",
            ExportFormat.VUE: ".vue",
            ExportFormat.ANGULAR: ".component.ts",
            ExportFormat.FLUTTER: ".dart",
            ExportFormat.GODOT: ".gd",
            ExportFormat.UNITY: ".cs",
        }[self]

    @property
    def filetypes(self) -> list[tuple[str, str]]:
        """Tkinter filedialog filetypes."""
        return [(self.label, f"*{self.extension}"), ("Todos", "*.*")]

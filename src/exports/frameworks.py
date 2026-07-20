"""Framework exporters (React, Vue, Angular, Flutter, Godot, Unity)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.exceptions import ProcessorError
from src.core.interfaces import Exporter
from src.exports.animation import AnimationOptions, AnimationPreset, build_animated_svg
from src.exports.base import ExportFormat
from src.exports.codegen import layer_component_name, visible_layers
from src.models.project import ProjectDocument
from src.utils.svg_builder import save_svg


def _require_layers(project: ProjectDocument) -> None:
    if not visible_layers(project):
        raise ProcessorError("Nenhuma camada visível para exportar ao framework.")


def _escape_attr(value: str) -> str:
    """Escape for HTML/XML attribute context."""
    return (
        value.replace("&", "&amp;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
    )


def _escape_jsx_attr(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_csharp(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class AnimatedSvgExporter(Exporter):
    """SVG with fade-in animations on each layer group."""

    @property
    def format_id(self) -> str:
        return ExportFormat.SVG_ANIMATED.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        preset_raw = kwargs.get("preset", AnimationPreset.FADE_IN)
        preset = (
            preset_raw
            if isinstance(preset_raw, AnimationPreset)
            else AnimationPreset(str(preset_raw))
        )
        svg = build_animated_svg(
            project,
            options=AnimationOptions(
                preset=preset,
                duration_seconds=float(kwargs.get("duration", 0.8)),
                stagger_seconds=float(kwargs.get("stagger", 0.12)),
            ),
        )
        path = Path(destination)
        save_svg(str(path), svg)
        return str(path.resolve())


class ReactExporter(Exporter):
    """Export a single `.tsx` with one component per layer + Scene."""

    @property
    def format_id(self) -> str:
        return ExportFormat.REACT.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        layers = visible_layers(project)
        width = project.width or 100
        height = project.height or 100
        parts: list[str] = [
            "import type { SVGProps } from 'react';",
            "",
            "type LayerProps = SVGProps<SVGGElement>;",
            "",
        ]
        names: list[str] = []
        for layer in layers:
            name = layer_component_name(layer)
            names.append(name)
            parts.append(f"/** Layer `{layer.id}` ({layer.layer_type.value}) */")
            parts.append(f"export function {name}(props: LayerProps) {{")
            parts.append("  return (")
            parts.append(
                f'    <g id="{layer.id}" data-type="{layer.layer_type.value}" '
                f'opacity={{{layer.opacity}}} {{...props}}>'
            )
            parts.append(
                f'      <path d="{_escape_jsx_attr(layer.path_data)}" fill="{layer.color}" '
                f'stroke="none" fillRule="evenodd" />'
            )
            parts.append("    </g>")
            parts.append("  );")
            parts.append("}")
            parts.append("")

        parts.append("/** Composed scene */")
        parts.append("export function Scene(props: SVGProps<SVGSVGElement>) {")
        parts.append("  return (")
        parts.append(
            f'    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" {{...props}}>'
        )
        for name in names:
            parts.append(f"      <{name} />")
        parts.append("    </svg>")
        parts.append("  );")
        parts.append("}")
        parts.append("")
        parts.append("export default Scene;")
        parts.append("")

        path = Path(destination)
        if path.suffix.lower() not in {".tsx", ".jsx", ".ts", ".js"}:
            path = path.with_suffix(".tsx")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(parts), encoding="utf-8")
        return str(path.resolve())


class VueExporter(Exporter):
    """Export a Vue 3 SFC (`.vue`) with one group per layer in the template."""

    @property
    def format_id(self) -> str:
        return ExportFormat.VUE.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        layers = visible_layers(project)
        width = project.width or 100
        height = project.height or 100
        groups = []
        for layer in layers:
            name = layer_component_name(layer)
            groups.append(
                f"    <!-- <{name} /> -->\n"
                f'    <g id="{layer.id}" data-type="{layer.layer_type.value}" '
                f'opacity="{layer.opacity}">\n'
                f'      <path d="{_escape_attr(layer.path_data)}" fill="{layer.color}" '
                f'stroke="none" fill-rule="evenodd" />\n'
                f"    </g>"
            )
        content = f"""<script setup lang="ts">
/** Auto-generated by SVG Builder AI — layers: {", ".join(layer_component_name(L) for L in layers)} */
</script>

<template>
  <svg
    width="{width}"
    height="{height}"
    viewBox="0 0 {width} {height}"
    xmlns="http://www.w3.org/2000/svg"
  >
{chr(10).join(groups)}
  </svg>
</template>
"""
        path = Path(destination)
        if path.suffix.lower() != ".vue":
            path = path.with_suffix(".vue")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())


class AngularExporter(Exporter):
    """Export an Angular standalone component (`.ts`)."""

    @property
    def format_id(self) -> str:
        return ExportFormat.ANGULAR.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        layers = visible_layers(project)
        width = project.width or 100
        height = project.height or 100
        inner = []
        for layer in layers:
            inner.append(
                f'    <g id="{layer.id}" data-type="{layer.layer_type.value}" '
                f'[attr.opacity]="{layer.opacity}">\n'
                f'      <path d="{_escape_attr(layer.path_data)}" fill="{layer.color}" '
                f'stroke="none" fill-rule="evenodd" />\n'
                f"    </g>"
            )
        template = "\n".join(inner)
        content = f"""import {{ Component }} from '@angular/core';

@Component({{
  selector: 'app-svg-scene',
  standalone: true,
  template: `
  <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">
{template}
  </svg>
  `,
}})
export class SvgSceneComponent {{}}
"""
        path = Path(destination)
        if path.suffix.lower() != ".ts":
            path = path.with_name(path.stem + ".component.ts") if path.suffix else path.with_suffix(".component.ts")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())


class FlutterExporter(Exporter):
    """Export a Flutter `CustomPainter` widget (`.dart`)."""

    @property
    def format_id(self) -> str:
        return ExportFormat.FLUTTER.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        layers = visible_layers(project)
        width = float(project.width or 100)
        height = float(project.height or 100)
        paint_blocks = []
        for layer in layers:
            # Flutter can't easily parse full SVG path without package;
            # emit path data + Path() placeholder using parseSvgPathData hint.
            paint_blocks.append(
                f"""    // {layer.id}
    final paint{layer_component_name(layer)} = Paint()
      ..color = const Color(0xFF{_hex_to_flutter(layer.color)})
      ..style = PaintingStyle.fill;
    // Prefer `path_drawing` / `flutter_svg` packages for production path parsing.
    // pathData: {layer.path_data!r}
    canvas.drawRect(
      Rect.fromLTWH({layer.bounds.x}, {layer.bounds.y}, {layer.bounds.width}, {layer.bounds.height}),
      paint{layer_component_name(layer)}..color = paint{layer_component_name(layer)}.color.withOpacity({layer.opacity}),
    );
"""
            )
        content = f"""import 'package:flutter/material.dart';

/// Auto-generated by SVG Builder AI
class SvgScene extends StatelessWidget {{
  const SvgScene({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return CustomPaint(
      size: const Size({width}, {height}),
      painter: SvgScenePainter(),
    );
  }}
}}

class SvgScenePainter extends CustomPainter {{
  @override
  void paint(Canvas canvas, Size size) {{
{"".join(paint_blocks)}  }}

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}}
"""
        path = Path(destination)
        if path.suffix.lower() != ".dart":
            path = path.with_suffix(".dart")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())


class GodotExporter(Exporter):
    """Export a Godot 4 GDScript that builds Polygon2D / Path2D placeholders."""

    @property
    def format_id(self) -> str:
        return ExportFormat.GODOT.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        layers = visible_layers(project)
        lines = [
            "extends Node2D",
            "# Auto-generated by SVG Builder AI",
            "",
            "func _ready() -> void:",
        ]
        for layer in layers:
            name = layer_component_name(layer)
            lines.append(f'	var {name.lower()} := Polygon2D.new()')
            lines.append(f'	{name.lower()}.name = "{layer.id}"')
            lines.append(
                f'	{name.lower()}.color = Color("{layer.color}")'
            )
            lines.append(f"	{name.lower()}.modulate.a = {layer.opacity}")
            # Approximate with bounding quad — full path parsing can use Curve2D later
            x, y, w, h = layer.bounds.x, layer.bounds.y, layer.bounds.width, layer.bounds.height
            lines.append(
                f"	{name.lower()}.polygon = PackedVector2Array(["
                f"Vector2({x}, {y}), Vector2({x + w}, {y}), "
                f"Vector2({x + w}, {y + h}), Vector2({x}, {y + h})])"
            )
            lines.append(f'	{name.lower()}.set_meta("svg_path", "{_escape_csharp(layer.path_data)}")')
            lines.append(f"	add_child({name.lower()})")
            lines.append("")
        path = Path(destination)
        if path.suffix.lower() != ".gd":
            path = path.with_suffix(".gd")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        return str(path.resolve())


class UnityExporter(Exporter):
    """Export a Unity C# MonoBehaviour that rebuilds UI Toolkit / Vector paths metadata."""

    @property
    def format_id(self) -> str:
        return ExportFormat.UNITY.value

    def export(self, project: ProjectDocument, destination: str, **kwargs: Any) -> str:
        _require_layers(project)
        layers = visible_layers(project)
        entries = []
        for layer in layers:
            entries.append(
                "        new SvgLayer {\n"
                f'            id = "{layer.id}",\n'
                f'            type = "{layer.layer_type.value}",\n'
                f'            color = "{layer.color}",\n'
                f"            opacity = {layer.opacity}f,\n"
                f'            path = "{_escape_csharp(layer.path_data)}",\n'
                f"            bounds = new Rect({layer.bounds.x}f, {layer.bounds.y}f, "
                f"{layer.bounds.width}f, {layer.bounds.height}f)\n"
                "        }"
            )
        layers_array = ",\n".join(entries)
        content = f"""using System;
using UnityEngine;

/// <summary>Auto-generated by SVG Builder AI</summary>
[Serializable]
public class SvgLayer
{{
    public string id;
    public string type;
    public string color;
    public float opacity;
    public string path;
    public Rect bounds;
}}

public class SvgSceneBehaviour : MonoBehaviour
{{
    public float width = {project.width or 100}f;
    public float height = {project.height or 100}f;

    public SvgLayer[] layers = new SvgLayer[]
    {{
{layers_array}
    }};

    // Hook these into UI Toolkit Vector API, LineRenderer, or a SVG importer asset.
}}
"""
        path = Path(destination)
        if path.suffix.lower() != ".cs":
            path = path.with_suffix(".cs")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.resolve())


def _hex_to_flutter(color: str) -> str:
    c = color.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    if len(c) != 6:
        return "808080"
    return c.upper()

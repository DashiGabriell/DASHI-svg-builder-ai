# Optimize & export (Stage 6)

## Optimize

Processor: `optimize_svg` → stage `OPTIMIZED`

- Round path coordinates (`precision`, default 2)
- Remove empty `<g>` / empty paths
- Deduplicate identical `d` + fill
- Minify whitespace
- Stats in `project.metadata["optimize_stats"]`
- File: `cache/<id>/optimized.svg`

## Export formats

| Format | Exporter | Notes |
|--------|----------|-------|
| SVG | `SvgExporter` | Current `svg_content` |
| SVG otimizado | `OptimizedSvgExporter` | Runs optimizer on export |
| JSON | `JsonExporter` | `to_layers_json()` |
| PNG | `PngExporter` | CairoSVG or Pillow composite |
| WEBP | `WebpExporter` | Same raster path |

UI: **Exportar** → format dialog → save file dialog.

## Modules

- `src/utils/svg_optimizer.py`
- `src/processors/processor_optimize_svg.py`
- `src/exports/` (`ExportService` + Strategy exporters)
- `src/ui/components/export_dialog.py`

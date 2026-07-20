# Framework exporters & SVG animations (Stage 8)

## Formats

| Format | File | Notes |
|--------|------|-------|
| React | `.tsx` | Components `<Building01/>` … + `Scene` |
| Vue | `.vue` | SFC with commented component names + `<g>` layers |
| Angular | `.component.ts` | Standalone `SvgSceneComponent` |
| Flutter | `.dart` | `CustomPainter` (bounds + path metadata) |
| Godot | `.gd` | `Polygon2D` nodes + `svg_path` meta |
| Unity | `.cs` | `SvgSceneBehaviour` + `SvgLayer[]` |
| SVG animado | `.svg` | CSS + SMIL fade-in per layer |

## Animation

`src/exports/animation.py` — presets: `fade_in`, `pulse`, `draw`.

## Codegen

`building_01` → `Building01` via `to_pascal_case` / `layer_component_name`.

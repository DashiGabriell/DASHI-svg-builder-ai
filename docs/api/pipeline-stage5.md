# Per-layer vectorization (Stage 5)

## Rule

> Each layer is traced independently. The artwork is **never** collapsed into a single SVG path.

## Engine

- **Potrace** via [`potracer`](https://pypi.org/project/potracer/) (pure-Python port)
- Import surface: `from potrace import Bitmap` (same API as classic bindings)
- Binary mask → invert (Potrace expects dark foreground) → `Bitmap.trace()` → SVG `d`

## Processor

| Action | Plugin | Stage |
|--------|--------|-------|
| Vetorizar | `vectorize` | `VECTORIZED` |

Parameters: `turdsize`, `alphamax`, `opttolerance`, `opticurve`.

## Output

```xml
<svg viewBox="0 0 W H">
  <g id="svg_builder_root">
    <g id="building_01" data-type="building">
      <path d="M..." fill="#202020"/>
    </g>
    <g id="tree_01" data-type="tree">
      <path d="M..." fill="#228822"/>
    </g>
  </g>
</svg>
```

Also written to `cache/<project_id>/vectorized.svg` and shown in the SVG preview panel.

## Modules

- `src/utils/potrace_trace.py` — mask → path `d`
- `src/utils/svg_builder.py` — layers → modular SVG (`svgwrite`)
- `src/processors/processor_vectorize.py` — pipeline plugin

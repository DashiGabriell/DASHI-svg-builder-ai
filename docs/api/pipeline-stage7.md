# Interactive canvas & layer CRUD (Stage 7)

## Layout

```
Original | Interactive Canvas | SVG Final
──────────────── Layers panel (inspector) ────────────────
```

## Canvas

| Gesture | Action |
|---------|--------|
| Scroll / +− | Zoom |
| RMB or MMB drag | Pan |
| LMB click | Select layer |
| LMB drag | Move layer (TranslateLayerCommand) |
| Grid / Fit | Toolbar |

## Layer CRUD (Command Pattern + undo/redo)

- Toggle visibility
- Set color / opacity
- Move z-index ↑↓
- Duplicate
- Delete
- Ctrl+Z / Ctrl+Y

Commands live in `src/core/commands/layer_commands.py`.

## Modules

- `src/ui/components/interactive_canvas.py`
- `src/ui/components/layers_panel.py` (inspector)
- `AppController` layer edit API

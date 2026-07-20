# Object detection & layer separation (Stage 4)

## Flow

```
raster (prefer no_background)
        ↓
detect_objects  →  contours / connected_components
        ↓
detections_overlay.png + mask_XX.png
        ↓
separate_layers → Layer[] + semantic ids + optional AI labels
        ↓
layers_preview.png + UI LayersPanel
```

## Processors

| Action | Plugin | Stage |
|--------|--------|-------|
| Detectar objetos | `detect_objects` | `OBJECTS_DETECTED` |
| Separar camadas | `separate_layers` | `LAYERS_SEPARATED` |

## Detection

- Default: **contours** (`cv2.findContours` RETR_EXTERNAL)
- Optional: `method="connected_components"`
- Foreground from alpha (after BG removal) or Otsu fallback

## Layers

- Each object → `Layer` with mask PNG, bounds, dominant color
- IDs: `building_01`, `tree_02`, … via `assign_semantic_ids`
- Offline fallback type: `other`
- Optional: `AIService.classify_objects` for semantic types

## Repository

`InMemoryLayerRepository` implements the Repository Pattern over `list[Layer]`.

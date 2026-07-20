# Raster pipeline (Stage 3)

## Processors

| Plugin name | Class | Stage |
|-------------|-------|-------|
| `load_image` | `LoadImageProcessor` | `LOADED` |
| `enhance_quality` | `UpscaleProcessor` | `UPSCALE` |
| `remove_background` | `RemoveBackgroundProcessor` | `BACKGROUND_REMOVED` |

## Algorithms

### Upscale (offline)

1. Bilateral denoise  
2. scikit-image Lanczos resize (`scale`, default 2×)  
3. Unsharp mask  

Optional: `AIService.suggest_structure` writes an advisory note to `project.ai_notes` (never affects pixels).

### Background removal (offline)

Default: **flood-fill from borders** (illustrations / logos).  
Also: `method="grabcut"` | `"threshold"`.

## Orchestration

`PipelineService` maps sidebar actions → plugins and injects `cache_dir` + `AIService`.

Outputs live under `cache/<project_id>/` (`original.png`, `upscaled.png`, `no_background.png`).

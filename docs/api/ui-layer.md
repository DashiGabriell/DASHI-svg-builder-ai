# Desktop UI (Stage 2)

## Layout

```
┌────────────┬──────────────────────────────────────────────┐
│ SVG Builder│ Workspace                                    │
│ AI         │ Original → Processada → SVG Final            │
│            ├──────────┬──────────┬────────────────────────┤
│ Importar   │ Original │ Processed│ SVG                    │
│ Qualidade  │ preview  │ preview  │ preview                │
│ Remover BG │          │          │                        │
│ Detectar   │          │          │                        │
│ Camadas    │          │          │                        │
│ Vetorizar  │          │          │                        │
│ Otimizar   │          │          │                        │
│ Exportar   │          │          │                        │
├────────────┴──────────┴──────────┴────────────────────────┤
│ ● status …                    Estágio | IA                │
└───────────────────────────────────────────────────────────┘
```

## Key classes

| Class | Role |
|-------|------|
| `run_app` | Composition entry for the Tk mainloop |
| `MainWindow` | Root window; wires dialogs + Observer subscriptions |
| `Sidebar` | Pipeline action rail |
| `PreviewPanel` | Raster / text preview slot |
| `StatusBar` | Footer feedback |
| `AppController` | Import + pending action dispatch |
| `AppState` | Current `ProjectDocument` + status |

## Events

- `project.updated`
- `status.message`
- `preview.original` / `preview.processed` / `preview.svg`
- `action.requested` / `action.completed` / `action.failed`

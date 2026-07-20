# Internal Classes (Stage 1)

## Config

- `Settings` — pydantic-settings model (`OPENROUTER_*`, paths, env)
- `get_settings()` — cached singleton

## Core

- `Container` / `get_container()` — DI
- `EventBus` / `Event` — Observer
- `Command` / `CommandHistory` — undo/redo foundation
- `Processor`, `Exporter`, `LayerRepository`, `AIClientProtocol` — interfaces
- `build_container()` — composition root

## Models

- `Bounds`, `Layer`, `LayerType`, `ProjectDocument`, `PipelineStage`

## Processors

- `BaseProcessor` — Strategy base with logging
- `PluginRegistry` — Factory + discovery via `discover("src.processors")`

## Exceptions

`SVGBuilderError` → `ConfigurationError`, `OpenRouterError`, `AIServiceError`, `ProcessorError`, `PluginError`

# Architecture Overview — Stage 1

## Goals

- Clean separation of UI, application services, domain models and infrastructure.
- AI fully decoupled behind `AIService` / `OpenRouterClient`.
- Processors as replaceable Strategies registered via plugins.
- Offline-first vectorization path.

## Layer diagram

```mermaid
flowchart TB
    subgraph UI["UI (CustomTkinter) — Stage 2+"]
        Views
        Components
    end

    subgraph Application["Application"]
        Bootstrap[bootstrap.py]
        AIService
        EventBus
        CommandHistory
        PluginRegistry
    end

    subgraph Domain["Domain"]
        ProjectDocument
        Layer
        ProcessorInterface[Processor ABC]
    end

    subgraph Infra["Infrastructure"]
        Settings
        OpenRouterClient
        Logging
        FutureCV[OpenCV / Potrace — Stage 3+]
    end

    Views --> EventBus
    Views --> CommandHistory
    Views --> AIService
    Views --> PluginRegistry
    PluginRegistry --> ProcessorInterface
    ProcessorInterface --> ProjectDocument
    AIService --> OpenRouterClient
    Bootstrap --> Settings
    Bootstrap --> AIService
    Bootstrap --> PluginRegistry
    OpenRouterClient --> OpenRouter[(OpenRouter API)]
    FutureCV --> ProjectDocument
```

## Pipeline (planned)

```mermaid
flowchart LR
    A[Load Image] --> B[Upscale]
    B --> C[Remove BG]
    C --> D[Detect Objects]
    D --> E[Separate Layers]
    E --> F[Vectorize per layer]
    F --> G[Optimize SVG]
    G --> H[Export]
    D -.->|optional labels| AI[AIService]
    B -.->|structure hints| AI
```

## Dependency rule

Inner layers never import UI. Infrastructure adapters are injected from `src/core/bootstrap.py`.

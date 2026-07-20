# AI Layer API

## `OpenRouterClient`

Low-level async HTTP client for `POST /chat/completions`.

| Method | Description |
|--------|-------------|
| `chat_completion(messages, model=None, ...)` | Sends chat request; retries transport errors |
| `extract_text(response)` | Pulls assistant content from JSON |
| `aclose()` | Closes owned `httpx.AsyncClient` |

Raises:

- `ConfigurationError` — missing `OPENROUTER_API_KEY`
- `OpenRouterError` — HTTP / shape errors (`status_code`, `response_body`)

## `AIService`

High-level façade. Configurable model at construction or via `set_model()`.

| Method | Role |
|--------|------|
| `chat(messages)` | Generic text completion |
| `classify_objects(descriptions)` | Semantic labels for CV regions |
| `suggest_structure(scene_description)` | Grouping / organization hints |
| `describe_image_context(notes)` | Short scene prose |

When `enabled=False` (no API key), classify/suggest return empty results instead of calling the network.

## Principle

> AI analyses. Local CV vectorizes.

"""Unit tests for OpenRouterClient and AIService (HTTP mocked)."""

from __future__ import annotations

import httpx
import pytest
import respx

from src.config.settings import Settings
from src.core.exceptions import AIServiceError, ConfigurationError, OpenRouterError
from src.services.ai import AIService, OpenRouterClient
from src.services.ai.schemas import ChatMessage, ChatRole


def _chat_response(content: str, model: str = "deepseek/deepseek-chat") -> dict:
    return {
        "id": "gen-test",
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
    }


@pytest.mark.unit
@pytest.mark.asyncio
async def test_openrouter_client_requires_api_key(tmp_path) -> None:
    settings = Settings(
        OPENROUTER_API_KEY="",
        LOGS_DIR=str(tmp_path / "logs"),
        CACHE_DIR=str(tmp_path / "cache"),
        EXPORTS_DIR=str(tmp_path / "exports"),
        ASSETS_DIR=str(tmp_path / "assets"),
    )
    client = OpenRouterClient(settings)
    with pytest.raises(ConfigurationError):
        await client.chat_completion([{"role": "user", "content": "hi"}])
    await client.aclose()


@pytest.mark.unit
@pytest.mark.asyncio
@respx.mock
async def test_openrouter_chat_completion_success(clean_env: Settings) -> None:
    route = respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_response("hello"))
    )
    async with OpenRouterClient(clean_env) as client:
        data = await client.chat_completion([{"role": "user", "content": "ping"}])
        assert OpenRouterClient.extract_text(data) == "hello"
    assert route.called


@pytest.mark.unit
@pytest.mark.asyncio
@respx.mock
async def test_openrouter_error_status(clean_env: Settings) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(401, text="unauthorized")
    )
    async with OpenRouterClient(clean_env) as client:
        with pytest.raises(OpenRouterError) as exc_info:
            await client.chat_completion([{"role": "user", "content": "ping"}])
        assert exc_info.value.status_code == 401


@pytest.mark.unit
@pytest.mark.asyncio
@respx.mock
async def test_ai_service_classify_objects(clean_env: Settings) -> None:
    payload = {
        "labels": [
            {
                "label": "building",
                "confidence": 0.95,
                "suggested_id": "building_01",
                "description": "tall structure",
            },
            {
                "label": "tree",
                "confidence": 0.8,
                "suggested_id": "tree_01",
                "description": "green canopy",
            },
        ]
    }
    import json

    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=_chat_response(json.dumps(payload)))
    )

    async with OpenRouterClient(clean_env) as client:
        service = AIService(client, default_model=clean_env.openrouter_model)
        result = await service.classify_objects(
            ["region A dark rectangle", "region B green blob"]
        )

    assert len(result.labels) == 2
    assert result.labels[0].label == "building"
    assert result.labels[1].suggested_id == "tree_01"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ai_service_disabled_skips_network(clean_env: Settings) -> None:
    async with OpenRouterClient(clean_env) as client:
        service = AIService(client, enabled=False)
        result = await service.classify_objects(["anything"])
        assert result.labels == []


@pytest.mark.unit
@pytest.mark.asyncio
@respx.mock
async def test_ai_service_chat_wraps_errors(clean_env: Settings) -> None:
    respx.post("https://openrouter.ai/api/v1/chat/completions").mock(
        return_value=httpx.Response(500, text="boom")
    )
    async with OpenRouterClient(clean_env) as client:
        service = AIService(client)
        with pytest.raises(AIServiceError):
            await service.chat([ChatMessage(role=ChatRole.USER, content="hi")])

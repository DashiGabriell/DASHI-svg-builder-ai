"""HTTP client for the OpenRouter API (OpenAI-compatible chat completions)."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.settings import Settings
from src.core.exceptions import ConfigurationError, OpenRouterError

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Low-level async client for OpenRouter.

    All vendor models (DeepSeek, Qwen, Claude, GPT, Gemini, …) are reached
    exclusively through this client. Direct OpenAI / Anthropic / Google SDKs
    must never be used in this project.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Create a client bound to application settings.

        Args:
            settings: Typed settings containing OpenRouter credentials.
            http_client: Optional injected httpx client (useful in tests).
        """
        self._settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.openrouter_base_url.rstrip("/"),
            timeout=settings.openrouter_timeout_seconds,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        """Build OpenRouter-required HTTP headers."""
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "HTTP-Referer": self._settings.openrouter_site_url,
            "X-Title": self._settings.openrouter_app_name,
        }
        if self._settings.openrouter_api_key.strip():
            headers["Authorization"] = f"Bearer {self._settings.openrouter_api_key.strip()}"
        return headers

    def _ensure_configured(self) -> None:
        """Raise if the API key is missing."""
        if not self._settings.is_ai_configured:
            raise ConfigurationError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and add your key."
            )

    async def chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call ``POST /chat/completions`` and return the JSON body.

        Args:
            messages: OpenAI-compatible message list.
            model: Override for ``OPENROUTER_MODEL`` (e.g. ``anthropic/claude-3.5-sonnet``).
            temperature: Sampling temperature.
            max_tokens: Optional completion budget.
            response_format: Optional structured output hint.
            extra_body: Extra fields merged into the request body.

        Returns:
            Parsed JSON response from OpenRouter.

        Raises:
            ConfigurationError: Missing API key.
            OpenRouterError: HTTP / transport failure.
        """
        self._ensure_configured()
        resolved_model = model or self._settings.openrouter_model

        body: dict[str, Any] = {
            "model": resolved_model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if response_format is not None:
            body["response_format"] = response_format
        if extra_body:
            body.update(extra_body)

        logger.info(
            "OpenRouter chat_completion model=%s messages=%d",
            resolved_model,
            len(messages),
        )
        return await self._post_chat_completions(body)

    async def _post_chat_completions(self, body: dict[str, Any]) -> dict[str, Any]:
        """Execute the HTTP POST with retries."""
        max_attempts = max(1, self._settings.openrouter_max_retries + 1)

        @retry(
            reraise=True,
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        )
        async def _do_request() -> dict[str, Any]:
            try:
                response = await self._client.post("/chat/completions", json=body)
            except httpx.TimeoutException as exc:
                logger.warning("OpenRouter request timed out: %s", exc)
                raise
            except httpx.TransportError as exc:
                logger.warning("OpenRouter transport error: %s", exc)
                raise

            if response.status_code >= 400:
                logger.error(
                    "OpenRouter error status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
                raise OpenRouterError(
                    f"OpenRouter request failed with status {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text,
                )

            data = response.json()
            logger.debug("OpenRouter response keys=%s", list(data.keys()))
            return data

        return await _do_request()

    @staticmethod
    def extract_text(response: dict[str, Any]) -> str:
        """Extract assistant text content from a chat completion response."""
        try:
            choices = response["choices"]
            message = choices[0]["message"]
            content = message.get("content", "")
            if isinstance(content, list):
                # Multimodal content blocks
                texts = [
                    block.get("text", "")
                    for block in content
                    if isinstance(block, dict) and block.get("type") == "text"
                ]
                return "\n".join(t for t in texts if t)
            return str(content)
        except (KeyError, IndexError, TypeError) as exc:
            raise OpenRouterError(
                "Unexpected OpenRouter response shape; cannot extract text.",
                response_body=str(response)[:1000],
            ) from exc

    async def aclose(self) -> None:
        """Close the underlying HTTP client when owned by this instance."""
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> OpenRouterClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.aclose()

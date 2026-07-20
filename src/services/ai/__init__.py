"""AI integration package — OpenRouter is the sole external gateway."""

from src.services.ai.ai_service import AIService
from src.services.ai.openrouter_client import OpenRouterClient
from src.services.ai.schemas import (
    ChatMessage,
    ChatRole,
    ClassificationResult,
    ObjectLabel,
    StructureSuggestion,
)

__all__ = [
    "AIService",
    "ChatMessage",
    "ChatRole",
    "ClassificationResult",
    "ObjectLabel",
    "OpenRouterClient",
    "StructureSuggestion",
]

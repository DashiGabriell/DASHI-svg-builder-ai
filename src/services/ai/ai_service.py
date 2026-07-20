"""High-level AI façade — analysis only, never the vectorization source of truth."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from src.core.exceptions import AIServiceError, ConfigurationError, OpenRouterError
from src.services.ai.openrouter_client import OpenRouterClient
from src.services.ai.schemas import (
    ChatMessage,
    ChatRole,
    ClassificationResult,
    ObjectLabel,
    StructureSuggestion,
)

logger = logging.getLogger(__name__)

# System prompts keep the model in an advisory role (offline CV does the work).
_CLASSIFY_SYSTEM = """You are an expert visual analyst assisting an offline SVG vectorization pipeline.
Your job is ONLY to classify detected image regions with semantic labels.
Respond with a JSON object of the form:
{"labels":[{"label":"building","confidence":0.92,"suggested_id":"building_01","description":"..."}]}
Use lowercase snake_case labels from this set when possible:
building, tree, lamp, panel, neon, road, vehicle, person, sky, smoke, window, light,
background, foreground, text, icon, other.
Never invent SVG paths. Never claim to have vectorized anything."""

_STRUCTURE_SYSTEM = """You are an expert in illustration structure and SVG layer organization.
Given a description of an artwork, suggest structural improvements for modular SVG export.
Respond with JSON:
{"summary":"...","improvements":["..."],"grouping_hints":["..."]}
Do NOT generate SVG markup. Analysis and suggestions only."""


class AIService:
    """Application-facing AI API.

    Responsibilities (analysis only):
    - classify detected objects
    - suggest layer names / IDs
    - propose groupings
    - describe scenes for operator review

    Non-responsibilities:
    - never produces SVG paths
    - never replaces OpenCV / Potrace vectorization
    - never talks to vendor APIs except via OpenRouterClient
    """

    def __init__(
        self,
        client: OpenRouterClient,
        *,
        default_model: str | None = None,
        enabled: bool = True,
    ) -> None:
        """Create the service.

        Args:
            client: Injected OpenRouterClient.
            default_model: Optional model override (DeepSeek, Claude, GPT, …).
            enabled: When False, methods return empty advisory results.
        """
        self._client = client
        self._default_model = default_model
        self._enabled = enabled

    @property
    def is_enabled(self) -> bool:
        """Whether AI calls are currently active."""
        return self._enabled

    def set_model(self, model: str) -> None:
        """Switch the default model for subsequent calls (e.g. ``openai/gpt-4o``)."""
        self._default_model = model
        logger.info("AIService default model set to %s", model)

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Generic chat helper returning plain text.

        Raises:
            AIServiceError: On provider or configuration failure.
        """
        self._assert_enabled()
        try:
            response = await self._client.chat_completion(
                [m.to_api_dict() for m in messages],
                model=model or self._default_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return self._client.extract_text(response)
        except (OpenRouterError, ConfigurationError) as exc:
            raise AIServiceError(str(exc)) from exc

    async def classify_objects(
        self,
        object_descriptions: list[str],
        *,
        model: str | None = None,
    ) -> ClassificationResult:
        """Ask the model to label detected objects/regions.

        Args:
            object_descriptions: Human/CV-produced descriptions of each region
                (geometry stats, dominant color, rough position, …).
            model: Optional OpenRouter model id.

        Returns:
            ClassificationResult with semantic labels (empty if AI disabled).
        """
        if not self._enabled:
            logger.info("AIService disabled — skipping classify_objects")
            return ClassificationResult(labels=[], raw_text="", model="")

        if not object_descriptions:
            return ClassificationResult(labels=[], raw_text="", model=model or "")

        numbered = "\n".join(f"{i + 1}. {desc}" for i, desc in enumerate(object_descriptions))
        user_prompt = (
            "Classify each numbered region below. Return one label entry per region, "
            f"preserving order.\n\n{numbered}"
        )

        try:
            text = await self.chat(
                [
                    ChatMessage(role=ChatRole.SYSTEM, content=_CLASSIFY_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=user_prompt),
                ],
                model=model,
                temperature=0.1,
            )
        except AIServiceError:
            raise
        except Exception as exc:  # noqa: BLE001 — wrap unexpected failures
            raise AIServiceError(f"classify_objects failed: {exc}") from exc

        labels = self._parse_labels(text, expected=len(object_descriptions))
        resolved_model = model or self._default_model or ""
        return ClassificationResult(labels=labels, raw_text=text, model=resolved_model)

    async def suggest_structure(
        self,
        scene_description: str,
        *,
        model: str | None = None,
    ) -> StructureSuggestion:
        """Request structural improvement hints for an artwork description."""
        if not self._enabled:
            logger.info("AIService disabled — skipping suggest_structure")
            return StructureSuggestion()

        try:
            text = await self.chat(
                [
                    ChatMessage(role=ChatRole.SYSTEM, content=_STRUCTURE_SYSTEM),
                    ChatMessage(role=ChatRole.USER, content=scene_description),
                ],
                model=model,
                temperature=0.3,
            )
        except AIServiceError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise AIServiceError(f"suggest_structure failed: {exc}") from exc

        data = self._extract_json_object(text) or {}
        return StructureSuggestion(
            summary=str(data.get("summary", "")),
            improvements=[str(x) for x in data.get("improvements", [])],
            grouping_hints=[str(x) for x in data.get("grouping_hints", [])],
            model=model or self._default_model or "",
            raw_text=text,
        )

    async def describe_image_context(
        self,
        caption_or_stats: str,
        *,
        model: str | None = None,
    ) -> str:
        """Produce a short scene description from CV-derived stats / caption."""
        if not self._enabled:
            return ""

        prompt = (
            "Given the following image analysis notes, write a concise scene description "
            "(max 120 words) to help an artist organize SVG layers. Notes:\n"
            f"{caption_or_stats}"
        )
        return await self.chat(
            [
                ChatMessage(
                    role=ChatRole.SYSTEM,
                    content="You write concise visual scene descriptions. No SVG.",
                ),
                ChatMessage(role=ChatRole.USER, content=prompt),
            ],
            model=model,
            temperature=0.4,
            max_tokens=300,
        )

    def _assert_enabled(self) -> None:
        if not self._enabled:
            raise AIServiceError("AIService is disabled.")

    def _parse_labels(self, text: str, *, expected: int) -> list[ObjectLabel]:
        """Parse model JSON into ObjectLabel list with graceful fallback."""
        data = self._extract_json_object(text)
        labels: list[ObjectLabel] = []

        if data and isinstance(data.get("labels"), list):
            for item in data["labels"]:
                if not isinstance(item, dict):
                    continue
                try:
                    labels.append(ObjectLabel.model_validate(item))
                except Exception:  # noqa: BLE001
                    logger.warning("Skipping invalid label payload: %s", item)

        # Fallback: ensure we always return expected count for pipeline stability
        while len(labels) < expected:
            idx = len(labels) + 1
            labels.append(
                ObjectLabel(
                    label="other",
                    confidence=0.0,
                    suggested_id=f"other_{idx:02d}",
                    description="unclassified",
                )
            )
        return labels[:expected]

    @staticmethod
    def _extract_json_object(text: str) -> dict[str, Any] | None:
        """Best-effort extraction of a JSON object from model output."""
        text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from model response")
            return None

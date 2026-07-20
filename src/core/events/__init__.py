"""Observer-pattern event bus for UI and pipeline updates."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True, slots=True)
class Event:
    """Immutable domain/UI event payload."""

    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class EventBus:
    """Publish/subscribe bus used for Observer updates across layers.

    Processors and services emit events; the UI (and other observers)
    subscribe without creating circular dependencies.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register a handler for a named event."""
        self._subscribers[event_name].append(handler)
        logger.debug("Subscribed %s to event '%s'", getattr(handler, "__name__", handler), event_name)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered handler."""
        handlers = self._subscribers.get(event_name, [])
        if handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Event) -> None:
        """Notify all subscribers of an event.

        Handler exceptions are logged and swallowed so one bad observer
        cannot break the pipeline.
        """
        handlers = list(self._subscribers.get(event.name, []))
        # Also notify wildcard listeners ("*")
        handlers.extend(self._subscribers.get("*", []))

        logger.debug("Publishing event '%s' to %d handler(s)", event.name, len(handlers))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Event handler failed for '%s'", event.name)

    def clear(self) -> None:
        """Remove all subscriptions."""
        self._subscribers.clear()

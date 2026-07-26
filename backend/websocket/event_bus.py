"""
Simple async event bus for decoupled real-time communication.

Services and API routes emit events; the ConnectionManager and
NotificationService subscribe.  No FastAPI dependency.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from typing import Any

logger = logging.getLogger(__name__)

# Type alias for async event handlers
EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventBus:
    """In-process pub/sub event bus.

    Callers ``emit(event_type, payload)``; subscribers register via
    ``subscribe(event_type, handler)``.  All handlers run concurrently.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register *handler* to be called whenever *event_type* fires."""
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to '%s'", handler.__qualname__, event_type)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove *handler* from the subscriber list for *event_type*."""
        try:
            self._subscribers[event_type].remove(handler)
        except ValueError:
            pass

    async def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        """Fire *event_type* with *payload* to all registered handlers.

        Handlers are gathered and run concurrently.  Exceptions are
        logged but never propagate to the caller.
        """
        handlers = self._subscribers.get(event_type, [])
        if not handlers:
            return

        results = await asyncio.gather(
            *(self._safe_call(h, event_type, payload) for h in handlers),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, Exception):
                logger.error(
                    "Handler error for '%s': %s", event_type, result, exc_info=result
                )

    @staticmethod
    async def _safe_call(
        handler: EventHandler, event_type: str, payload: dict[str, Any]
    ) -> None:
        try:
            await handler(payload)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Handler %s failed for '%s': %s",
                handler.__qualname__,
                event_type,
                exc,
                exc_info=exc,
            )


# Module-level singleton
event_bus = EventBus()

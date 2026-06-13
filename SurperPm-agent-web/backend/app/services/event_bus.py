"""In-process async pub/sub event bus."""
from collections import defaultdict
from typing import Any, Awaitable, Callable

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler):
        self._handlers[event].append(handler)

    async def emit(self, event: str, payload: dict[str, Any]):
        for handler in self._handlers[event]:
            await handler(payload)


bus = EventBus()

"""In-process async pub/sub event bus."""
from collections import defaultdict
from typing import Any, Awaitable, Callable

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]

GOAL_CREATED = "goal_created"
GOAL_UPDATED = "goal_updated"
EXECUTION_STARTED = "execution_started"
EXECUTION_PROGRESS = "execution_progress"
EXECUTION_COMPLETED = "execution_completed"
DISCUSSION_CREATED = "discussion_created"
WORKSPACE_CREATED = "workspace_created"
WORKSPACE_UPDATED = "workspace_updated"
KNOWLEDGE_UPDATED = "knowledge_updated"

ALL_EVENTS = [
    GOAL_CREATED, GOAL_UPDATED,
    EXECUTION_STARTED, EXECUTION_PROGRESS, EXECUTION_COMPLETED,
    DISCUSSION_CREATED,
    WORKSPACE_CREATED, WORKSPACE_UPDATED,
    KNOWLEDGE_UPDATED,
]


class EventBus:
    def __init__(self):
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)

    def on(self, event: str, handler: EventHandler):
        self._handlers[event].append(handler)

    def off(self, event: str, handler: EventHandler):
        handlers = self._handlers.get(event, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(self, event: str, payload: dict[str, Any]):
        for handler in self._handlers[event]:
            await handler(payload)


bus = EventBus()

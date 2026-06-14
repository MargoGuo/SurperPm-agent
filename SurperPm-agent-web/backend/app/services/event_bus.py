"""In-process async pub/sub event bus."""
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

_logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], Awaitable[None]]

GOAL_CREATED = "goal_created"
GOAL_UPDATED = "goal_updated"
EXECUTION_STARTED = "execution_started"
EXECUTION_PROGRESS = "execution_progress"
EXECUTION_COMPLETED = "execution_completed"
DISCUSSION_CREATED = "discussion_created"
DISCUSSION_DELTA = "discussion_delta"
WORKSPACE_CREATED = "workspace_created"
WORKSPACE_UPDATED = "workspace_updated"
KNOWLEDGE_UPDATED = "knowledge_updated"
TOPIC_CREATED = "topic_created"
TOPIC_UPDATED = "topic_updated"

SKILL_CREATED = "skill_created"
SKILL_UPDATED = "skill_updated"
SKILL_DELETED = "skill_deleted"

MCP_SERVER_CREATED = "mcp_server_created"
MCP_SERVER_UPDATED = "mcp_server_updated"
MCP_SERVER_DELETED = "mcp_server_deleted"

ALL_EVENTS = [
    GOAL_CREATED, GOAL_UPDATED,
    EXECUTION_STARTED, EXECUTION_PROGRESS, EXECUTION_COMPLETED,
    DISCUSSION_CREATED, DISCUSSION_DELTA,
    WORKSPACE_CREATED, WORKSPACE_UPDATED,
    KNOWLEDGE_UPDATED,
    TOPIC_CREATED, TOPIC_UPDATED,
    SKILL_CREATED, SKILL_UPDATED, SKILL_DELETED,
    MCP_SERVER_CREATED, MCP_SERVER_UPDATED, MCP_SERVER_DELETED,
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
            try:
                await handler(payload)
            except Exception:
                _logger.exception("EventBus handler error for event=%s", event)


bus = EventBus()

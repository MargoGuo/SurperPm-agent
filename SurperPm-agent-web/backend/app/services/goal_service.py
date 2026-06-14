"""Unified Goal factory — single entry point for creating goals from anywhere.

Usage:
    from app.services.goal_service import create_goal
    goal = await create_goal(title="Fix the bug", description="...")
    goal = await create_goal(title="Sync conflict", priority="high", source="knowledge_sync")
"""
from __future__ import annotations

import re

from app.services.event_bus import GOAL_CREATED, bus
from app.services.knowledge_store import get_store


def _slugify(title: str, goal_id: int | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    return slug or f"goal-{goal_id or 0}"


def _resolve_default_workspace() -> str | None:
    store = get_store()
    workspaces = store.list("workspaces")
    if workspaces:
        return workspaces[0]["id"]
    return None


async def create_goal(
    *,
    title: str,
    description: str | None = None,
    priority: int | str = 0,
    status: str = "todo",
    workspace_id: str | None = None,
    group_id: int | None = None,
    deadline: str | None = None,
    token_budget: int | None = None,
    assigned_to: str | None = None,
    repo_url: str | None = None,
    repo_path: str | None = None,
    repos: str | None = None,
    schedule: str | None = None,
    delay_until: str | None = None,
    target: str | None = None,
    session_name: str | None = None,
    source: str | None = None,
    dedup_key: str | None = None,
) -> dict:
    """Create a goal from anywhere — routes, services, sync, plugins, AI.

    Args:
        title: Goal title (required)
        description: Detailed description / instructions
        priority: 0 (normal) or "high" / "low" / int
        status: Initial status — "todo", "scheduled", etc.
        workspace_id: If None, uses the first workspace
        source: Where this goal came from (e.g. "knowledge_sync", "discuss", "plugin")
        dedup_key: If set, skips creation when an active goal with this key exists
    """
    store = get_store()

    if dedup_key:
        existing = store.list("goals")
        if any(
            g.get("status") in ("todo", "doing")
            and dedup_key in (g.get("title") or "")
            for g in existing
        ):
            return next(
                g for g in existing
                if g.get("status") in ("todo", "doing")
                and dedup_key in (g.get("title") or "")
            )

    if not workspace_id:
        workspace_id = _resolve_default_workspace()

    if isinstance(priority, str):
        priority = {"high": 10, "low": -10}.get(priority, 0)

    if schedule and status == "todo":
        status = "scheduled"

    data = {
        "workspace_id": workspace_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "session_name": session_name,
        "group_id": group_id,
        "deadline": deadline,
        "token_budget": token_budget,
        "assigned_to": assigned_to,
        "suggested_assignee": None,
        "parent_goal_id": None,
        "reviewed_by": None,
        "reviewed_at": None,
        "repo_url": repo_url,
        "repo_path": repo_path,
        "repos": repos,
        "schedule": schedule,
        "delay_until": delay_until,
        "target": target,
        "source": source,
    }

    goal = await store.create("goals", data)
    goal["slug"] = _slugify(goal["title"], goal["id"])
    await store.update("goals", goal["id"], {"slug": goal["slug"]})

    await bus.emit(GOAL_CREATED, {
        "goal_id": goal["id"],
        "workspace_id": goal.get("workspace_id"),
        "title": goal["title"],
        "source": source,
    })

    return goal

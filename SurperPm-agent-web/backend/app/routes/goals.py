"""Goals API - CRUD, execution, review."""

import asyncio
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.routes.deps import require_auth
from app.services.event_bus import (
    EXECUTION_COMPLETED,
    EXECUTION_PROGRESS,
    GOAL_CREATED,
    GOAL_UPDATED,
    bus,
)
from app.services.goal_executor import execute_goal as _execute_goal_bg
from app.services.goal_executor import request_cancel, request_pause, request_resume
from app.services.goal_service import create_goal as _create_goal
from app.services.knowledge_store import KnowledgeStore, get_store

router = APIRouter()


class GoalCreate(BaseModel):
    workspace_id: str
    title: str
    description: str | None = None
    priority: int = 0
    session_name: str | None = None
    group_id: int | None = None
    deadline: str | None = None
    token_budget: int | None = None
    assigned_to: str | None = None
    repo_url: str | None = None
    repo_path: str | None = None
    repos: str | None = None
    schedule: str | None = None
    delay_until: str | None = None
    target: str | None = None


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    assigned_to: str | None = None
    suggested_assignee: str | None = None
    parent_goal_id: int | None = None
    group_id: int | None = None
    deadline: str | None = None
    schedule: str | None = None
    delay_until: str | None = None
    target: str | None = None
    token_budget: int | None = None
    session_name: str | None = None
    repo_url: str | None = None
    repo_path: str | None = None
    repos: str | None = None


def _slugify(title: str, goal_id: int | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    return slug or f"goal-{goal_id or 0}"


def _knowledge_root() -> str:
    return os.getenv("KNOWLEDGE_REPO_PATH") or settings.knowledge_repo_path


def _notes_path(session_name: str) -> Path:
    root = (_knowledge_root() or "").strip()
    if not root:
        raise HTTPException(
            status_code=409,
            detail="KNOWLEDGE_REPO_PATH is not configured",
        )
    return Path(root) / "sessions" / session_name / "notes.md"


def _ready_for_goal(notes_text: str) -> bool:
    return "ready_for_goal: yes" in notes_text.lower()


def _assert_session_ready(session_name: str) -> None:
    notes_path = _notes_path(session_name)
    if not notes_path.exists():
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_name}' notes.md not found",
        )
    notes_text = notes_path.read_text(encoding="utf-8")
    if not _ready_for_goal(notes_text):
        raise HTTPException(
            status_code=409,
            detail=f"Session '{session_name}' is not ready for goal execution",
        )


def _resolve_workspace(store: KnowledgeStore, workspace_ref: str) -> dict | None:
    ws = store.get("workspaces", workspace_ref)
    if ws:
        return ws
    for w in store.list("workspaces"):
        if w.get("slug") == workspace_ref:
            return w
    return None


def _has_repo_binding(goal: dict, workspace: dict) -> bool:
    if goal.get("repo_url") or workspace.get("repo_url"):
        return True
    for raw in (goal.get("repos"), workspace.get("repos")):
        if not raw:
            continue
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(data, list) and any(str(item).strip() for item in data):
            return True
    return False


@router.get("")
async def list_goals(
    status: str | None = None,
    workspace_id: str | None = None,
    group_id: int | None = None,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    filters: dict = {}
    if workspace_id:
        filters["workspace_id"] = workspace_id
    if status:
        filters["status"] = status
    if group_id is not None:
        filters["group_id"] = group_id
    rows = store.list("goals", **filters)
    rows.sort(key=lambda r: (r.get("priority", 0), r.get("created_at", "")), reverse=True)
    return rows


@router.post("", status_code=201)
async def create_goal(
    body: GoalCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    workspace = _resolve_workspace(store, body.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    goal = await _create_goal(
        title=body.title,
        description=body.description,
        priority=body.priority,
        workspace_id=workspace["id"],
        session_name=body.session_name,
        group_id=body.group_id,
        deadline=body.deadline,
        token_budget=body.token_budget,
        assigned_to=body.assigned_to,
        repo_url=body.repo_url,
        repo_path=body.repo_path,
        repos=body.repos,
        schedule=body.schedule,
        delay_until=body.delay_until,
        target=body.target,
        source="api",
    )
    return goal


class GoalBatchCreate(BaseModel):
    workspace_id: str
    goals: list[GoalCreate]


@router.post("/batch", status_code=201)
async def batch_create_goals(
    body: GoalBatchCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    workspace = _resolve_workspace(store, body.workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    created = []
    for item in body.goals:
        goal = await _create_goal(
            title=item.title,
            description=item.description,
            priority=item.priority,
            workspace_id=workspace["id"],
            group_id=item.group_id,
            deadline=item.deadline,
            token_budget=item.token_budget,
            assigned_to=item.assigned_to,
            repo_url=item.repo_url,
            repo_path=item.repo_path,
            repos=item.repos,
            source="api_batch",
        )
        created.append(goal)
    return created


@router.get("/{goal_id}")
async def get_goal(
    goal_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: int,
    body: GoalUpdate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    patch = body.model_dump(exclude_unset=True)
    if "title" in patch:
        patch["slug"] = _slugify(patch["title"], goal_id)
    updated = await store.update("goals", goal_id, patch)
    await bus.emit(
        GOAL_UPDATED,
        {
            "goal_id": goal_id,
            "workspace_id": updated["workspace_id"],
            "status": updated.get("status"),
        },
    )
    return updated


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await store.delete("goals", goal_id)


@router.post("/{goal_id}/execute", status_code=202)
async def execute_goal(
    goal_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.get("status") == "doing":
        raise HTTPException(status_code=409, detail="Goal is already executing")
    workspace = store.get("workspaces", goal["workspace_id"])
    if not workspace:
        raise HTTPException(status_code=409, detail="Workspace not found for goal")
    if goal.get("session_name"):
        _assert_session_ready(goal["session_name"])
    # Repo is optional — goals without repos run in a temp directory

    execution = await store.create("executions", {
        "goal_id": goal_id,
        "workspace_id": goal["workspace_id"],
        "status": "pending",
        "token_budget": goal.get("token_budget"),
        "error": None,
    })

    await store.update("goals", goal_id, {"status": "doing"})

    await bus.emit(
        GOAL_UPDATED,
        {
            "goal_id": goal_id,
            "workspace_id": goal["workspace_id"],
            "status": "doing",
        },
    )
    asyncio.create_task(_execute_goal_bg(goal["workspace_id"], goal_id, execution["id"]))
    return {"goal_id": goal_id, "execution_id": execution["id"], "status": "doing"}


@router.get("/{goal_id}/executions")
async def list_goal_executions(
    goal_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    rows = store.list("executions", goal_id=goal_id)
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


@router.post("/{goal_id}/executions/{execution_id}/cancel", status_code=200)
async def cancel_goal_execution(
    goal_id: int,
    execution_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    execution = store.get("executions", execution_id)
    if not execution or execution.get("goal_id") != goal_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.get("status") not in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Execution is not running")

    if request_cancel(execution_id):
        return {"ok": True, "execution_id": execution_id, "cancelling": True}

    await store.update("executions", execution_id, {
        "status": "failed",
        "error": "Cancelled by user",
    })
    await bus.emit(
        EXECUTION_COMPLETED,
        {
            "execution_id": execution_id,
            "goal_id": goal_id,
            "workspace_id": execution["workspace_id"],
            "status": "failed",
            "error": "Cancelled by user",
        },
    )
    return {"ok": True, "execution_id": execution_id}


async def _set_pause(
    goal_id: int, execution_id: str, store: KnowledgeStore, paused: bool
):
    execution = store.get("executions", execution_id)
    if not execution or execution.get("goal_id") != goal_id:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.get("status") not in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Execution is not running")
    toggled = request_pause(execution_id) if paused else request_resume(execution_id)
    if not toggled:
        raise HTTPException(status_code=409, detail="Execution is not in-flight")
    await bus.emit(
        EXECUTION_PROGRESS,
        {
            "execution_id": execution_id,
            "goal_id": goal_id,
            "workspace_id": execution["workspace_id"],
            "paused": paused,
        },
    )
    return {"ok": True, "execution_id": execution_id, "paused": paused}


@router.post("/{goal_id}/executions/{execution_id}/pause", status_code=200)
async def pause_goal_execution(
    goal_id: int,
    execution_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    return await _set_pause(goal_id, execution_id, store, paused=True)


@router.post("/{goal_id}/executions/{execution_id}/resume", status_code=200)
async def resume_goal_execution(
    goal_id: int,
    execution_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    return await _set_pause(goal_id, execution_id, store, paused=False)


class GoalReviewBody(BaseModel):
    action: str  # approve | reject


@router.post("/{goal_id}/review")
async def review_goal(
    goal_id: int,
    body: GoalReviewBody,
    store: KnowledgeStore = Depends(get_store),
    user: dict = Depends(require_auth),
):
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve or reject")
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.get("status") != "review":
        raise HTTPException(status_code=409, detail="Goal is not in review state")
    new_status = "done" if body.action == "approve" else "failed"
    updated = await store.update("goals", goal_id, {
        "status": new_status,
        "reviewed_by": user.get("login") or user.get("sub", "unknown"),
        "reviewed_at": datetime.now(UTC).isoformat(),
    })
    await bus.emit(
        GOAL_UPDATED,
        {
            "goal_id": goal_id,
            "workspace_id": updated["workspace_id"],
            "status": new_status,
        },
    )
    return updated

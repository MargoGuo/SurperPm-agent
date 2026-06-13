"""Goals API — CRUD, execution, review."""
import asyncio
import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.execution import Execution
from app.models.goal import Goal
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

router = APIRouter()


class GoalCreate(BaseModel):
    workspace_id: str
    title: str
    description: str | None = None
    priority: int = 0
    repo_url: str | None = None
    repo_path: str | None = None
    repos: str | None = None


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    assigned_to: str | None = None
    suggested_assignee: str | None = None
    parent_goal_id: int | None = None
    token_budget: int | None = None
    repo_url: str | None = None
    repo_path: str | None = None
    repos: str | None = None


def _slugify(title: str, goal_id: int | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60]
    return slug or f"goal-{goal_id or 0}"


@router.get("")
async def list_goals(
    status: str | None = None,
    workspace_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    stmt = select(Goal)
    if workspace_id:
        stmt = stmt.where(Goal.workspace_id == workspace_id)
    if status:
        stmt = stmt.where(Goal.status == status)
    stmt = stmt.order_by(Goal.priority.desc(), Goal.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", status_code=201)
async def create_goal(
    body: GoalCreate,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    goal = Goal(
        workspace_id=body.workspace_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
        repo_url=body.repo_url,
        repo_path=body.repo_path,
        repos=body.repos,
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    goal.slug = _slugify(goal.title, goal.id)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    await bus.emit(GOAL_CREATED, {
        "goal_id": goal.id,
        "workspace_id": goal.workspace_id,
        "title": goal.title,
    })
    return goal


@router.get("/{goal_id}")
async def get_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: int,
    body: GoalUpdate,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(goal, key, val)
    if "title" in update_data:
        goal.slug = _slugify(goal.title, goal.id)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    await bus.emit(GOAL_UPDATED, {
        "goal_id": goal.id,
        "workspace_id": goal.workspace_id,
        "status": goal.status,
    })
    return goal


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await session.delete(goal)
    await session.commit()


@router.post("/{goal_id}/execute", status_code=202)
async def execute_goal(
    goal_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.status == "doing":
        raise HTTPException(status_code=409, detail="Goal is already executing")

    # Pre-create the Execution row so we can return its ID immediately.
    execution = Execution(
        goal_id=goal_id,
        workspace_id=goal.workspace_id,
        status="pending",
        token_budget=goal.token_budget,
    )
    session.add(execution)

    goal.status = "doing"
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    await session.refresh(execution)

    await bus.emit(GOAL_UPDATED, {
        "goal_id": goal.id,
        "workspace_id": goal.workspace_id,
        "status": "doing",
    })
    asyncio.create_task(_execute_goal_bg(goal.workspace_id, goal.id, execution.id))
    return {"goal_id": goal.id, "execution_id": execution.id, "status": "doing"}


@router.get("/{goal_id}/executions")
async def list_goal_executions(
    goal_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    stmt = (
        select(Execution)
        .where(Execution.goal_id == goal_id)
        .order_by(Execution.created_at.desc())
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("/{goal_id}/executions/{execution_id}/cancel", status_code=200)
async def cancel_goal_execution(
    goal_id: int,
    execution_id: str,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    stmt = select(Execution).where(
        Execution.id == execution_id, Execution.goal_id == goal_id
    )
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status not in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Execution is not running")

    # If the execution is in-flight, signal the agent to stop and let the
    # background task finalize the execution/goal status and emit events.
    if request_cancel(execution_id):
        return {"ok": True, "execution_id": execution_id, "cancelling": True}

    # Otherwise (no in-flight task in this process) flip the DB row directly.
    execution.status = "failed"
    execution.error = "Cancelled by user"
    session.add(execution)
    await session.commit()
    await session.refresh(execution)
    await bus.emit(EXECUTION_COMPLETED, {
        "execution_id": execution_id,
        "goal_id": goal_id,
        "workspace_id": execution.workspace_id,
        "status": "failed",
        "error": "Cancelled by user",
    })
    return {"ok": True, "execution_id": execution_id}


async def _set_pause(goal_id: int, execution_id: str, session: AsyncSession, paused: bool):
    """Shared pause/resume handler: toggle the in-flight agent loop + notify WS."""
    stmt = select(Execution).where(
        Execution.id == execution_id, Execution.goal_id == goal_id
    )
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    if execution.status not in ("pending", "running"):
        raise HTTPException(status_code=409, detail="Execution is not running")
    toggled = request_pause(execution_id) if paused else request_resume(execution_id)
    if not toggled:
        raise HTTPException(status_code=409, detail="Execution is not in-flight")
    # Live-only flag; not persisted (it has no meaning once the run ends).
    await bus.emit(EXECUTION_PROGRESS, {
        "execution_id": execution_id,
        "goal_id": goal_id,
        "workspace_id": execution.workspace_id,
        "paused": paused,
    })
    return {"ok": True, "execution_id": execution_id, "paused": paused}


@router.post("/{goal_id}/executions/{execution_id}/pause", status_code=200)
async def pause_goal_execution(
    goal_id: int,
    execution_id: str,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    return await _set_pause(goal_id, execution_id, session, paused=True)


@router.post("/{goal_id}/executions/{execution_id}/resume", status_code=200)
async def resume_goal_execution(
    goal_id: int,
    execution_id: str,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    return await _set_pause(goal_id, execution_id, session, paused=False)


class GoalReviewBody(BaseModel):
    action: str  # approve | reject


@router.post("/{goal_id}/review")
async def review_goal(
    goal_id: int,
    body: GoalReviewBody,
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(require_auth),
):
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be approve or reject")
    goal = await session.get(Goal, goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.status != "review":
        raise HTTPException(status_code=409, detail="Goal is not in review state")
    goal.status = "done" if body.action == "approve" else "failed"
    goal.reviewed_by = user.get("login") or user.get("sub", "unknown")
    goal.reviewed_at = datetime.now(UTC)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    await bus.emit(GOAL_UPDATED, {
        "goal_id": goal.id,
        "workspace_id": goal.workspace_id,
        "status": goal.status,
    })
    return goal

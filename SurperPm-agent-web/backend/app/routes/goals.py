"""V2 Goals API — workspace-scoped CRUD + execution trigger."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.goal import Goal
from app.services.event_bus import bus

router = APIRouter()


class GoalCreate(BaseModel):
    title: str
    description: str | None = None
    priority: int = 0


class GoalUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None


@router.get("")
async def list_goals(
    workspace_id: str,
    status: str | None = None,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Goal).where(Goal.workspace_id == workspace_id)
    if status:
        stmt = stmt.where(Goal.status == status)
    stmt = stmt.order_by(Goal.priority.desc(), Goal.created_at.desc())
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", status_code=201)
async def create_goal(
    workspace_id: str,
    body: GoalCreate,
    session: AsyncSession = Depends(get_session),
):
    goal = Goal(
        workspace_id=workspace_id,
        title=body.title,
        description=body.description,
        priority=body.priority,
    )
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    await bus.emit("goal_created", {
        "goal_id": goal.id,
        "workspace_id": workspace_id,
        "title": goal.title,
    })
    return goal


@router.get("/{goal_id}")
async def get_goal(
    workspace_id: str,
    goal_id: int,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Goal).where(Goal.id == goal_id, Goal.workspace_id == workspace_id)
    result = await session.execute(stmt)
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.patch("/{goal_id}")
async def update_goal(
    workspace_id: str,
    goal_id: int,
    body: GoalUpdate,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Goal).where(Goal.id == goal_id, Goal.workspace_id == workspace_id)
    result = await session.execute(stmt)
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(goal, key, val)
    session.add(goal)
    await session.commit()
    await session.refresh(goal)
    await bus.emit("goal_updated", {
        "goal_id": goal.id,
        "workspace_id": workspace_id,
        "status": goal.status,
    })
    return goal


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    workspace_id: str,
    goal_id: int,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Goal).where(Goal.id == goal_id, Goal.workspace_id == workspace_id)
    result = await session.execute(stmt)
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    await session.delete(goal)
    await session.commit()


@router.post("/{goal_id}/execute", status_code=202)
async def execute_goal(
    workspace_id: str,
    goal_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Trigger agent execution for a goal. Returns immediately (async)."""
    stmt = select(Goal).where(Goal.id == goal_id, Goal.workspace_id == workspace_id)
    result = await session.execute(stmt)
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    if goal.status == "doing":
        raise HTTPException(status_code=409, detail="Goal is already executing")

    # Mark as doing
    goal.status = "doing"
    session.add(goal)
    await session.commit()
    await session.refresh(goal)

    await bus.emit("goal_updated", {
        "goal_id": goal.id,
        "workspace_id": workspace_id,
        "status": "doing",
    })

    # TODO: Phase 3 wire-up — actually trigger goal_runner_v2 here
    # For now, just return accepted status
    return {"goal_id": goal.id, "status": "doing", "message": "Execution queued"}

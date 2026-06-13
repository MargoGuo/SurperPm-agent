"""V2 Discussions API — workspace-scoped messaging + goal trigger."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.discussion import Discussion
from app.models.execution import Execution
from app.models.goal import Goal
from app.services.discuss_parser import parse_goal_mentions
from app.services.event_bus import bus
from app.ws.hub import hub

router = APIRouter()


class DiscussionCreate(BaseModel):
    content: str
    role: str = "user"


@router.get("")
async def list_discussions(
    workspace_id: str,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
):
    stmt = (
        select(Discussion)
        .where(Discussion.workspace_id == workspace_id)
        .order_by(Discussion.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.post("", status_code=201)
async def create_discussion(
    workspace_id: str,
    body: DiscussionCreate,
    session: AsyncSession = Depends(get_session),
):
    discussion = Discussion(
        workspace_id=workspace_id,
        content=body.content,
        role=body.role,
    )
    session.add(discussion)
    await session.commit()
    await session.refresh(discussion)

    # Parse @goal-N mentions and trigger execution for each
    goal_ids = parse_goal_mentions(body.content)
    for goal_id in goal_ids:
        stmt = select(Goal).where(
            Goal.id == goal_id, Goal.workspace_id == workspace_id
        )
        result = await session.execute(stmt)
        goal = result.scalar_one_or_none()
        if goal and goal.status != "doing":
            # Mark goal as doing
            goal.status = "doing"
            session.add(goal)

            # Create Execution row
            execution = Execution(
                goal_id=goal.id,
                workspace_id=workspace_id,
            )
            session.add(execution)
            await session.commit()
            await session.refresh(goal)

            await bus.emit("goal_updated", {
                "goal_id": goal.id,
                "workspace_id": workspace_id,
                "status": "doing",
            })

    # Emit discussion_created event
    await bus.emit("discussion_created", {
        "discussion_id": discussion.id,
        "workspace_id": workspace_id,
        "role": discussion.role,
        "content": discussion.content,
    })

    # Broadcast via WS hub
    await hub.broadcast(workspace_id, "discussion_created", {
        "discussion_id": discussion.id,
        "role": discussion.role,
        "content": discussion.content,
    })

    return discussion


@router.get("/{discussion_id}")
async def get_discussion(
    workspace_id: str,
    discussion_id: int,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Discussion).where(
        Discussion.id == discussion_id,
        Discussion.workspace_id == workspace_id,
    )
    result = await session.execute(stmt)
    discussion = result.scalar_one_or_none()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return discussion

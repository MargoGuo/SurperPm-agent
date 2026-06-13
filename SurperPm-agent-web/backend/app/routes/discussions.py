"""V2 Discussions API — workspace-scoped messaging + goal trigger + AI reply."""

import asyncio
import logging

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.config import settings
from app.database import get_session, async_session
from app.routes.deps import require_auth
from app.models.discussion import Discussion
from app.models.execution import Execution
from app.models.goal import Goal
from app.services.discuss_parser import parse_goal_mentions
from app.services.event_bus import bus, DISCUSSION_CREATED, GOAL_UPDATED

_logger = logging.getLogger(__name__)

router = APIRouter()


class DiscussionCreate(BaseModel):
    content: str
    role: str = "user"
    parent_id: int | None = None


@router.get("")
async def list_discussions(
    workspace_id: str,
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
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
    _user: dict = Depends(require_auth),
):
    discussion = Discussion(
        workspace_id=workspace_id,
        content=body.content,
        role=body.role,
        parent_id=body.parent_id,
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

            await bus.emit(GOAL_UPDATED, {
                "goal_id": goal.id,
                "workspace_id": workspace_id,
                "status": "doing",
            })

    await bus.emit(DISCUSSION_CREATED, {
        "id": discussion.id,
        "workspace_id": workspace_id,
        "role": discussion.role,
        "content": discussion.content,
        "created_at": discussion.created_at.isoformat(),
    })

    # Trigger AI auto-reply for user messages
    if body.role == "user":
        asyncio.create_task(_generate_ai_reply(workspace_id, body.content))

    return discussion


@router.get("/{discussion_id}")
async def get_discussion(
    workspace_id: str,
    discussion_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
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


# ============================================================
# AI Auto-Reply (background task)
# ============================================================

_SYSTEM_PROMPT = (
    "You are a helpful project management assistant for SuperPmAgent. "
    "You discuss project goals, provide suggestions, and help coordinate work. "
    "Be concise and actionable. Reply in the same language the user uses."
)

_MAX_CONTEXT_MESSAGES = 20


async def _generate_ai_reply(workspace_id: str, user_content: str) -> None:
    """Background task: call Anthropic API and post agent reply."""
    api_key = settings.anthropic_api_key
    if not api_key:
        return

    try:
        # Fetch recent messages for context
        async with async_session() as db:
            stmt = (
                select(Discussion)
                .where(Discussion.workspace_id == workspace_id)
                .order_by(Discussion.created_at.desc())
                .limit(_MAX_CONTEXT_MESSAGES)
            )
            result = await db.execute(stmt)
            recent = list(reversed(result.scalars().all()))

        messages = []
        for msg in recent:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})

        client = anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=settings.anthropic_base_url or None,
        )

        model = settings.agent_model or "claude-sonnet-4-20260613"
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=messages,
        )

        reply_text = response.content[0].text if response.content else ""
        if not reply_text.strip():
            return

        # Save agent reply
        async with async_session() as db:
            agent_msg = Discussion(
                workspace_id=workspace_id,
                content=reply_text,
                role="agent",
            )
            db.add(agent_msg)
            await db.commit()
            await db.refresh(agent_msg)

        await bus.emit(DISCUSSION_CREATED, {
            "id": agent_msg.id,
            "workspace_id": workspace_id,
            "role": "agent",
            "content": reply_text,
            "created_at": agent_msg.created_at.isoformat(),
        })

    except Exception as e:
        _logger.warning("AI reply failed for workspace %s: %s", workspace_id, e)

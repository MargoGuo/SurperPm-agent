"""Learnings — execution distillations read straight from the DB.

The knowledge repo is a read-only mirror of the bound GitHub repo, so
execution summaries live in the Execution table rather than as files.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.execution import Execution
from app.models.goal import Goal
from app.routes.deps import require_auth

router = APIRouter()


@router.get("")
async def list_learnings(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> list[dict]:
    """Return finished executions that carry a distilled summary, newest first."""
    stmt = (
        select(Execution, Goal.title)
        .join(Goal, Goal.id == Execution.goal_id)
        .where(Execution.summary.is_not(None))
        .order_by(Execution.created_at.desc())
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [
        {
            "id": ex.id,
            "goal_id": ex.goal_id,
            "goal_title": title,
            "status": ex.status,
            "summary": ex.summary,
            "pr_url": ex.pr_url,
            "token_used": ex.token_used,
            "started_at": ex.started_at,
            "finished_at": ex.finished_at,
            "created_at": ex.created_at,
        }
        for ex, title in rows
    ]

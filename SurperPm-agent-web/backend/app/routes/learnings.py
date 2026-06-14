"""Learnings API — file-based knowledge from SuperPmAgent-knowledge/learnings/.

Reads Markdown files with frontmatter, computes memory-curve scores,
supports pin/archive/manual-distill actions.
"""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.routes.deps import require_auth
from app.services.knowledge_distiller import (
    DEFAULT_DISTILL_CONFIG,
    record_access,
    run_distill_cycle,
    write_learning,
)
from app.services.knowledge_distiller import (
    list_learnings as _list_learnings,
)

router = APIRouter()


class LearningCreate(BaseModel):
    title: str
    content: str
    category: str = "insight"
    importance: float = 0.5
    tags: list[str] | None = None


class LearningPin(BaseModel):
    pinned: bool


class LearningArchive(BaseModel):
    archived: bool


async def _load_distill_config(session: AsyncSession) -> dict:
    from app.services.knowledge_store import get_store

    store = get_store()
    store_settings = store.get_settings()
    distill_raw = store_settings.get("distill_config")
    if distill_raw:
        try:
            return json.loads(distill_raw) if isinstance(distill_raw, str) else distill_raw
        except (json.JSONDecodeError, TypeError):
            pass
    return DEFAULT_DISTILL_CONFIG


@router.get("")
async def list_learnings_route(
    category: str | None = None,
    pinned: bool | None = None,
    archived: bool = False,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> list[dict]:
    """Return all learnings sorted by score, with optional filters."""
    config = await _load_distill_config(session)
    all_learnings = _list_learnings(config)

    results = []
    for item in all_learnings:
        if item.get("archived", False) != archived:
            continue
        if category and item.get("category") != category:
            continue
        if pinned is not None and item.get("pinned", False) != pinned:
            continue
        results.append({
            "slug": item["slug"],
            "title": item.get("title", item["slug"]),
            "category": item.get("category", "insight"),
            "source_type": item.get("source_type", "internal"),
            "importance": item.get("importance", 0.5),
            "confidence": item.get("confidence", 0.8),
            "score": round(item.get("score", 0), 3),
            "pinned": item.get("pinned", False),
            "archived": item.get("archived", False),
            "created": item.get("created", ""),
            "tags": item.get("tags", ""),
            "body": item.get("body", ""),
            "access_count": item.get("access_count", 0),
        })

    return results


@router.get("/{slug}")
async def get_learning(
    slug: str,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> dict:
    """Get a single learning by slug and record access."""
    config = await _load_distill_config(session)
    all_learnings = _list_learnings(config)

    for item in all_learnings:
        if item["slug"] == slug:
            record_access(slug)
            return {
                "slug": item["slug"],
                "title": item.get("title", item["slug"]),
                "category": item.get("category", "insight"),
                "source_type": item.get("source_type", "internal"),
                "importance": item.get("importance", 0.5),
                "confidence": item.get("confidence", 0.8),
                "score": round(item.get("score", 0), 3),
                "pinned": item.get("pinned", False),
                "archived": item.get("archived", False),
                "created": item.get("created", ""),
                "tags": item.get("tags", ""),
                "body": item.get("body", ""),
                "access_count": item.get("access_count", 0),
            }

    raise HTTPException(status_code=404, detail="Learning not found")


@router.post("", status_code=201)
async def create_learning(
    body: LearningCreate,
    _session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> dict:
    """Manually create a learning."""
    path = write_learning(
        title=body.title,
        content=body.content,
        category=body.category,
        importance=body.importance,
        tags=body.tags,
        source_type="manual",
    )
    return {"ok": True, "slug": path.stem}


@router.patch("/{slug}/pin")
async def pin_learning(
    slug: str,
    body: LearningPin,
    _session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> dict:
    """Toggle pin status of a learning."""
    from app.services.knowledge_distiller import _learnings_dir

    file_path = _learnings_dir() / f"{slug}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Learning not found")

    text = file_path.read_text(encoding="utf-8")
    old_val = "pinned: true" if not body.pinned else "pinned: false"
    new_val = "pinned: true" if body.pinned else "pinned: false"
    text = text.replace(old_val, new_val, 1)
    file_path.write_text(text, encoding="utf-8")
    return {"ok": True, "pinned": body.pinned}


@router.patch("/{slug}/archive")
async def archive_learning(
    slug: str,
    body: LearningArchive,
    _session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> dict:
    """Toggle archive status of a learning."""
    from app.services.knowledge_distiller import _learnings_dir

    file_path = _learnings_dir() / f"{slug}.md"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Learning not found")

    text = file_path.read_text(encoding="utf-8")
    old_val = "archived: true" if not body.archived else "archived: false"
    new_val = "archived: true" if body.archived else "archived: false"
    text = text.replace(old_val, new_val, 1)
    file_path.write_text(text, encoding="utf-8")
    return {"ok": True, "archived": body.archived}


@router.post("/distill")
async def trigger_distill(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> dict:
    """Manually trigger a distill cycle."""
    config = await _load_distill_config(session)
    result = await run_distill_cycle(config)
    return result

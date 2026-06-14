"""Standalone Topics — discussion channels not tied to any goal."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.deps import require_auth
from app.services.knowledge_store import KnowledgeStore, get_store

router = APIRouter()


def _get_default_workspace_id(store: KnowledgeStore) -> str:
    workspaces = store.list("workspaces")
    if not workspaces:
        raise HTTPException(status_code=404, detail="No workspace found")
    return workspaces[0]["id"]


class TopicCreate(BaseModel):
    name: str
    description: str | None = None


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    archived: bool | None = None


@router.get("")
async def list_standalone_topics(
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    workspace_id = _get_default_workspace_id(store)
    rows = store.list("topics", workspace_id=workspace_id)
    return [
        r for r in rows
        if r.get("goal_id") is None and not r.get("archived", False)
    ]


@router.post("")
async def create_standalone_topic(
    body: TopicCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    workspace_id = _get_default_workspace_id(store)
    return await store.create("topics", {
        "workspace_id": workspace_id,
        "goal_id": None,
        "name": body.name,
        "description": body.description,
        "pinned": False,
        "archived": False,
    })


@router.patch("/{topic_id}")
async def update_standalone_topic(
    topic_id: int,
    body: TopicUpdate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    topic = store.get("topics", topic_id)
    if not topic or topic.get("goal_id") is not None:
        raise HTTPException(status_code=404, detail="Topic not found")
    patch = body.model_dump(exclude_unset=True)
    updated = await store.update("topics", topic_id, patch)
    if not updated:
        raise HTTPException(status_code=404, detail="Topic not found")
    return updated


@router.delete("/{topic_id}")
async def delete_standalone_topic(
    topic_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    topic = store.get("topics", topic_id)
    if not topic or topic.get("goal_id") is not None:
        raise HTTPException(status_code=404, detail="Topic not found")
    await store.update("topics", topic_id, {"archived": True})
    return {"ok": True}

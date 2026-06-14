"""Topics API — goal-scoped conversation channels."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.deps import require_auth
from app.services.event_bus import TOPIC_CREATED, TOPIC_UPDATED, bus
from app.services.knowledge_store import KnowledgeStore, get_store

router = APIRouter()


class TopicCreate(BaseModel):
    name: str
    description: str | None = None
    repo_url: str | None = None


class TopicUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    pinned: bool | None = None
    archived: bool | None = None


@router.get("")
async def list_topics(
    goal_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    rows = store.list("topics", workspace_id=goal["workspace_id"], goal_id=goal_id)
    return [r for r in rows if not r.get("archived", False)]


@router.post("", status_code=201)
async def create_topic(
    goal_id: int,
    body: TopicCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    topic = await store.create("topics", {
        "workspace_id": goal["workspace_id"],
        "name": body.name,
        "description": body.description,
        "goal_id": goal_id,
        "repo_url": body.repo_url,
        "pinned": False,
        "archived": False,
    })
    await bus.emit(TOPIC_CREATED, {
        "topic_id": topic["id"],
        "workspace_id": goal["workspace_id"],
        "goal_id": goal_id,
        "name": topic["name"],
    })
    return topic


@router.get("/{topic_id}")
async def get_topic(
    goal_id: int,
    topic_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    topic = store.get("topics", topic_id)
    if not topic or topic.get("goal_id") != goal_id:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


@router.patch("/{topic_id}")
async def update_topic(
    goal_id: int,
    topic_id: int,
    body: TopicUpdate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    topic = store.get("topics", topic_id)
    if not topic or topic.get("goal_id") != goal_id:
        raise HTTPException(status_code=404, detail="Topic not found")
    patch = body.model_dump(exclude_unset=True)
    updated = await store.update("topics", topic_id, patch)
    await bus.emit(TOPIC_UPDATED, {
        "topic_id": topic_id,
        "workspace_id": goal["workspace_id"],
        "goal_id": goal_id,
        "name": updated["name"],
    })
    return updated


@router.delete("/{topic_id}", status_code=204)
async def delete_topic(
    goal_id: int,
    topic_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    goal = store.get("goals", goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    topic = store.get("topics", topic_id)
    if not topic or topic.get("goal_id") != goal_id:
        raise HTTPException(status_code=404, detail="Topic not found")
    if topic.get("name") == "general":
        raise HTTPException(status_code=400, detail="Cannot delete the #general topic")
    await store.delete("topics", topic_id)

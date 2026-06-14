"""Workspaces API — CRUD + SSH keys + repos management."""

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.deps import require_auth
from app.services.crypto import encrypt
from app.services.event_bus import WORKSPACE_CREATED, WORKSPACE_UPDATED, bus
from app.services.knowledge_store import KnowledgeStore, get_store
from app.services.ssh_keygen import generate_ssh_keypair

router = APIRouter()


def _resolve_workspace(store: KnowledgeStore, workspace_id: str) -> dict | None:
    ws = store.get("workspaces", workspace_id)
    if ws:
        return ws
    for w in store.list("workspaces"):
        if w.get("slug") == workspace_id:
            return w
    return None


class WorkspaceCreate(BaseModel):
    name: str
    slug: str
    repo_url: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = None
    repo_url: str | None = None
    knowledge_repo_url: str | None = None


@router.get("")
async def list_workspaces(
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    return store.list("workspaces")


@router.post("", status_code=201)
async def create_workspace(
    body: WorkspaceCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    public_key, private_key = generate_ssh_keypair()
    private_key_enc = encrypt(private_key)

    ws = await store.create("workspaces", {
        "name": body.name,
        "slug": body.slug,
        "repo_url": body.repo_url,
        "repos": None,
        "ssh_public_key": public_key,
        "ssh_private_key_enc": private_key_enc,
    }, id_type="hex")

    await store.create("topics", {
        "workspace_id": ws["id"],
        "goal_id": None,
        "name": "general",
        "description": "General discussion",
        "pinned": True,
        "archived": False,
    })

    await bus.emit(WORKSPACE_CREATED, {"workspace_id": ws["id"], "name": ws["name"]})
    return ws


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    body: WorkspaceUpdate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    patch = body.model_dump(exclude_unset=True)
    updated = await store.update("workspaces", ws["id"], patch)
    await bus.emit(WORKSPACE_UPDATED, {
        "workspace_id": ws["id"],
        "name": updated["name"],
    })
    return updated


@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(
    workspace_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await store.delete("workspaces", ws["id"])


@router.get("/{workspace_id}/ssh-public-key")
async def get_ssh_public_key(
    workspace_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not ws.get("ssh_public_key"):
        raise HTTPException(
            status_code=404,
            detail="No SSH key generated for this workspace",
        )
    return {"public_key": ws["ssh_public_key"]}


@router.post("/{workspace_id}/regenerate-ssh-key", status_code=201)
async def regenerate_ssh_key(
    workspace_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    public_key, private_key = generate_ssh_keypair()
    private_key_enc = encrypt(private_key)
    await store.update("workspaces", ws["id"], {
        "ssh_public_key": public_key,
        "ssh_private_key_enc": private_key_enc,
    })
    return {"public_key": public_key}


def _parse_repos(ws: dict) -> list[str]:
    raw = ws.get("repos")
    if not raw:
        return []
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


class RepoAdd(BaseModel):
    url: str


@router.get("/{workspace_id}/repos")
async def list_repos(
    workspace_id: str,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return _parse_repos(ws)


@router.post("/{workspace_id}/repos", status_code=201)
async def add_repo(
    workspace_id: str,
    body: RepoAdd,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    repos = _parse_repos(ws)
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required")
    if url in repos:
        raise HTTPException(status_code=409, detail="Repo already exists")
    repos.append(url)
    await store.update("workspaces", ws["id"], {"repos": json.dumps(repos)})
    return repos


@router.delete("/{workspace_id}/repos/{index}")
async def delete_repo(
    workspace_id: str,
    index: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    ws = _resolve_workspace(store, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    repos = _parse_repos(ws)
    if index < 0 or index >= len(repos):
        raise HTTPException(status_code=404, detail="Repo index out of range")
    repos.pop(index)
    await store.update("workspaces", ws["id"], {"repos": json.dumps(repos)})
    return repos

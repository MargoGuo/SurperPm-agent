from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel

from app.database import get_session
from app.routes.deps import require_auth
from app.models.workspace import Workspace
from app.services.crypto import encrypt
from app.services.event_bus import bus, WORKSPACE_CREATED
from app.services.ssh_keygen import generate_ssh_keypair

router = APIRouter()

class WorkspaceCreate(BaseModel):
    name: str
    slug: str
    repo_url: str | None = None

class WorkspaceUpdate(BaseModel):
    name: str | None = None
    repo_url: str | None = None
    knowledge_repo_url: str | None = None

@router.get("")
async def list_workspaces(session: AsyncSession = Depends(get_session), _user: dict = Depends(require_auth)):
    result = await session.execute(select(Workspace))
    return result.scalars().all()

@router.post("", status_code=201)
async def create_workspace(body: WorkspaceCreate, session: AsyncSession = Depends(get_session), _user: dict = Depends(require_auth)):
    # Generate SSH keypair for the new workspace
    public_key, private_key = generate_ssh_keypair()
    private_key_enc = encrypt(private_key)

    ws = Workspace(
        name=body.name,
        slug=body.slug,
        repo_url=body.repo_url,
        ssh_public_key=public_key,
        ssh_private_key_enc=private_key_enc,
    )
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    await bus.emit(WORKSPACE_CREATED, {"workspace_id": ws.id, "name": ws.name})
    return ws

@router.get("/{workspace_id}")
async def get_workspace(workspace_id: str, session: AsyncSession = Depends(get_session), _user: dict = Depends(require_auth)):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return ws

@router.patch("/{workspace_id}")
async def update_workspace(workspace_id: str, body: WorkspaceUpdate, session: AsyncSession = Depends(get_session), _user: dict = Depends(require_auth)):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    update_data = body.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(ws, key, val)
    session.add(ws)
    await session.commit()
    await session.refresh(ws)
    return ws

@router.delete("/{workspace_id}", status_code=204)
async def delete_workspace(workspace_id: str, session: AsyncSession = Depends(get_session), _user: dict = Depends(require_auth)):
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    await session.delete(ws)
    await session.commit()


@router.get("/{workspace_id}/ssh-public-key")
async def get_ssh_public_key(workspace_id: str, session: AsyncSession = Depends(get_session), _user: dict = Depends(require_auth)):
    """Return the SSH public key for a workspace (for user to copy)."""
    ws = await session.get(Workspace, workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not ws.ssh_public_key:
        raise HTTPException(status_code=404, detail="No SSH key generated for this workspace")
    return PlainTextResponse(ws.ssh_public_key)

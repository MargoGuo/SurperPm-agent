"""Workspace-scoped Secrets API — CRUD with encryption."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.secret import Secret
from app.services.crypto import decrypt, encrypt

router = APIRouter()


class SecretCreate(BaseModel):
    key: str
    value: str
    category: str = "env"


class SecretOut(BaseModel):
    id: int
    workspace_id: str
    key: str
    value: str  # redacted
    category: str


@router.get("")
async def list_secrets(
    workspace_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[SecretOut]:
    """List all secrets for a workspace. Values are redacted."""
    stmt = select(Secret).where(Secret.workspace_id == workspace_id)
    result = await session.execute(stmt)
    secrets = result.scalars().all()
    return [
        SecretOut(
            id=s.id,  # type: ignore[arg-type]
            workspace_id=s.workspace_id,
            key=s.key,
            value="***",
            category=s.category,
        )
        for s in secrets
    ]


@router.post("", status_code=201)
async def create_secret(
    workspace_id: str,
    body: SecretCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new secret. The value is encrypted before storage."""
    encrypted_value = encrypt(body.value)
    secret = Secret(
        workspace_id=workspace_id,
        key=body.key,
        value_enc=encrypted_value,
        category=body.category,
    )
    session.add(secret)
    await session.commit()
    await session.refresh(secret)
    return SecretOut(
        id=secret.id,  # type: ignore[arg-type]
        workspace_id=secret.workspace_id,
        key=secret.key,
        value="***",
        category=secret.category,
    )


@router.delete("/{secret_id}", status_code=204)
async def delete_secret(
    workspace_id: str,
    secret_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete a secret by ID."""
    stmt = select(Secret).where(
        Secret.id == secret_id, Secret.workspace_id == workspace_id
    )
    result = await session.execute(stmt)
    secret = result.scalar_one_or_none()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    await session.delete(secret)
    await session.commit()


@router.get("/{secret_id}/reveal")
async def reveal_secret(
    workspace_id: str,
    secret_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Reveal the decrypted value of a single secret."""
    stmt = select(Secret).where(
        Secret.id == secret_id, Secret.workspace_id == workspace_id
    )
    result = await session.execute(stmt)
    secret = result.scalar_one_or_none()
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    decrypted_value = decrypt(secret.value_enc)
    return {"id": secret.id, "key": secret.key, "value": decrypted_value}

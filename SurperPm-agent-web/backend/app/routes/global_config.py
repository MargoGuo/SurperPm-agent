"""Global Config API — system-wide settings (SSH, knowledge, AI, secrets)."""
import shutil
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.database import get_session
from app.models.global_config import GlobalConfig
from app.models.secret import Secret
from app.routes.deps import require_auth
from app.services.crypto import decrypt, encrypt
from app.services.ssh_keygen import generate_ssh_keypair

router = APIRouter()


class GlobalConfigUpdate(BaseModel):
    knowledge_repo_url: str | None = None
    knowledge_repo_path: str | None = None
    ssh_public_key: str | None = None
    ssh_private_key_enc: str | None = None
    ai_base_url: str | None = None
    ai_api_key_enc: str | None = None
    ai_model: str | None = None


class SecretCreate(BaseModel):
    key: str
    value: str
    category: str = "env"


class SecretOut(BaseModel):
    id: int
    key: str
    value: str
    category: str


async def _get_or_create_config(session: AsyncSession) -> GlobalConfig:
    cfg = await session.get(GlobalConfig, 1)
    if not cfg:
        cfg = GlobalConfig(id=1)
        session.add(cfg)
        await session.commit()
        await session.refresh(cfg)
    return cfg


@router.get("")
async def get_global_config(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    cfg = await _get_or_create_config(session)
    return {
        "knowledge_repo_url": cfg.knowledge_repo_url,
        "knowledge_repo_path": cfg.knowledge_repo_path,
        "ssh_public_key": cfg.ssh_public_key,
        "ai_base_url": cfg.ai_base_url,
        "ai_api_key_set": bool(cfg.ai_api_key_enc),
        "ai_model": cfg.ai_model,
    }


@router.patch("")
async def update_global_config(
    body: GlobalConfigUpdate,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    cfg = await _get_or_create_config(session)
    update_data = body.model_dump(exclude_unset=True)

    if cfg.knowledge_repo_url and "knowledge_repo_url" in update_data:
        raise HTTPException(
            status_code=400,
            detail="Knowledge repo URL cannot be changed once set",
        )

    for key, val in update_data.items():
        setattr(cfg, key, val)
    cfg.updated_at = datetime.now(UTC)
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return {"ok": True}


@router.delete("")
async def reset_global_config(
    session: AsyncSession = Depends(get_session),
    user: dict = Depends(require_auth),
):
    """Founder-only: wipe global config + global secrets + local knowledge clone.

    Used by the founder to re-run first-time setup from the settings page.
    """
    cfg = await _get_or_create_config(session)
    if not cfg.founder_username or user.get("username") != cfg.founder_username:
        raise HTTPException(status_code=403, detail="Only the founder can reset")

    cfg.founder_username = None
    cfg.knowledge_repo_url = None
    cfg.knowledge_repo_path = None
    cfg.ssh_public_key = None
    cfg.ssh_private_key_enc = None
    cfg.ai_base_url = None
    cfg.ai_api_key_enc = None
    cfg.ai_model = None
    cfg.github_token_enc = None
    cfg.updated_at = datetime.now(UTC)
    session.add(cfg)

    stmt = select(Secret).where(Secret.workspace_id == "__global__")
    result = await session.execute(stmt)
    for secret in result.scalars().all():
        await session.delete(secret)
    await session.commit()

    # Remove the local knowledge clone so the next bind re-clones cleanly.
    from app.services.knowledge_sync import _target_path
    dest = _target_path()
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    return {"ok": True}


@router.get("/ssh-key")
async def get_ssh_key(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    cfg = await _get_or_create_config(session)
    return {
        "ssh_public_key": cfg.ssh_public_key,
        "has_private_key": bool(cfg.ssh_private_key_enc),
    }


@router.post("/generate-ssh-key", status_code=201)
async def generate_ssh_key(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    """Generate a new Ed25519 SSH key pair and store it in global config."""
    cfg = await _get_or_create_config(session)
    public_key, private_key = generate_ssh_keypair()
    cfg.ssh_public_key = public_key
    cfg.ssh_private_key_enc = encrypt(private_key)
    cfg.updated_at = datetime.now(UTC)
    session.add(cfg)
    await session.commit()
    await session.refresh(cfg)
    return {"ssh_public_key": cfg.ssh_public_key}


@router.get("/secrets")
async def list_secrets(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> list[SecretOut]:
    stmt = select(Secret)
    result = await session.execute(stmt)
    secrets = result.scalars().all()
    return [
        SecretOut(
            id=s.id,  # type: ignore[arg-type]
            key=s.key,
            value="***",
            category=s.category,
        )
        for s in secrets
    ]


@router.post("/secrets", status_code=201)
async def create_secret(
    body: SecretCreate,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    encrypted_value = encrypt(body.value)
    secret = Secret(
        workspace_id="__global__",
        key=body.key,
        value_enc=encrypted_value,
        category=body.category,
    )
    session.add(secret)
    await session.commit()
    await session.refresh(secret)
    return SecretOut(
        id=secret.id,  # type: ignore[arg-type]
        key=secret.key,
        value="***",
        category=secret.category,
    )


@router.get("/secrets/{secret_id}/reveal")
async def reveal_secret(
    secret_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    secret = await session.get(Secret, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return SecretOut(
        id=secret.id,  # type: ignore[arg-type]
        key=secret.key,
        value=decrypt(secret.value_enc),
        category=secret.category,
    )


@router.delete("/secrets/{secret_id}", status_code=204)
async def delete_secret(
    secret_id: int,
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
):
    secret = await session.get(Secret, secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    await session.delete(secret)
    await session.commit()

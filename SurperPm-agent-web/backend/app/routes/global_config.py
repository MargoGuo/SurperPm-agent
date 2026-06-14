"""Global Config API — system-wide settings (SSH, knowledge, AI, secrets).

Sensitive fields (SSH private key, GitHub token, AI API key, founder) stay in SQLite.
Non-sensitive config (repo URL, AI model, base_url, distill_config) lives in
KnowledgeStore settings.json. Secrets use the KnowledgeStore 'secrets' collection.
"""
import shutil
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.global_config import GlobalConfig
from app.routes.deps import require_auth
from app.services.crypto import decrypt, encrypt
from app.services.knowledge_store import KnowledgeStore, get_store
from app.services.ssh_keygen import generate_ssh_keypair

router = APIRouter()

_SQLITE_FIELDS = {
    "ssh_private_key_enc",
    "ai_api_key_enc",
    "github_token_enc",
    "founder_username",
}

_SETTINGS_FIELDS = {
    "knowledge_repo_url",
    "knowledge_repo_path",
    "ssh_public_key",
    "ai_base_url",
    "ai_model",
    "distill_config",
}


class GlobalConfigUpdate(BaseModel):
    knowledge_repo_url: str | None = None
    knowledge_repo_path: str | None = None
    ssh_public_key: str | None = None
    ssh_private_key_enc: str | None = None
    ai_base_url: str | None = None
    ai_api_key_enc: str | None = None
    ai_model: str | None = None
    distill_config: str | None = None
    github_token_enc: str | None = None
    founder_username: str | None = None


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
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    cfg = await _get_or_create_config(session)
    store_settings = store.get_settings()

    return {
        "knowledge_repo_url": store_settings.get("knowledge_repo_url"),
        "knowledge_repo_path": store_settings.get("knowledge_repo_path"),
        "ssh_public_key": store_settings.get("ssh_public_key"),
        "ai_base_url": store_settings.get("ai_base_url"),
        "ai_api_key_set": bool(cfg.ai_api_key_enc),
        "ai_model": store_settings.get("ai_model"),
        "distill_config": store_settings.get("distill_config"),
        "founder_username": cfg.founder_username,
        "github_token_set": bool(cfg.github_token_enc),
    }


@router.patch("")
async def update_global_config(
    body: GlobalConfigUpdate,
    session: AsyncSession = Depends(get_session),
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    update_data = body.model_dump(exclude_unset=True)

    store_settings = store.get_settings()
    if store_settings.get("knowledge_repo_url") and "knowledge_repo_url" in update_data:
        raise HTTPException(
            status_code=400,
            detail="Knowledge repo URL cannot be changed once set",
        )

    settings_patch = {k: v for k, v in update_data.items() if k in _SETTINGS_FIELDS}
    sqlite_patch = {k: v for k, v in update_data.items() if k in _SQLITE_FIELDS}

    if settings_patch:
        await store.update_settings(settings_patch)

    if sqlite_patch:
        cfg = await _get_or_create_config(session)
        for key, val in sqlite_patch.items():
            setattr(cfg, key, val)
        cfg.updated_at = datetime.now(UTC)
        session.add(cfg)
        await session.commit()

    return {"ok": True}


@router.delete("")
async def reset_global_config(
    session: AsyncSession = Depends(get_session),
    store: KnowledgeStore = Depends(get_store),
    user: dict = Depends(require_auth),
):
    """Founder-only: wipe global config + global secrets + local knowledge clone."""
    cfg = await _get_or_create_config(session)
    if not cfg.founder_username or user.get("username") != cfg.founder_username:
        raise HTTPException(status_code=403, detail="Only the founder can reset")

    cfg.founder_username = None
    cfg.ssh_private_key_enc = None
    cfg.ai_api_key_enc = None
    cfg.github_token_enc = None
    cfg.updated_at = datetime.now(UTC)
    session.add(cfg)
    await session.commit()

    await store.update_settings({
        "knowledge_repo_url": None,
        "knowledge_repo_path": None,
        "ssh_public_key": None,
        "ai_base_url": None,
        "ai_model": None,
        "distill_config": None,
    })

    secrets = store.list("secrets")
    for s in secrets:
        await store.delete("secrets", s["id"])

    from app.services.knowledge_sync import _target_path
    dest = _target_path()
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)

    return {"ok": True}


@router.get("/ssh-key")
async def get_ssh_key(
    session: AsyncSession = Depends(get_session),
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    cfg = await _get_or_create_config(session)
    store_settings = store.get_settings()
    return {
        "ssh_public_key": store_settings.get("ssh_public_key"),
        "has_private_key": bool(cfg.ssh_private_key_enc),
    }


@router.post("/generate-ssh-key", status_code=201)
async def generate_ssh_key(
    session: AsyncSession = Depends(get_session),
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    """Generate a new Ed25519 SSH key pair."""
    cfg = await _get_or_create_config(session)
    public_key, private_key = generate_ssh_keypair()

    await store.update_settings({"ssh_public_key": public_key})

    cfg.ssh_private_key_enc = encrypt(private_key)
    cfg.updated_at = datetime.now(UTC)
    session.add(cfg)
    await session.commit()

    return {"ssh_public_key": public_key}


@router.post("/push-ssh-key-to-github")
async def push_ssh_key_to_github(
    store: KnowledgeStore = Depends(get_store),
    user: dict = Depends(require_auth),
):
    """Add the SSH public key to the user's GitHub account via API."""
    import requests as http_requests

    store_settings = await store.read_settings()
    pub_key = store_settings.get("ssh_public_key", "")
    if not pub_key:
        raise HTTPException(status_code=400, detail="No SSH public key. Generate one first.")

    token = user.get("github_token", "")
    if not token:
        raise HTTPException(status_code=400, detail="No GitHub token. Please re-login with GitHub.")

    resp = http_requests.post(
        "https://api.github.com/user/keys",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"title": "SuperPmAgent", "key": pub_key},
        timeout=15,
    )
    if resp.status_code == 422:
        errors = resp.json().get("errors", [])
        if any("already" in (e.get("message", "") or "") for e in errors):
            return {"ok": True, "message": "Key already exists on GitHub"}
        raise HTTPException(status_code=422, detail=resp.json().get("message", "Validation failed"))
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=resp.status_code, detail=f"GitHub API error: {resp.text[:300]}")
    return {"ok": True, "message": "SSH key added to GitHub", "key_id": resp.json().get("id")}


# ── Secrets (KnowledgeStore-backed) ───────────────────────────


@router.get("/secrets")
async def list_secrets(
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
) -> list[SecretOut]:
    secrets = store.list("secrets")
    return [
        SecretOut(id=s["id"], key=s["key"], value="***", category=s.get("category", "env"))
        for s in secrets
    ]


@router.post("/secrets", status_code=201)
async def create_secret(
    body: SecretCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    encrypted_value = encrypt(body.value)
    secret = await store.create("secrets", {
        "workspace_id": "__global__",
        "key": body.key,
        "value_enc": encrypted_value,
        "category": body.category,
    })
    return SecretOut(
        id=secret["id"],
        key=secret["key"],
        value="***",
        category=secret.get("category", "env"),
    )


@router.get("/secrets/{secret_id}/reveal")
async def reveal_secret(
    secret_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    secret = store.get("secrets", secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    return SecretOut(
        id=secret["id"],
        key=secret["key"],
        value=decrypt(secret["value_enc"]),
        category=secret.get("category", "env"),
    )


@router.delete("/secrets/{secret_id}", status_code=204)
async def delete_secret(
    secret_id: int,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    secret = store.get("secrets", secret_id)
    if not secret:
        raise HTTPException(status_code=404, detail="Secret not found")
    await store.delete("secrets", secret_id)

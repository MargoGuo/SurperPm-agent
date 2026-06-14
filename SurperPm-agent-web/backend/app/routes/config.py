"""Config tabs — integrations / profile / extensions / usage / ai."""
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.config import settings
from app.routes.deps import require_auth

router = APIRouter()

KNOWLEDGE_ROOT = (
    Path(settings.knowledge_repo_path) if settings.knowledge_repo_path else Path("knowledge")
)
PLUGIN_ROOT = Path(settings.plugin_repo_path) if settings.plugin_repo_path else None


@router.get("/integrations")
async def integrations(_user: dict = Depends(require_auth)) -> list:
    github_connected = bool(_user.get("github_token"))
    items = [
        {
            "name": "GitHub PAT",
            "endpoint": "https://api.github.com",
            "connected": github_connected,
        },
        {
            "name": "模型 endpoint",
            "endpoint": settings.anthropic_base_url or "https://api.anthropic.com",
            "connected": bool(settings.anthropic_api_key),
        },
        {
            "name": "豆包 API",
            "endpoint": settings.doubao_endpoint,
            "connected": bool(settings.doubao_api_key),
        },
        {
            "name": "LAP",
            "endpoint": settings.lap_url or "",
            "connected": bool(settings.lap_token),
        },
    ]
    return items


@router.get("/profile")
async def profile(_user: dict = Depends(require_auth)) -> dict:
    team_file = KNOWLEDGE_ROOT / "profiles" / "team.md"
    if team_file.is_file():
        return {"content": team_file.read_text(encoding="utf-8")}
    return {"content": ""}


@router.put("/profile")
async def update_profile(payload: dict, _user: dict = Depends(require_auth)) -> dict:
    team_file = KNOWLEDGE_ROOT / "profiles" / "team.md"
    team_file.parent.mkdir(parents=True, exist_ok=True)
    content = payload.get("content", "")
    team_file.write_text(content, encoding="utf-8")
    return {"ok": True}


@router.get("/extensions")
async def extensions(_user: dict = Depends(require_auth)) -> list:
    if not PLUGIN_ROOT or not PLUGIN_ROOT.is_dir():
        return []
    result = []
    for category_dir in sorted(PLUGIN_ROOT.iterdir()):
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue
        skill_file = category_dir / "SKILL.md"
        if skill_file.is_file():
            content = skill_file.read_text(encoding="utf-8")
            title = category_dir.name
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            result.append({
                "name": title,
                "category": category_dir.name,
                "path": str(category_dir.relative_to(PLUGIN_ROOT)),
            })
    return result


AI_CONFIG_FILE = Path(__file__).resolve().parent.parent.parent / "ai_config.json"

_AI_DEFAULTS = {"base_url": "", "api_key": "", "model": ""}


def _read_ai_config() -> dict:
    if AI_CONFIG_FILE.is_file():
        try:
            return {**_AI_DEFAULTS, **json.loads(AI_CONFIG_FILE.read_text("utf-8"))}
        except (json.JSONDecodeError, OSError):
            pass
    return dict(_AI_DEFAULTS)


def _write_ai_config(data: dict) -> None:
    AI_CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class AIConfigPayload(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


@router.get("/ai")
async def get_ai_config(_user: dict = Depends(require_auth)) -> dict:
    cfg = _read_ai_config()
    return {
        "base_url": cfg.get("base_url", ""),
        "api_key_masked": ("*" * 8 + cfg["api_key"][-4:]) if cfg.get("api_key") else "",
        "api_key_set": bool(cfg.get("api_key")),
        "model": cfg.get("model", ""),
    }


@router.patch("/ai")
async def update_ai_config(
    payload: AIConfigPayload, _user: dict = Depends(require_auth)
) -> dict:
    cfg = _read_ai_config()
    if payload.base_url is not None:
        cfg["base_url"] = payload.base_url
    if payload.api_key is not None:
        cfg["api_key"] = payload.api_key
    if payload.model is not None:
        cfg["model"] = payload.model
    _write_ai_config(cfg)
    return {"ok": True}


@router.get("/usage")
async def usage(
    _user: dict = Depends(require_auth),
) -> dict:
    from app.services.knowledge_store import get_store

    store = get_store()
    exes = store.list("executions")
    total_tokens = sum(e.get("token_used") or 0 for e in exes)
    return {
        "total_tokens": total_tokens,
        "total_executions": len(exes),
    }

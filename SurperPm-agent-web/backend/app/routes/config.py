"""Config tabs — integrations / profile / extensions / usage."""
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlmodel import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_session
from app.models.execution import Execution
from app.routes.deps import require_auth

router = APIRouter()

KNOWLEDGE_ROOT = Path(settings.knowledge_repo_path) if settings.knowledge_repo_path else Path("knowledge")
PLUGIN_ROOT = Path(settings.plugin_repo_path) if settings.plugin_repo_path else None


@router.get("/integrations")
async def integrations(_user: dict = Depends(require_auth)) -> list:
    items = [
        {
            "name": "GitHub PAT",
            "endpoint": "https://api.github.com",
            "connected": bool(settings.github_token),
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
            result.append({"name": title, "category": category_dir.name, "path": str(category_dir.relative_to(PLUGIN_ROOT))})
    return result


@router.get("/usage")
async def usage(
    session: AsyncSession = Depends(get_session),
    _user: dict = Depends(require_auth),
) -> dict:
    token_stmt = select(
        func.coalesce(func.sum(Execution.token_used), 0)
    )
    result = await session.execute(token_stmt)
    total_tokens = result.scalar() or 0

    count_stmt = select(func.count()).select_from(Execution)
    result = await session.execute(count_stmt)
    total_executions = result.scalar() or 0

    return {
        "total_tokens": total_tokens,
        "total_executions": total_executions,
    }

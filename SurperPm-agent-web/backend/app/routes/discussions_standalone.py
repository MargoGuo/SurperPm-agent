"""Standalone Discussions — pre-goal brainstorming chat (no goal_id required)."""
import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.routes.deps import require_auth
from app.services.event_bus import DISCUSSION_CREATED, bus
from app.services.knowledge_store import KnowledgeStore, get_store

router = APIRouter()


def _get_default_workspace_id(store: KnowledgeStore) -> str:
    workspaces = store.list("workspaces")
    if not workspaces:
        raise HTTPException(status_code=404, detail="No workspace found")
    return workspaces[0]["id"]


class StandaloneDiscussionCreate(BaseModel):
    content: str
    role: str = "user"
    topic_id: int | None = None
    image_data_uri: str | None = None


@router.get("")
async def list_standalone_discussions(
    topic_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    workspace_id = _get_default_workspace_id(store)
    rows = store.list_discussions(topic_id=topic_id)
    filtered = [
        r for r in rows
        if r.get("workspace_id") == workspace_id and r.get("goal_id") is None
    ]
    filtered.sort(key=lambda r: r.get("created_at", ""))
    return filtered[offset:offset + limit]


@router.post("")
async def create_standalone_discussion(
    body: StandaloneDiscussionCreate,
    store: KnowledgeStore = Depends(get_store),
    _user: dict = Depends(require_auth),
):
    workspace_id = _get_default_workspace_id(store)

    disc_data: dict = {
        "workspace_id": workspace_id,
        "goal_id": None,
        "role": body.role,
        "content": body.content,
        "topic_id": body.topic_id,
        "author": _user.get("username"),
    }
    if body.image_data_uri:
        disc_data["image_data_uri"] = body.image_data_uri
    discussion = await store.create_discussion(disc_data)

    await bus.emit(DISCUSSION_CREATED, {
        "id": discussion["id"],
        "workspace_id": workspace_id,
        "goal_id": None,
        "role": body.role,
        "content": body.content,
        "topic_id": body.topic_id,
        "created_at": discussion["created_at"],
    })

    if body.role == "user":
        from app.services.ai_chat import generate_ai_reply

        asyncio.create_task(
            generate_ai_reply(
                workspace_id, body.content,
                image_data_uri=body.image_data_uri,
                topic_id=body.topic_id,
            )
        )

    return discussion


_BASE_SYSTEM_PROMPT = (
    "You are a helpful project management assistant for SuperPmAgent. "
    "You help brainstorm ideas, discuss project direction, and clarify goals. "
    "Be concise and actionable. Reply in the same language the user uses.\n\n"
    "When the conversation reaches a point where concrete tasks or goals "
    "can be identified, output each proposed goal as a fenced code block "
    "with language tag `goal-proposal` containing a JSON object. Example:\n"
    "```goal-proposal\n"
    '{"title": "Implement user login", "description": "Add OAuth login flow"}\n'
    "```\n"
    "You can output multiple goal-proposal blocks in one reply. "
    "Only propose goals when the user seems ready to commit to actions, "
    "not during early exploration."
)


def _build_system_prompt() -> str:
    import json

    from app.services.knowledge_distiller import get_top_learnings

    prompt = _BASE_SYSTEM_PROMPT
    store = get_store()
    root = store._root.parent

    sections: list[str] = []

    # 1. Skills
    try:
        from app.routes.skills import _scan_skills
        skills = _scan_skills()
        if skills:
            lines = [f"- **{s['name']}**: {s['description']}" for s in skills]
            sections.append(
                "## Available Skills\n" + "\n".join(lines)
            )
    except Exception:
        pass

    # 2. Plugins
    try:
        plugins_dir = root / "plugins"
        if plugins_dir.is_dir():
            names = []
            for d in sorted(plugins_dir.iterdir()):
                if not d.is_dir() or d.name.startswith("."):
                    continue
                manifest = d / ".claude-plugin" / "plugin.json"
                if manifest.is_file():
                    m = json.loads(manifest.read_text(encoding="utf-8"))
                    desc = m.get("description", "")
                    names.append(f"- **{m.get('name', d.name)}**: {desc}")
            if names:
                sections.append(
                    "## Installed Plugins\n" + "\n".join(names)
                )
    except Exception:
        pass

    # 3. MCP Servers
    try:
        from app.routes.mcp import _read_servers
        servers = _read_servers()
        if servers:
            lines = []
            for name, cfg in servers.items():
                status = "enabled" if cfg.get("enabled") else "disabled"
                lines.append(f"- **{name}** ({status})")
            sections.append(
                "## MCP Servers\n" + "\n".join(lines)
            )
    except Exception:
        pass

    # 4. Knowledge structure
    try:
        dirs = []
        for p in sorted(root.iterdir()):
            if p.name.startswith(".") or p.name == "__pycache__":
                continue
            if p.is_dir():
                dirs.append(f"- `{p.name}/`")
            elif p.is_file() and p.suffix == ".md":
                dirs.append(f"- `{p.name}`")
        if dirs:
            sections.append(
                "## Knowledge Repository Structure\n" + "\n".join(dirs)
            )
    except Exception:
        pass

    # 5. Team profile
    try:
        team_md = root / "profiles" / "team.md"
        if team_md.is_file():
            content = team_md.read_text(encoding="utf-8")[:500]
            sections.append(f"## Team Profile\n{content}")
    except Exception:
        pass

    # 6. Domain knowledge summaries
    try:
        domain_dir = root / "domain"
        if domain_dir.is_dir():
            index = domain_dir / "INDEX.md"
            if index.is_file():
                content = index.read_text(encoding="utf-8")[:800]
                sections.append(f"## Domain Knowledge\n{content}")
    except Exception:
        pass

    # 7. Learnings
    learnings = get_top_learnings(budget_tokens=300)
    if learnings:
        sections.append(
            "## Team Learnings\n"
            "Use these to inform your answers:\n"
            f"{learnings}"
        )

    if sections:
        prompt += "\n\n" + "\n\n".join(sections)

    return prompt



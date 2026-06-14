"""Knowledge — tree + file read/write + session chat.

Reads from the SuperPmAgent-knowledge repo clone (KNOWLEDGE_REPO_PATH config).
Falls back to ./knowledge/ relative to the backend working directory.
"""
import json
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.routes.deps import require_auth, require_founder
from app.services.clarify_agent import run_clarify_agent
from app.services.clarify_executor import (
    append_conversation_entry,
    ensure_session_structure,
    register_sources,
    scaffold_notes,
)
from app.services.export_feishu_prd import export_session_to_feishu_prd

router = APIRouter()

KNOWLEDGE_ROOT = (
    Path(settings.knowledge_repo_path) if settings.knowledge_repo_path else Path("knowledge")
)


def _ensure_root() -> Path:
    KNOWLEDGE_ROOT.mkdir(parents=True, exist_ok=True)
    return KNOWLEDGE_ROOT


def _build_tree(p: Path, rel: Path) -> dict:
    """Recursively build a directory tree dict."""
    node: dict = {"path": str(rel), "name": p.name}
    if p.is_dir():
        children = []
        for child in sorted(p.iterdir()):
            if child.name.startswith("."):
                continue
            children.append(_build_tree(child, rel / child.name))
        node["children"] = children
    return node


@router.get("/tree")
async def tree(_user: dict = Depends(require_auth)) -> dict:
    """Return the knowledge/ directory tree."""
    root = _ensure_root()
    return _build_tree(root, Path("knowledge"))


@router.get("/file")
async def file(path: str, _user: dict = Depends(require_auth)) -> dict:
    """Read a single file by path."""
    target = _resolve(path)
    if not target.is_file():
        raise HTTPException(404, f"File not found: {path}")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


class FilePayload(BaseModel):
    path: str
    content: str


@router.put("/file")
async def update_file(payload: FilePayload, _user: dict = Depends(require_founder)) -> dict:
    """Write a file under knowledge/. Founder-only — the knowledge repo is a read-only mirror."""
    target = _resolve(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True}


class NewSessionPayload(BaseModel):
    name: str


@router.post("/session/new")
async def new_session(payload: NewSessionPayload, _user: dict = Depends(require_auth)) -> dict:
    """Create a new canonical session folder under knowledge/sessions/."""
    root = _ensure_root()
    session_dir = root / "sessions" / payload.name
    if session_dir.exists():
        raise HTTPException(409, f"Session already exists: {payload.name}")

    ensure_session_structure(root, payload.name)
    (session_dir / "notes.md").write_text(
        scaffold_notes(payload.name, "", []),
        encoding="utf-8",
    )

    return {
        "name": payload.name,
        "path": f"knowledge/sessions/{payload.name}",
    }


class ChatPayload(BaseModel):
    session: str
    message: str


class ClarifyPayload(BaseModel):
    session: str
    message: str
    source_urls: list[str] = Field(default_factory=list)
    use_agent: bool = True


class ExportFeishuPrdPayload(BaseModel):
    session: str
    title: str | None = None
    as_identity: str = "user"
    parent_token: str | None = None
    parent_position: str | None = None


@router.post("/session/clarify")
async def session_clarify(
    payload: ClarifyPayload,
    _user: dict = Depends(require_auth),
) -> dict:
    """Create or update a canonical clarify session under the knowledge repo."""
    root = _ensure_root()
    session_dir = ensure_session_structure(root, payload.session)
    notes_file = session_dir / "notes.md"

    source_records = register_sources(
        session_dir,
        message=payload.message,
        source_urls=payload.source_urls,
    )
    append_conversation_entry(
        session_dir,
        message=payload.message,
        source_records=source_records,
    )

    notes_created = False
    mode = "fallback"
    agent_response = ""
    agent_error = ""
    should_use_agent = (
        payload.use_agent
        and bool(settings.anthropic_api_key)
        and bool(settings.plugin_repo_path)
    )

    if should_use_agent:
        try:
            result = await run_clarify_agent(
                session_name=payload.session,
                message=payload.message,
                source_urls=[record["source_uri"] for record in source_records],
                knowledge_root=root,
            )
            agent_response = result.get("response", "")
            mode = result.get("mode", "agent")
        except Exception as exc:
            agent_error = str(exc)

    if not notes_file.exists():
        notes_file.write_text(
            scaffold_notes(
                payload.session,
                payload.message,
                [record["source_uri"] for record in source_records],
            ),
            encoding="utf-8",
        )
        notes_created = True

    return {
        "ok": True,
        "session": payload.session,
        "path": f"knowledge/sessions/{payload.session}",
        "knowledge_root": str(root.resolve()),
        "session_dir": str(session_dir.resolve()),
        "notes_created": notes_created,
        "registered_sources": len(source_records),
        "ready_for_goal": False,
        "mode": mode,
        "agent_response": agent_response,
        "agent_error": agent_error,
    }


@router.post("/session/chat")
async def session_chat(payload: ChatPayload, _user: dict = Depends(require_auth)) -> dict:
    """Append a chat turn to the session's chat.jsonl and return AI reply."""
    root = _ensure_root()
    session_dir = root / "sessions" / payload.session
    if not session_dir.is_dir():
        raise HTTPException(404, f"Session not found: {payload.session}")

    chat_file = session_dir / "chat.jsonl"
    now = datetime.now(UTC).isoformat()

    user_turn = json.dumps(
        {"role": "user", "content": payload.message, "ts": now},
        ensure_ascii=False,
    )

    reply_content = f"收到：{payload.message}。这是 MVP 占位回复，W2 将接入真实 AI。"
    reply_turn = json.dumps(
        {"role": "assistant", "content": reply_content, "ts": now},
        ensure_ascii=False,
    )

    with chat_file.open("a", encoding="utf-8") as f:
        f.write(user_turn + "\n")
        f.write(reply_turn + "\n")

    return {"reply": reply_content}


@router.post("/session/export/feishu-prd")
async def export_feishu_prd(
    payload: ExportFeishuPrdPayload,
    _user: dict = Depends(require_auth),
) -> dict:
    root = _ensure_root()
    try:
        return export_session_to_feishu_prd(
            session_name=payload.session,
            knowledge_root=root,
            title=payload.title,
            as_identity=payload.as_identity,
            parent_token=payload.parent_token,
            parent_position=payload.parent_position,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/sync")
async def sync_knowledge(_user: dict = Depends(require_auth)) -> dict:
    """Trigger a git clone/pull of the knowledge repo."""
    from app.services.knowledge_sync import ensure_knowledge_cloned

    result = await ensure_knowledge_cloned()
    if result:
        return {"ok": True, "path": str(result)}
    return {"ok": False, "message": "同步失败，请检查知识库配置或网络"}


# Future extension point: a `POST /webhook` endpoint receiving GitHub push
# events would call `ensure_knowledge_cloned()` for near-instant sync. The
# current implementation relies on the lifespan polling loop in app/main.py.


def _resolve(path: str) -> Path:
    """Resolve a knowledge-relative path safely."""
    root = _ensure_root()
    clean = path.removeprefix("knowledge/").removeprefix("knowledge\\")
    target = (root / clean).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise HTTPException(400, "Path traversal not allowed")
    return target

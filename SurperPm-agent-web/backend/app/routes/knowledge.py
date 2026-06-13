"""Knowledge — tree + file read/write + session chat.

Reads from the claude-for-knowledge repo clone (KNOWLEDGE_REPO_PATH config).
Falls back to ./knowledge/ relative to the backend working directory.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.routes.deps import require_auth

router = APIRouter()

KNOWLEDGE_ROOT = Path(settings.knowledge_repo_path) if settings.knowledge_repo_path else Path("knowledge")


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
async def update_file(payload: FilePayload, _user: dict = Depends(require_auth)) -> dict:
    """Write a file under knowledge/."""
    target = _resolve(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True}


class NewSessionPayload(BaseModel):
    name: str


@router.post("/session/new")
async def new_session(payload: NewSessionPayload, _user: dict = Depends(require_auth)) -> dict:
    """Create a new session folder under knowledge/sessions/."""
    root = _ensure_root()
    session_dir = root / "sessions" / payload.name
    if session_dir.exists():
        raise HTTPException(409, f"Session already exists: {payload.name}")

    session_dir.mkdir(parents=True)
    (session_dir / "chat.jsonl").write_text("", encoding="utf-8")
    (session_dir / "notes.md").write_text(
        f"# {payload.name}\n\n_Session created {datetime.now(timezone.utc).isoformat()}_\n",
        encoding="utf-8",
    )
    exec_dir = session_dir / "executions"
    exec_dir.mkdir()

    return {
        "name": payload.name,
        "path": f"knowledge/sessions/{payload.name}",
    }


class ChatPayload(BaseModel):
    session: str
    message: str


@router.post("/session/chat")
async def session_chat(payload: ChatPayload, _user: dict = Depends(require_auth)) -> dict:
    """Append a chat turn to the session's chat.jsonl and return AI reply."""
    root = _ensure_root()
    session_dir = root / "sessions" / payload.session
    if not session_dir.is_dir():
        raise HTTPException(404, f"Session not found: {payload.session}")

    chat_file = session_dir / "chat.jsonl"
    now = datetime.now(timezone.utc).isoformat()

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


def _resolve(path: str) -> Path:
    """Resolve a knowledge-relative path safely."""
    root = _ensure_root()
    clean = path.removeprefix("knowledge/").removeprefix("knowledge\\")
    target = (root / clean).resolve()
    if not str(target).startswith(str(root.resolve())):
        raise HTTPException(400, "Path traversal not allowed")
    return target

"""Tests for /api/knowledge endpoints.

Covers the full knowledge CRUD flow with real filesystem operations.
Uses a temp directory via monkeypatch to isolate from production data.
"""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routes import knowledge as k_mod


@pytest.fixture(autouse=True)
def _knowledge_tmp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Point KNOWLEDGE_ROOT to a temp directory for every test."""
    root = tmp_path / "knowledge"
    root.mkdir()
    monkeypatch.setattr(k_mod, "KNOWLEDGE_ROOT", root)
    # Seed profiles/team.md so file-read tests have something to read
    profiles = root / "profiles"
    profiles.mkdir()
    (profiles / "team.md").write_text("# Team\n\nDefault content.", encoding="utf-8")


@pytest.fixture()
def client():
    return TestClient(app)


# ── tree ──────────────────────────────────────────────────


def test_tree_returns_structure(client: TestClient):
    """GET /api/knowledge/tree returns a directory tree with children."""
    r = client.get("/api/knowledge/tree")
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "knowledge"
    assert "children" in body
    names = [c["name"] for c in body["children"]]
    assert "profiles" in names


# ── file read ─────────────────────────────────────────────


def test_file_read_returns_content(client: TestClient):
    """GET /api/knowledge/file returns path and content."""
    r = client.get("/api/knowledge/file", params={"path": "knowledge/profiles/team.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "knowledge/profiles/team.md"
    assert "Default content" in body["content"]


def test_file_read_missing_path_param(client: TestClient):
    """GET /api/knowledge/file without path param returns 422."""
    r = client.get("/api/knowledge/file")
    assert r.status_code == 422


def test_file_read_not_found(client: TestClient):
    """GET /api/knowledge/file for nonexistent file returns 404."""
    r = client.get("/api/knowledge/file", params={"path": "knowledge/nope.md"})
    assert r.status_code == 404


# ── file write ────────────────────────────────────────────


def test_file_update_writes_content(client: TestClient):
    """PUT /api/knowledge/file writes and subsequent read returns new content."""
    r = client.put(
        "/api/knowledge/file",
        json={"path": "knowledge/profiles/team.md", "content": "# Team\n\nUpdated."},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r2 = client.get("/api/knowledge/file", params={"path": "knowledge/profiles/team.md"})
    assert "Updated." in r2.json()["content"]


def test_file_update_creates_parent_dirs(client: TestClient):
    """PUT /api/knowledge/file creates intermediate directories."""
    r = client.put(
        "/api/knowledge/file",
        json={"path": "knowledge/domain/new-area/doc.md", "content": "# New"},
    )
    assert r.status_code == 200
    r2 = client.get("/api/knowledge/file", params={"path": "knowledge/domain/new-area/doc.md"})
    assert r2.status_code == 200


# ── session new ───────────────────────────────────────────


def test_new_session_creates_folder(client: TestClient):
    """POST /api/knowledge/session/new creates session with chat.jsonl + notes.md."""
    r = client.post(
        "/api/knowledge/session/new",
        json={"name": "test-session-001"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "test-session-001"
    assert "path" in body

    tree = client.get("/api/knowledge/tree").json()
    session_names = []
    for child in tree.get("children", []):
        if child["name"] == "sessions":
            for sc in child.get("children", []):
                session_names.append(sc["name"])
    assert "test-session-001" in session_names


def test_new_session_duplicate_returns_409(client: TestClient):
    """POST /api/knowledge/session/new with existing name returns 409."""
    client.post("/api/knowledge/session/new", json={"name": "dup-session"})
    r = client.post("/api/knowledge/session/new", json={"name": "dup-session"})
    assert r.status_code == 409


# ── session chat ──────────────────────────────────────────


def test_session_chat_returns_reply(client: TestClient):
    """POST /api/knowledge/session/chat appends to chat.jsonl and returns reply."""
    client.post("/api/knowledge/session/new", json={"name": "chat-test"})

    r = client.post(
        "/api/knowledge/session/chat",
        json={"session": "chat-test", "message": "给 user 表加 phone 字段"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body
    assert len(body["reply"]) > 0

    chat_r = client.get(
        "/api/knowledge/file",
        params={"path": "knowledge/sessions/chat-test/chat.jsonl"},
    )
    lines = chat_r.json()["content"].strip().split("\n")
    assert len(lines) == 2
    user_msg = json.loads(lines[0])
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "给 user 表加 phone 字段"
    asst_msg = json.loads(lines[1])
    assert asst_msg["role"] == "assistant"


def test_session_chat_nonexistent_session(client: TestClient):
    """POST /api/knowledge/session/chat with missing session returns 404."""
    r = client.post(
        "/api/knowledge/session/chat",
        json={"session": "no-such-session", "message": "hello"},
    )
    assert r.status_code == 404


def test_session_chat_appends_multiple(client: TestClient):
    """Multiple chat messages append correctly to chat.jsonl."""
    client.post("/api/knowledge/session/new", json={"name": "multi-chat"})
    client.post(
        "/api/knowledge/session/chat",
        json={"session": "multi-chat", "message": "第一条消息"},
    )
    client.post(
        "/api/knowledge/session/chat",
        json={"session": "multi-chat", "message": "第二条消息"},
    )

    chat_r = client.get(
        "/api/knowledge/file",
        params={"path": "knowledge/sessions/multi-chat/chat.jsonl"},
    )
    lines = chat_r.json()["content"].strip().split("\n")
    assert len(lines) == 4

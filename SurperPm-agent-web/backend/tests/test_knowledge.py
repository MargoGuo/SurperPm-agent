"""Tests for /api/knowledge endpoints.

Covers the full knowledge CRUD flow:
- GET /api/knowledge/tree
- GET /api/knowledge/file
- PUT /api/knowledge/file
- POST /api/knowledge/session/new
- POST /api/knowledge/session/chat
"""
from fastapi.testclient import TestClient

from app.main import app


def test_tree_returns_structure():
    """GET /api/knowledge/tree returns a directory tree object."""
    client = TestClient(app)
    r = client.get("/api/knowledge/tree")
    assert r.status_code == 200
    body = r.json()
    assert "path" in body
    assert "children" in body


def test_file_read_returns_content():
    """GET /api/knowledge/file returns path and content."""
    client = TestClient(app)
    r = client.get("/api/knowledge/file", params={"path": "knowledge/profiles/team.md"})
    assert r.status_code == 200
    body = r.json()
    assert body["path"] == "knowledge/profiles/team.md"
    assert "content" in body


def test_file_update_returns_ok():
    """PUT /api/knowledge/file writes and returns ok."""
    client = TestClient(app)
    r = client.put(
        "/api/knowledge/file",
        json={"path": "knowledge/profiles/team.md", "content": "# Team\n\nUpdated."},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_new_session_creates_folder():
    """POST /api/knowledge/session/new creates a session folder."""
    client = TestClient(app)
    r = client.post(
        "/api/knowledge/session/new",
        json={"name": "add-phone-field-20260613"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "add-phone-field-20260613"
    assert "path" in body


def test_session_chat_returns_reply():
    """POST /api/knowledge/session/chat returns AI reply."""
    client = TestClient(app)
    r = client.post(
        "/api/knowledge/session/chat",
        json={
            "session": "add-phone-field-20260613",
            "message": "给 user 表加 phone 字段",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "reply" in body


def test_file_read_missing_path_param():
    """GET /api/knowledge/file without path param returns 422."""
    client = TestClient(app)
    r = client.get("/api/knowledge/file")
    assert r.status_code == 422

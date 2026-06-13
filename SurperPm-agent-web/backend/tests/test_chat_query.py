"""Tests for POST /api/chat/query endpoint."""
import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


async def _empty_gen(*args, **kwargs):
    return
    yield


@pytest.fixture()
def chat_client(temp_git_repo):
    os.environ["PLUGIN_REPO_PATH"] = "/tmp/fake-plugin"
    os.environ["TARGET_REPO_PATH"] = temp_git_repo
    from app.main import app

    with TestClient(app) as client:
        yield client
    os.environ.pop("PLUGIN_REPO_PATH", None)
    os.environ.pop("TARGET_REPO_PATH", None)


def test_chat_query_returns_response(chat_client):
    """POST /api/chat/query returns inline response."""
    with patch("app.services.chat_query.query", side_effect=_empty_gen):
        r = chat_client.post("/api/chat/query", json={"prompt": "hello"})
        assert r.status_code == 200
        body = r.json()
        assert "response" in body
        assert body["error"] is None


def test_chat_query_with_plugin_param(chat_client):
    """POST /api/chat/query accepts optional plugin param."""
    with patch("app.services.chat_query.query", side_effect=_empty_gen):
        r = chat_client.post("/api/chat/query", json={"prompt": "test", "plugin": "SuperPmAgent-coding"})
        assert r.status_code == 200


def test_chat_query_error_handling(chat_client):
    """POST /api/chat/query returns error field on exception."""
    with patch("app.services.chat_query.query", side_effect=RuntimeError("sdk error")):
        r = chat_client.post("/api/chat/query", json={"prompt": "fail"})
        assert r.status_code == 200
        body = r.json()
        assert body["error"] == "sdk error"

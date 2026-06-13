"""V2 Discussions integration tests."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.database as db_module
from app.database import get_session
from app.main import app as fastapi_app


@pytest.fixture()
def client(tmp_path):
    """Fresh app client with clean temp-file DB for each test."""
    db_file = tmp_path / "test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    test_session_factory = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    original_engine = db_module.engine
    db_module.engine = test_engine

    async def _override_get_session():
        async with test_session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = _override_get_session

    with TestClient(fastapi_app) as c:
        yield c

    fastapi_app.dependency_overrides.clear()
    db_module.engine = original_engine


def _create_workspace(client: TestClient) -> str:
    """Helper: create a workspace and return its id."""
    res = client.post("/api/workspaces", json={
        "name": "Discuss Test WS",
        "slug": "discuss-test-ws",
    })
    assert res.status_code == 201
    return res.json()["id"]


def _create_goal(client: TestClient, ws_id: str, title: str = "Test Goal") -> int:
    """Helper: create a goal and return its id."""
    res = client.post(f"/api/workspaces/{ws_id}/goals", json={
        "title": title,
    })
    assert res.status_code == 201
    return res.json()["id"]


class TestDiscussions:
    def test_create_discussion(self, client):
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": "Hello world",
            "role": "user",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["content"] == "Hello world"
        assert data["role"] == "user"
        assert data["workspace_id"] == ws_id
        assert "id" in data

    def test_list_discussions_ordered_by_created_at_desc(self, client):
        ws_id = _create_workspace(client)
        client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": "First message",
            "role": "user",
        })
        client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": "Second message",
            "role": "user",
        })
        res = client.get(f"/api/workspaces/{ws_id}/discussions")
        assert res.status_code == 200
        items = res.json()
        assert len(items) == 2
        # Most recent first
        assert items[0]["content"] == "Second message"
        assert items[1]["content"] == "First message"

    def test_list_discussions_pagination(self, client):
        ws_id = _create_workspace(client)
        for i in range(5):
            client.post(f"/api/workspaces/{ws_id}/discussions", json={
                "content": f"Message {i}",
                "role": "user",
            })
        res = client.get(f"/api/workspaces/{ws_id}/discussions", params={
            "limit": 2, "offset": 0,
        })
        assert res.status_code == 200
        assert len(res.json()) == 2

        res = client.get(f"/api/workspaces/{ws_id}/discussions", params={
            "limit": 2, "offset": 3,
        })
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_goal_mention_triggers_execution(self, client):
        ws_id = _create_workspace(client)
        goal_id = _create_goal(client, ws_id, "My Goal")

        # Post a message mentioning the goal
        res = client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": f"Let's work on @goal-{goal_id} now",
            "role": "user",
        })
        assert res.status_code == 201

        # Verify goal status changed to "doing"
        res = client.get(f"/api/workspaces/{ws_id}/goals/{goal_id}")
        assert res.status_code == 200
        assert res.json()["status"] == "doing"

    def test_multiple_goal_mentions(self, client):
        ws_id = _create_workspace(client)
        goal_id_1 = _create_goal(client, ws_id, "Goal A")
        goal_id_2 = _create_goal(client, ws_id, "Goal B")

        res = client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": f"Execute @goal-{goal_id_1} and @goal-{goal_id_2}",
            "role": "user",
        })
        assert res.status_code == 201

        # Both goals should be "doing"
        res = client.get(f"/api/workspaces/{ws_id}/goals/{goal_id_1}")
        assert res.json()["status"] == "doing"

        res = client.get(f"/api/workspaces/{ws_id}/goals/{goal_id_2}")
        assert res.json()["status"] == "doing"

    def test_mention_nonexistent_goal_ignored(self, client):
        ws_id = _create_workspace(client)

        # Mention a goal that does not exist — should not error
        res = client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": "Let's do @goal-9999",
            "role": "user",
        })
        assert res.status_code == 201

    def test_get_discussion_by_id(self, client):
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/discussions", json={
            "content": "Find me later",
            "role": "agent",
        })
        disc_id = res.json()["id"]

        res = client.get(f"/api/workspaces/{ws_id}/discussions/{disc_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["content"] == "Find me later"
        assert data["role"] == "agent"

    def test_get_discussion_not_found(self, client):
        ws_id = _create_workspace(client)
        res = client.get(f"/api/workspaces/{ws_id}/discussions/9999")
        assert res.status_code == 404

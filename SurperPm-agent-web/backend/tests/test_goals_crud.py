"""V2 Goals CRUD integration tests."""
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
        "name": "Goal Test WS",
        "slug": "goal-test-ws",
    })
    assert res.status_code == 201
    return res.json()["id"]


class TestGoalsCRUD:
    def test_create_goal(self, client):
        ws_id = _create_workspace(client)
        res = client.post(f"/api/workspaces/{ws_id}/goals", json={
            "title": "Ship MVP",
            "description": "Launch the first version",
            "priority": 5,
        })
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Ship MVP"
        assert data["description"] == "Launch the first version"
        assert data["priority"] == 5
        assert data["status"] == "todo"
        assert data["workspace_id"] == ws_id
        assert "id" in data

    def test_list_goals(self, client):
        ws_id = _create_workspace(client)
        client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Goal A"})
        client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Goal B"})
        res = client.get(f"/api/workspaces/{ws_id}/goals")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_list_goals_with_status_filter(self, client):
        ws_id = _create_workspace(client)
        client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Todo Goal"})
        # Create and update one to "done"
        r = client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Done Goal"})
        goal_id = r.json()["id"]
        client.patch(f"/api/workspaces/{ws_id}/goals/{goal_id}", json={"status": "done"})

        # Filter by todo
        res = client.get(f"/api/workspaces/{ws_id}/goals", params={"status": "todo"})
        assert res.status_code == 200
        goals = res.json()
        assert len(goals) == 1
        assert goals[0]["title"] == "Todo Goal"

        # Filter by done
        res = client.get(f"/api/workspaces/{ws_id}/goals", params={"status": "done"})
        assert res.status_code == 200
        goals = res.json()
        assert len(goals) == 1
        assert goals[0]["title"] == "Done Goal"

    def test_get_goal(self, client):
        ws_id = _create_workspace(client)
        r = client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "My Goal"})
        goal_id = r.json()["id"]
        res = client.get(f"/api/workspaces/{ws_id}/goals/{goal_id}")
        assert res.status_code == 200
        assert res.json()["title"] == "My Goal"

    def test_get_goal_not_found(self, client):
        ws_id = _create_workspace(client)
        res = client.get(f"/api/workspaces/{ws_id}/goals/9999")
        assert res.status_code == 404

    def test_update_goal_status(self, client):
        ws_id = _create_workspace(client)
        r = client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Update Me"})
        goal_id = r.json()["id"]
        res = client.patch(f"/api/workspaces/{ws_id}/goals/{goal_id}", json={
            "status": "done",
        })
        assert res.status_code == 200
        assert res.json()["status"] == "done"

    def test_delete_goal(self, client):
        ws_id = _create_workspace(client)
        r = client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Delete Me"})
        goal_id = r.json()["id"]
        res = client.delete(f"/api/workspaces/{ws_id}/goals/{goal_id}")
        assert res.status_code == 204
        # Confirm it's gone
        res = client.get(f"/api/workspaces/{ws_id}/goals/{goal_id}")
        assert res.status_code == 404

    def test_execute_goal(self, client):
        ws_id = _create_workspace(client)
        r = client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Run Me"})
        goal_id = r.json()["id"]
        res = client.post(f"/api/workspaces/{ws_id}/goals/{goal_id}/execute")
        assert res.status_code == 202
        data = res.json()
        assert data["status"] == "doing"
        assert data["goal_id"] == goal_id

        # Verify goal is now "doing"
        res = client.get(f"/api/workspaces/{ws_id}/goals/{goal_id}")
        assert res.json()["status"] == "doing"

    def test_execute_goal_conflict(self, client):
        ws_id = _create_workspace(client)
        r = client.post(f"/api/workspaces/{ws_id}/goals", json={"title": "Conflict"})
        goal_id = r.json()["id"]
        # First execute succeeds
        res = client.post(f"/api/workspaces/{ws_id}/goals/{goal_id}/execute")
        assert res.status_code == 202
        # Second execute → 409
        res = client.post(f"/api/workspaces/{ws_id}/goals/{goal_id}/execute")
        assert res.status_code == 409

"""Phase 1: Database + WebSocket + Event Bus integration tests."""
import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

import app.database as db_module
from app.database import get_session
from app.main import app as fastapi_app


@pytest.fixture()
def client(tmp_path):
    """Fresh app client with clean temp-file DB for each test.

    Patches app.database.engine so the lifespan creates tables on the test DB,
    and overrides get_session dependency so routes use test sessions.
    """
    db_file = tmp_path / "test.db"
    test_engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_file}",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    test_session_factory = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    # Patch the module-level engine so lifespan's create_db_and_tables uses it
    original_engine = db_module.engine
    db_module.engine = test_engine

    async def _override_get_session():
        async with test_session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_session] = _override_get_session

    with TestClient(fastapi_app) as c:
        yield c

    # Restore
    fastapi_app.dependency_overrides.clear()
    db_module.engine = original_engine


class TestWorkspaceCRUD:
    def test_create_workspace(self, client):
        res = client.post("/api/workspaces", json={
            "name": "Test Project",
            "slug": "test-project",
        })
        assert res.status_code == 201
        data = res.json()
        assert data["name"] == "Test Project"
        assert data["slug"] == "test-project"
        assert "id" in data

    def test_list_workspaces(self, client):
        client.post("/api/workspaces", json={"name": "WS1", "slug": "ws-1"})
        client.post("/api/workspaces", json={"name": "WS2", "slug": "ws-2"})
        res = client.get("/api/workspaces")
        assert res.status_code == 200
        assert len(res.json()) == 2

    def test_get_workspace(self, client):
        create = client.post("/api/workspaces", json={"name": "WS", "slug": "ws"})
        ws_id = create.json()["id"]
        res = client.get(f"/api/workspaces/{ws_id}")
        assert res.status_code == 200
        assert res.json()["name"] == "WS"

    def test_get_workspace_not_found(self, client):
        res = client.get("/api/workspaces/nonexistent")
        assert res.status_code == 404

    def test_update_workspace(self, client):
        create = client.post("/api/workspaces", json={"name": "WS", "slug": "ws"})
        ws_id = create.json()["id"]
        res = client.patch(f"/api/workspaces/{ws_id}", json={"name": "Updated"})
        assert res.status_code == 200
        assert res.json()["name"] == "Updated"

    def test_delete_workspace(self, client):
        create = client.post("/api/workspaces", json={"name": "WS", "slug": "ws"})
        ws_id = create.json()["id"]
        res = client.delete(f"/api/workspaces/{ws_id}")
        assert res.status_code == 204
        res = client.get(f"/api/workspaces/{ws_id}")
        assert res.status_code == 404


class TestWebSocket:
    def test_ws_connect(self, client):
        with client.websocket_connect("/ws/test-ws-id") as ws:
            # Connection should succeed — send text to confirm channel is open
            ws.send_text("ping")


class TestEventBus:
    def test_emit_and_receive(self):
        from app.services.event_bus import EventBus
        bus = EventBus()
        received = []

        async def handler(payload):
            received.append(payload)

        bus.on("test_event", handler)
        asyncio.run(bus.emit("test_event", {"key": "value"}))
        assert received == [{"key": "value"}]

    def test_multiple_handlers(self):
        from app.services.event_bus import EventBus
        bus = EventBus()
        results = []

        async def h1(payload):
            results.append("h1")

        async def h2(payload):
            results.append("h2")

        bus.on("ev", h1)
        bus.on("ev", h2)
        asyncio.run(bus.emit("ev", {}))
        assert results == ["h1", "h2"]

    def test_no_handler(self):
        from app.services.event_bus import EventBus
        bus = EventBus()
        # Should not raise
        asyncio.run(bus.emit("unknown_event", {}))


class TestHealth:
    def test_health_endpoint(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_root_endpoint(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["name"] == "SuperPmAgent-web"

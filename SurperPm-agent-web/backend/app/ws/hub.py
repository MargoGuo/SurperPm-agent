"""WebSocket connection manager — broadcasts events to workspace subscribers."""
from collections import defaultdict

from fastapi import WebSocket


class WSHub:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, workspace_id: str, ws: WebSocket):
        await ws.accept()
        self._connections[workspace_id].append(ws)

    def disconnect(self, workspace_id: str, ws: WebSocket):
        conns = self._connections[workspace_id]
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, workspace_id: str, event: str, payload: dict):
        message = {"event": event, "data": payload}
        dead: list[WebSocket] = []
        for ws in self._connections[workspace_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections[workspace_id].remove(ws)


hub = WSHub()

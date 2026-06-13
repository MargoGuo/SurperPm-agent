from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws import hub

router = APIRouter()

@router.websocket("/ws/{workspace_id}")
async def websocket_endpoint(websocket: WebSocket, workspace_id: str):
    await hub.connect(workspace_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Client can send ping, we just ignore for now
    except WebSocketDisconnect:
        hub.disconnect(workspace_id, websocket)

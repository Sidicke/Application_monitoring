"""WebSocket router for real-time measurement streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    await manager.connect(device_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle state updates from hardware via WebSocket (Faster than HTTP POST)
            if data.get("type") == "hardware_state_update":
                await manager.broadcast(device_id, {
                    "type": "hardware_update",
                    "data": data.get("data")
                })
    except (WebSocketDisconnect, Exception):
        manager.disconnect(device_id, websocket)

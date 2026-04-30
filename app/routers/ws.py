"""WebSocket router for real-time measurement streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    await manager.connect(device_id, websocket)
    try:
        while True:
            # Keep connection alive — client can send pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(device_id, websocket)

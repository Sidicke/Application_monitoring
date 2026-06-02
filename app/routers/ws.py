"""WebSocket router for real-time measurement streaming."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


import logging

logger = logging.getLogger(__name__)

@router.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: int):
    await manager.connect(device_id, websocket)
    try:
        while True:
            try:
                text = await websocket.receive_text()
                import json
                data = json.loads(text)
                # Handle state updates from hardware via WebSocket
                if data.get("type") == "hardware_state_update":
                    await manager.broadcast(device_id, {
                        "type": "hardware_update",
                        "data": data.get("data")
                    })
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON via WS from device {device_id}: {text}")
            except WebSocketDisconnect:
                break # Client disconnected normally
            except Exception as e:
                logger.error(f"Error processing WS message for {device_id}: {e}")
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(device_id, websocket)


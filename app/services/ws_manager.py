"""WebSocket connection manager for real-time data push."""

from fastapi import WebSocket
from typing import Dict, List
import json


class ConnectionManager:
    """Manages WebSocket connections grouped by device_id."""

    def __init__(self):
        self.active: Dict[int, List[WebSocket]] = {}

    async def connect(self, device_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(device_id, []).append(ws)

    def disconnect(self, device_id: int, ws: WebSocket):
        if device_id in self.active:
            self.active[device_id] = [c for c in self.active[device_id] if c != ws]

    async def broadcast(self, device_id: int, data: dict):
        """Send data to all clients watching a device."""
        import logging
        logger = logging.getLogger(__name__)
        
        connections = list(self.active.get(device_id, []))
        logger.info(f"WS Broadcast to device {device_id} ({len(connections)} clients): {data.get('type')}")
        
        for ws in connections:
            try:
                await ws.send_text(json.dumps(data))
            except Exception as e:
                logger.warning(f"WS send failed for client on device {device_id}: {e}")
                self.disconnect(device_id, ws)


manager = ConnectionManager()

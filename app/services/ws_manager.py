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
        for ws in self.active.get(device_id, []):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.disconnect(device_id, ws)


manager = ConnectionManager()

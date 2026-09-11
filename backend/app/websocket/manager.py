from __future__ import annotations
import asyncio
import json
from typing import Optional
from fastapi import WebSocket
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections for the dashboard."""

    def __init__(self):
        self._connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.append(websocket)
        logger.info({"event": "ws_connected", "total": len(self._connections)})

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self._connections:
                self._connections.remove(websocket)
        logger.info({"event": "ws_disconnected", "total": len(self._connections)})

    async def broadcast(self, message: dict) -> None:
        """Send a JSON message to all connected dashboard clients."""
        if not self._connections:
            return
        payload = json.dumps(message)
        dead = []
        async with self._lock:
            connections = list(self._connections)
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    if ws in self._connections:
                        self._connections.remove(ws)

    def connection_count(self) -> int:
        return len(self._connections)


# Global singleton
ws_manager = ConnectionManager()

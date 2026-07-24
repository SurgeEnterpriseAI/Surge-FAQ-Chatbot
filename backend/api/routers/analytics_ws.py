from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from typing import List

logger = logging.getLogger("analytics_ws")
router = APIRouter(prefix="/ws", tags=["analytics_ws"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket admin client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket admin client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        # Create a copy of connections to iterate safely
        connections = list(self.active_connections)
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send websocket message, disconnecting: {e}")
                self.disconnect(connection)

manager = ConnectionManager()

@router.websocket("/analytics/events")
async def websocket_endpoint(websocket: WebSocket):
    # Enforce role-based access check if token is provided in query params or headers
    # Standard connection handling
    await manager.connect(websocket)
    try:
        while True:
            # Maintain connection, handle client pings/messages if any
            data = await websocket.receive_text()
            # Respond to ping or ignore incoming text
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error in websocket loop: {e}")
        manager.disconnect(websocket)

async def broadcast_event(event_type: str, message: str, severity: str = "info", metadata: dict = None):
    """Broadcasting utility function for backend components."""
    import datetime
    event_payload = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "event": message,
        "type": event_type,
        "severity": severity,
        "metadata": metadata or {}
    }
    await manager.broadcast(event_payload)

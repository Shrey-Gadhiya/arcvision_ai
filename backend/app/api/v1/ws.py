import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.event_bus import event_bus

logger = logging.getLogger("arc_vision.ws")
router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await event_bus.register_ws(websocket)
    try:
        # Keep connection open and receive optional client messages / ping-pong
        while True:
            data = await websocket.receive_text()
            # Client can send ping
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await event_bus.unregister_ws(websocket)
    except Exception as e:
        logger.error(f"WebSocket client error: {e}")
        await event_bus.unregister_ws(websocket)

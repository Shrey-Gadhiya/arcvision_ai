import asyncio
import json
import logging
from typing import Dict, Set, Callable, Any
from datetime import datetime, timezone

logger = logging.getLogger("arc_vision.event_bus")

class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, Set[Callable[[Dict[str, Any]], Any]]] = {}
        self._ws_clients: Set[Any] = set()
        self._lock = asyncio.Lock()

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Any]):
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(callback)

    def unsubscribe(self, topic: str, callback: Callable[[Dict[str, Any]], Any]):
        if topic in self._subscribers:
            self._subscribers[topic].discard(callback)

    async def register_ws(self, websocket: Any):
        async with self._lock:
            self._ws_clients.add(websocket)
            logger.info(f"WebSocket client registered. Total active: {len(self._ws_clients)}")

    async def unregister_ws(self, websocket: Any):
        async with self._lock:
            self._ws_clients.discard(websocket)
            logger.info(f"WebSocket client unregistered. Total active: {len(self._ws_clients)}")

    async def publish(self, topic: str, data: Dict[str, Any]):
        payload = {
            "topic": topic,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }
        
        # Dispatch to in-process subscribers
        if topic in self._subscribers:
            for callback in list(self._subscribers[topic]):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(payload))
                    else:
                        callback(payload)
                except Exception as e:
                    logger.error(f"Error in subscriber callback for {topic}: {e}")

        # Wildcard subscribers
        if "*" in self._subscribers:
            for callback in list(self._subscribers["*"]):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        asyncio.create_task(callback(payload))
                    else:
                        callback(payload)
                except Exception as e:
                    logger.error(f"Error in wildcard subscriber callback: {e}")

        # Broadcast to WebSockets
        if self._ws_clients:
            msg_str = json.dumps(payload, default=str)
            stale_clients = []
            async with self._lock:
                for ws in self._ws_clients:
                    try:
                        await ws.send_text(msg_str)
                    except Exception:
                        stale_clients.append(ws)
                for ws in stale_clients:
                    self._ws_clients.discard(ws)

event_bus = EventBus()

"""WebSocket endpoint for real-time signal updates"""

import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.services import signal_store

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active: List[WebSocket] = []
    
    async def connect(self, ws: WebSocket):
        """Accept and register a new WebSocket connection"""
        await ws.accept()
        self.active.append(ws)
        logger.info(f"WS client connected — total: {len(self.active)}")
    
    def disconnect(self, ws: WebSocket):
        """Remove a WebSocket connection"""
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"WS client disconnected — total: {len(self.active)}")
    
    async def broadcast(self, msg: dict):
        """Broadcast message to all connected clients"""
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        
        # Clean up dead connections
        for ws in dead:
            self.disconnect(ws)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/signals")
async def websocket_signals(ws: WebSocket):
    """WebSocket endpoint for real-time signal updates"""
    await manager.connect(ws)
    
    # Send initial state immediately
    state = signal_store.get_state()
    initial = {
        "type": "full_update",
        "signals": state["signals"],
        "history": state["history"],
        "stats": state["stats"],
        "next_cycle": 0,  # Will be updated by main app
    }
    
    # Serialize datetime objects
    await ws.send_json(json.loads(json.dumps(initial, default=str)))
    
    # Keep connection alive and send periodic updates
    try:
        while True:
            await asyncio.sleep(30)
            try:
                await ws.send_json({
                    "type": "ping",
                    "timestamp": json.dumps({"now": "now"}, default=str),
                })
            except Exception:
                break
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(ws)


async def broadcast_update():
    """Broadcast state update to all connected clients"""
    state = signal_store.get_state()
    msg = {
        "type": "full_update",
        "signals": state["signals"],
        "history": state["history"],
        "stats": state["stats"],
        "next_cycle": 0,  # Will be set by main app
    }
    
    # Serialize datetime objects
    msg_str = json.dumps(msg, default=str)
    msg_obj = json.loads(msg_str)
    
    await manager.broadcast(msg_obj)
    logger.info(f"Broadcast sent to {len(manager.active)} clients")

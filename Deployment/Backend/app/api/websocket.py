"""WebSocket endpoint for real-time signal updates"""

import asyncio
import json
from typing import List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.api.signals import enrich_signal_for_api
from app.services import signal_store, calendar_service, news_service, price_service

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
    
    logger.debug(f"WS initial: state has {len(state['signals'])} signals: {[s.get('pair') for s in state['signals']]}")
    
    enriched_signals = [enrich_signal_for_api(s) for s in state["signals"]]
    logger.debug(f"WS initial: enriched {len(enriched_signals)} signals")
    
    initial = {
        "type": "full_update",
        "signals": enriched_signals,
        "history": state["history"],
        "stats": state["stats"],
        "calendar": calendar_service.get_upcoming(hours_ahead=24),
        "news": news_service.get_articles(limit=15),
        "prices": price_service.get_prices(),
        "next_cycle": 0,  # Will be updated by main app
    }
    
    # Serialize datetime objects
    serialized = json.loads(json.dumps(initial, default=str))
    logger.debug(f"WS initial: sending {len(serialized.get('signals', []))} signals to client")
    
    await ws.send_json(serialized)
    
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


async def broadcast_update(include_prices: bool = True):
    """Broadcast full state update to all connected clients"""
    state = signal_store.get_state()
    
    logger.debug(f"broadcast_update: state has {len(state['signals'])} signals: {[s.get('pair') for s in state['signals']]}")
    
    enriched_signals = [enrich_signal_for_api(s) for s in state["signals"]]
    logger.debug(f"broadcast_update: enriched {len(enriched_signals)} signals")
    
    msg = {
        "type": "full_update",
        "signals": enriched_signals,
        "history": state["history"],
        "stats": state["stats"],
        "calendar": calendar_service.get_upcoming(hours_ahead=24),
        "news": news_service.get_articles(limit=15),
        "next_cycle": 0,  # Will be set by main app
    }
    
    if include_prices:
        msg["prices"] = price_service.get_prices()
    
    # Serialize datetime objects
    msg_str = json.dumps(msg, default=str)
    msg_obj = json.loads(msg_str)
    
    logger.debug(f"broadcast_update: final message has {len(msg_obj.get('signals', []))} signals")
    
    await manager.broadcast(msg_obj)
    logger.info(f"Full update broadcast to {len(manager.active)} clients")


async def broadcast_prices():
    """Broadcast lightweight price update to all connected clients"""
    prices = price_service.get_prices()
    msg = {
        "type": "price_update",
        "prices": prices,
    }
    
    await manager.broadcast(msg)
    logger.debug(f"Price update broadcast to {len(manager.active)} clients")


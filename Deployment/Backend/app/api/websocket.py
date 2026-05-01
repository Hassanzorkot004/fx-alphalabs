"""WebSocket endpoint for real-time signal updates"""

import asyncio
import json
import math
from datetime import datetime, timezone
from typing import List, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from app.api.signals import enrich_signal_for_api
from app.services import signal_store, calendar_service, news_service, price_service
from app.services.live_context_service import live_context_service

router = APIRouter()


def clean_nan(obj: Any) -> Any:
    """Recursively replace NaN, Infinity, and Timestamp with JSON-serializable values"""
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(item) for item in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    elif hasattr(obj, 'isoformat'):  # datetime, Timestamp, etc.
        return obj.isoformat()
    else:
        return obj


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
            except Exception as e:
                logger.error(f"Broadcast send_json failed: {e}")
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
    
    # Get live context for all signals
    prices = price_service.get_prices()
    live_contexts = live_context_service.get_all_contexts(state["signals"], prices)
    
    # Get next cycle countdown
    from main import get_next_cycle_seconds
    next_cycle_seconds = get_next_cycle_seconds()
    
    initial = {
        "type": "full_update",
        "signals": enriched_signals,
        "history": state["history"],
        "stats": state["stats"],
        "calendar": calendar_service.get_upcoming(hours_ahead=24),
        "news": news_service.get_articles(limit=15),
        "prices": prices,
        "live_contexts": live_contexts,
        "next_cycle": next_cycle_seconds,
    }
    
    logger.debug(f"WS initial: sending {len(initial.get('signals', []))} signals to client")
    
    try:
        # Clean NaN values and serialize
        cleaned = clean_nan(initial)
        json_str = json.dumps(cleaned, default=str)
        await ws.send_text(json_str)
    except Exception as e:
        logger.error(f"Failed to send initial state: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Keep connection alive by sending periodic pings
    try:
        while True:
            await asyncio.sleep(30)
            try:
                await ws.send_json({
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
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
    
    # Get live context for all signals
    prices = price_service.get_prices() if include_prices else {}
    live_contexts = live_context_service.get_all_contexts(state["signals"], prices)
    
    # Get next cycle countdown
    from main import get_next_cycle_seconds
    next_cycle_seconds = get_next_cycle_seconds()
    
    msg = {
        "type": "full_update",
        "signals": enriched_signals,
        "history": state["history"],
        "stats": state["stats"],
        "calendar": calendar_service.get_upcoming(hours_ahead=24),
        "news": news_service.get_articles(limit=15),
        "live_contexts": live_contexts,
        "next_cycle": next_cycle_seconds,
    }
    
    if include_prices:
        msg["prices"] = prices
    
    logger.debug(f"broadcast_update: final message has {len(msg.get('signals', []))} signals")
    
    # Clean NaN values and serialize datetime objects before broadcasting
    cleaned = clean_nan(msg)
    serialized = json.loads(json.dumps(cleaned, default=str))
    await manager.broadcast(serialized)
    logger.info(f"Full update broadcast to {len(manager.active)} clients")


async def broadcast_prices():
    """Broadcast lightweight price + context update to all connected clients"""
    state = signal_store.get_state()
    prices = price_service.get_prices()
    
    # Get live context for all signals (includes validity checks)
    live_contexts = live_context_service.get_all_contexts(state["signals"], prices)
    
    msg = {
        "type": "context_update",
        "prices": prices,
        "live_contexts": live_contexts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Clean NaN values before broadcasting
    cleaned = clean_nan(msg)
    await manager.broadcast(cleaned)
    logger.info(f"✓ Context update broadcast to {len(manager.active)} clients")


async def broadcast_news_alert(pair: str, spike_data: dict):
    """Broadcast news alert to all connected clients"""
    msg = {
        "type": "news_alert",
        "pair": pair,
        "spike_data": spike_data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Clean NaN values before broadcasting
    cleaned = clean_nan(msg)
    await manager.broadcast(cleaned)
    logger.info(f"News alert broadcast for {pair} to {len(manager.active)} clients")


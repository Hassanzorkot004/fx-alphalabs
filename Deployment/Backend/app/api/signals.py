import json
import math
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.services import agent_service, signal_store

router = APIRouter()


def _clean_nan(obj):
    """Recursively replace NaN/Inf with None so JSON serialization doesn't crash."""
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    elif isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def enrich_signal_for_api(s: dict) -> dict:
    """Add computed fields and sanitize NaN values."""
    out = dict(s)
    
    # Compute signal age and lifecycle
    try:
        ts = datetime.fromisoformat(str(s.get("timestamp", "")).replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        out["age_hours"] = round(age_hours, 2)
        
        agreement = s.get("agent_agreement", "CONFLICT")
        horizon = 8.0 if agreement == "FULL" else 12.0
        pct_elapsed = age_hours / horizon
        
        if pct_elapsed >= 1.0:
            out["lifecycle_status"] = "expired"
        elif pct_elapsed >= 0.75:
            out["lifecycle_status"] = "near_expiry"
        else:
            out["lifecycle_status"] = "active"
        
        out["horizon_hours"] = horizon
        out["pct_elapsed"] = round(pct_elapsed, 3)
    except Exception:
        out["age_hours"] = 0
        out["lifecycle_status"] = "active"
        out["horizon_hours"] = 12
        out["pct_elapsed"] = 0

    # Parse headlines from JSON string if needed
    headlines = out.get("headlines", "[]")
    if isinstance(headlines, str):
        try:
            out["headlines"] = json.loads(headlines)
        except Exception:
            out["headlines"] = []

    # Clean NaN/Inf — pandas fills missing numerics with NaN which breaks JSON
    return _clean_nan(out)


@router.get("/signals")
async def get_signals():
    """Get latest signals with lifecycle enrichment"""
    state = signal_store.get_state()
    enriched = [enrich_signal_for_api(s) for s in state["signals"]]
    return {"signals": enriched}


@router.get("/history")
async def get_history():
    """Get signal history"""
    state = signal_store.get_state()
    enriched = [enrich_signal_for_api(s) for s in state["history"]]
    return {"history": enriched, "n": len(enriched)}


@router.get("/stats")
async def get_stats():
    """Get performance statistics"""
    state = signal_store.get_state()
    return state["stats"]


@router.post("/run-now")
async def run_now():
    """Force an immediate agent cycle"""
    if agent_service.is_running:
        return {"status": "already_running", "cycle": agent_service.cycle_number}
    
    try:
        import asyncio
        from app.api.websocket import broadcast_update

        async def _run_and_broadcast():
            signals_list = await agent_service.run_cycle()
            signal_store.update(signals_list)
            await broadcast_update()

        asyncio.create_task(_run_and_broadcast())
        return {"status": "started", "cycle": agent_service.cycle_number + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

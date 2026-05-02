"""Signal endpoints"""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.auth.security import get_current_user
from app.services import agent_service, signal_store

router = APIRouter()


def enrich_signal_for_api(s: dict) -> dict:
    out = dict(s)

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

    headlines = out.get("headlines", "[]")
    if isinstance(headlines, str):
        try:
            out["headlines"] = json.loads(headlines)
        except Exception:
            out["headlines"] = []

    return out


@router.get("/signals")
async def get_signals(current_user=Depends(get_current_user)):
    state = signal_store.get_state()
    enriched = [enrich_signal_for_api(s) for s in state["signals"]]
    return {"signals": enriched}


@router.get("/history")
async def get_history(current_user=Depends(get_current_user)):
    state = signal_store.get_state()
    return {"history": state["history"], "n": len(state["history"])}


@router.get("/stats")
async def get_stats(current_user=Depends(get_current_user)):
    state = signal_store.get_state()
    return state["stats"]


@router.post("/run-now")
async def run_now(current_user=Depends(get_current_user)):
    if agent_service.is_running:
        return {"status": "already_running", "cycle": agent_service.cycle_number}

    try:
        import asyncio
        asyncio.create_task(agent_service.run_cycle())
        return {"status": "started", "cycle": agent_service.cycle_number + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
"""Signal endpoints"""

from fastapi import APIRouter, HTTPException

from app.services import agent_service, signal_store

router = APIRouter()


@router.get("/signals")
async def get_signals():
    """Get latest signals"""
    state = signal_store.get_state()
    return {"signals": state["signals"]}


@router.get("/history")
async def get_history():
    """Get signal history"""
    state = signal_store.get_state()
    return {"history": state["history"], "n": len(state["history"])}


@router.get("/stats")
async def get_stats():
    """Get performance statistics"""
    state = signal_store.get_state()
    return state["stats"]


@router.post("/run-now")
async def run_now():
    """Force an immediate agent cycle (for testing)"""
    if agent_service.is_running:
        return {"status": "already_running", "cycle": agent_service.cycle_number}
    
    try:
        # Run cycle in background (don't await)
        import asyncio
        asyncio.create_task(agent_service.run_cycle())
        return {"status": "started", "cycle": agent_service.cycle_number + 1}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

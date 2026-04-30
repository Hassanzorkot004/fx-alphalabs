"""Health check endpoint"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.services import agent_service

router = APIRouter()


@router.get("/health")
async def health():
    """Health check endpoint with system status"""
    return {
        "status": "ok",
        "version": "2.0.0",
        "agent_running": agent_service.is_running,
        "agent_initialized": agent_service.is_initialized,
        "cycle_number": agent_service.cycle_number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

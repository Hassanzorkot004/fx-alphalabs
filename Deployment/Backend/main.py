"""
FX AlphaLab Backend - Clean FastAPI application

No subprocess, no hardcoded paths, proper imports.
Uses fx_alphalab package directly via Python imports.
"""

import time
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import health, signals, websocket
from app.config import settings
from app.services import agent_service, signal_store

# Global state for next cycle tracking
next_cycle_ts = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic"""
    global next_cycle_ts
    
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║   FX AlphaLab  ·  Backend FastAPI                       ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"  Host     : {settings.HOST}:{settings.PORT}")
    logger.info(f"  Outputs  : {settings.OUTPUTS_DIR}")
    logger.info(f"  Signals  : {settings.SIGNALS_CSV}")
    
    # Initialize services
    try:
        agent_service.initialize()
        signal_store.load_from_csv()
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        logger.error("Make sure fx_alphalab is installed: pip install -e ../../fx_alphalab")
        raise
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_agent_cycle,
        trigger="interval",
        minutes=settings.RUN_EVERY_MINS,
        id="agent_cycle",
        max_instances=1,
        next_run_time=datetime.now() if settings.RUN_ON_STARTUP else None,
    )
    scheduler.start()
    next_cycle_ts = time.time() + (settings.RUN_EVERY_MINS * 60)
    
    logger.info(f"Scheduler started — agent runs every {settings.RUN_EVERY_MINS} min")
    logger.success(f"✓ Backend ready on http://{settings.HOST}:{settings.PORT}")
    
    yield
    
    # Shutdown
    scheduler.shutdown()
    logger.info("Backend stopped")


app = FastAPI(
    title="FX AlphaLab API",
    version="2.0.0",
    description="Multi-agent FX trading signal system",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(signals.router, prefix="/api", tags=["signals"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])


async def run_agent_cycle():
    """Scheduled agent execution"""
    global next_cycle_ts
    
    try:
        signals_list = await agent_service.run_cycle()
        signal_store.update(signals_list)
        await websocket.broadcast_update()
        next_cycle_ts = time.time() + (settings.RUN_EVERY_MINS * 60)
    except Exception as e:
        logger.error(f"Agent cycle failed: {e}")
        import traceback
        traceback.print_exc()


def get_next_cycle_seconds() -> int:
    """Get seconds until next cycle"""
    remaining = int(next_cycle_ts - time.time())
    return max(0, remaining)


# Export for use in routes
app.state.get_next_cycle_seconds = get_next_cycle_seconds


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level="info",
    )

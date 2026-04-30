"""
FX AlphaLab Backend - Clean FastAPI application

No subprocess, no hardcoded paths, proper imports.
Uses fx_alphalab package directly via Python imports.
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# Load .env file before importing anything else
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"✓ Loaded .env: GROQ_API_KEY={'SET' if os.getenv('GROQ_API_KEY') else 'NOT SET'}, FRED_API_KEY={'SET' if os.getenv('FRED_API_KEY') else 'NOT SET'}")

from app.api import health, signals, websocket, prices, calendar, news, alphabot
from app.config import settings
from app.services import agent_service, signal_store, news_service

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
        
        # Initialize news service with RSS feeds from config
        news_service._feeds = settings.RSS_FEEDS
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        logger.error("Make sure fx_alphalab is installed: pip install -e ../../fx_alphalab")
        raise
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    
    # Agent cycle job (every 60 minutes)
    scheduler.add_job(
        run_agent_cycle,
        trigger="interval",
        minutes=settings.RUN_EVERY_MINS,
        id="agent_cycle",
        max_instances=1,
        next_run_time=datetime.now() if settings.RUN_ON_STARTUP else None,
    )
    
    # Price broadcast job (every 30 seconds)
    scheduler.add_job(
        broadcast_price_update,
        trigger="interval",
        seconds=30,
        id="price_broadcast",
        max_instances=1,
    )
    
    # Stats computation job (every 6 hours)
    scheduler.add_job(
        compute_stats_cache,
        trigger="interval",
        hours=6,
        id="stats_computation",
        max_instances=1,
    )
    
    scheduler.start()
    next_cycle_ts = time.time() + (settings.RUN_EVERY_MINS * 60)
    
    logger.info(f"Scheduler started:")
    logger.info(f"  - Agent cycle: every {settings.RUN_EVERY_MINS} min")
    logger.info(f"  - Price updates: every 30 seconds")
    logger.info(f"  - Stats computation: every 6 hours")
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
app.include_router(prices.router, prefix="/api", tags=["prices"])
app.include_router(calendar.router, prefix="/api", tags=["calendar"])
app.include_router(news.router, prefix="/api", tags=["news"])
app.include_router(alphabot.router, prefix="/api", tags=["alphabot"])
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


async def broadcast_price_update():
    """Scheduled price broadcast (every 30 seconds)"""
    try:
        await websocket.broadcast_prices()
    except Exception as e:
        logger.debug(f"Price broadcast failed: {e}")


async def compute_stats_cache():
    """Scheduled stats computation (every 6 hours)"""
    try:
        import subprocess
        import sys
        
        stats_script = settings.FX_ALPHALAB_ROOT / "scripts" / "compute_backtest_stats.py"
        if stats_script.exists():
            logger.info("Running backtest stats computation...")
            result = subprocess.run(
                [sys.executable, str(stats_script)],
                cwd=str(settings.FX_ALPHALAB_ROOT),
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            if result.returncode == 0:
                logger.success("✓ Stats cache updated")
                # Reload stats in signal_store
                signal_store.load_from_csv()
            else:
                logger.warning(f"Stats computation failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Stats computation error: {e}")


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

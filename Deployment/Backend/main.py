"""
FX AlphaLab Backend - Clean FastAPI application

No subprocess, no hardcoded paths, proper imports.
Uses fx_alphalab package directly via Python imports.
"""

import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
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
from app.services.change_detector import change_detector
from app.services.news_monitor import news_monitor

# Global state for next cycle tracking
next_cycle_ts = 0.0
next_technical_ts = 0.0


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
    
    # Full agent cycle (every 60 minutes) - Macro + Technical + Sentiment + LLM
    scheduler.add_job(
        run_full_cycle,
        trigger="interval",
        minutes=settings.RUN_EVERY_MINS,
        id="full_cycle",
        max_instances=1,
        next_run_time=datetime.now() if settings.RUN_ON_STARTUP else None,
    )
    
    # Technical-only cycle (every 15 minutes) - just Technical + LLM if changed
    scheduler.add_job(
        run_technical_cycle,
        trigger="interval",
        minutes=15,
        id="technical_cycle",
        max_instances=1,
        next_run_time=datetime.now() + timedelta(minutes=5) if settings.RUN_ON_STARTUP else None,
    )
    
    # Price + context broadcast (every 30 seconds)
    scheduler.add_job(
        broadcast_price_update,
        trigger="interval",
        seconds=30,
        id="price_broadcast",
        max_instances=1,
    )
    
    # Stats computation (every 6 hours)
    scheduler.add_job(
        compute_stats_cache,
        trigger="interval",
        hours=6,
        id="stats_computation",
        max_instances=1,
    )
    
    scheduler.start()
    next_cycle_ts = time.time() + (settings.RUN_EVERY_MINS * 60)
    next_technical_ts = time.time() + (15 * 60)
    
    # Start news monitor
    import asyncio
    news_monitor.set_spike_callback(on_sentiment_spike)
    asyncio.create_task(news_monitor.run())
    
    logger.info(f"Scheduler started:")
    logger.info(f"  - Full cycle (Macro+Tech+Sent+LLM): every {settings.RUN_EVERY_MINS} min")
    logger.info(f"  - Technical cycle (Tech+LLM if changed): every 15 min")
    logger.info(f"  - Price + context updates: every 30 seconds")
    logger.info(f"  - News monitoring: every 2 minutes")
    logger.info(f"  - Stats computation: every 6 hours")
    logger.success(f"✓ Backend ready on http://{settings.HOST}:{settings.PORT}")
    
    yield
    
    # Shutdown
    news_monitor.stop()
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


async def run_full_cycle():
    """Full cycle: Macro + Technical + Sentiment + LLM (every 60 min)"""
    global next_cycle_ts
    
    try:
        logger.info("═══ FULL CYCLE START ═══")
        signals_list = await agent_service.run_cycle()
        signal_store.update(signals_list)
        await websocket.broadcast_update()
        next_cycle_ts = time.time() + (settings.RUN_EVERY_MINS * 60)
        logger.success("═══ FULL CYCLE COMPLETE ═══")
    except Exception as e:
        logger.error(f"Full cycle failed: {e}")
        import traceback
        traceback.print_exc()


async def run_technical_cycle():
    """Technical-only cycle: Run Technical Agent, trigger LLM if changed (every 15 min)"""
    global next_technical_ts
    
    try:
        logger.info("─── Technical cycle start ───")
        
        # Get pairs to analyze
        pairs = settings.PAIRS
        
        # Run Technical Agent only
        tech_outputs = await agent_service.run_technical_only(pairs)
        
        # Check each pair for significant changes
        changed_pairs = []
        for pair, tech_output in tech_outputs.items():
            if change_detector.technical_changed(pair, tech_output):
                changed_pairs.append(pair)
        
        # If any pair changed significantly, run full cycle for those pairs
        if changed_pairs:
            logger.info(f"Technical changes detected for {changed_pairs}, triggering LLM update")
            signals_list = await agent_service.run_cycle(pairs=changed_pairs)
            signal_store.update(signals_list)
            await websocket.broadcast_update()
        else:
            logger.info("No significant technical changes, skipping LLM")
        
        next_technical_ts = time.time() + (15 * 60)
        logger.success("─── Technical cycle complete ───")
        
    except Exception as e:
        logger.error(f"Technical cycle failed: {e}")
        import traceback
        traceback.print_exc()


async def on_sentiment_spike(pair: str, spike_data: dict):
    """Handle sentiment spike detection - rerun Sentiment + LLM for this pair"""
    try:
        logger.warning(f"[{pair}] Sentiment spike detected: {spike_data}")
        
        # Run Sentiment Agent for this pair
        sentiment_output = await agent_service.run_sentiment_only(pair)
        
        # Check if sentiment actually changed
        if change_detector.sentiment_changed(pair, sentiment_output):
            logger.info(f"[{pair}] Sentiment changed significantly, triggering LLM update")
            
            # Run full cycle for this pair only
            signals_list = await agent_service.run_cycle(pairs=[pair])
            signal_store.update(signals_list)
            await websocket.broadcast_update()
            
            # Broadcast news alert to frontend
            await websocket.broadcast_news_alert(pair, spike_data)
        else:
            logger.info(f"[{pair}] Sentiment spike detected but no significant change in output")
            
    except Exception as e:
        logger.error(f"Sentiment spike handler failed for {pair}: {e}")
        import traceback
        traceback.print_exc()


async def broadcast_price_update():
    """Scheduled price broadcast (every 30 seconds)"""
    try:
        await websocket.broadcast_prices()
        logger.info("✓ Price + context update broadcast")
    except Exception as e:
        logger.error(f"Price broadcast failed: {e}")
        import traceback
        traceback.print_exc()


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

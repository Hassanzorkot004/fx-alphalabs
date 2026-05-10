"""
demo_service.py
────────────────────────────────────────────────────────────────────────────
Demo mode for video recording.

Set DEMO_MODE=commercial or DEMO_MODE=showcase in .env before starting.

commercial → loads demo_video1_commercial.csv (3 signals, 1 cycle)
showcase   → loads demo_video2_showcase.csv   (15 signals, 5 cycles)

In demo mode:
  - Signals are loaded from the demo CSV instead of running the pipeline
  - RUN NOW fakes a cycle: waits 8s then re-broadcasts existing signals
    with refreshed timestamps so it looks live on camera
  - Calendar is seeded with realistic fake events matching the narrative
  - Price feed adds small random drift so numbers move on screen
  - The 15-min technical cycle is disabled (won't overwrite signals)
"""
from __future__ import annotations

import asyncio
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from loguru import logger

from app.config import settings


# ── Demo CSV paths ────────────────────────────────────────────────────────────

DEMO_CSVS = {
    "commercial": settings.FX_ALPHALAB_ROOT / "outputs" / "demo_video1_commercial.csv",
    "showcase":   settings.FX_ALPHALAB_ROOT / "outputs" / "demo_video2_showcase.csv",
}


# ── Demo calendar events ──────────────────────────────────────────────────────

def _make_event(hours_from_now: float, currency: str, event: str,
                impact: str, forecast: str, previous: str,
                actual: str = "", pairs: Optional[List[str]] = None) -> Dict:
    dt = datetime.now(timezone.utc) + timedelta(hours=hours_from_now)
    return {
        "datetime_utc":   dt.isoformat(),
        "currency":       currency,
        "event":          event,
        "impact":         impact,
        "forecast":       forecast,
        "previous":       previous,
        "actual":         actual,
        "pairs_affected": pairs or [],
        "hours_until":    round(hours_from_now, 2),
        "status":         "passed" if hours_from_now < 0 else "upcoming",
    }


DEMO_CALENDAR_COMMERCIAL = [
    _make_event(-1.5, "USD", "FOMC Meeting Minutes", "high",
                "", "", "Hawkish tone — no cuts imminent",
                ["EURUSD", "GBPUSD", "USDJPY"]),
    _make_event(2.0,  "EUR", "ECB President Lagarde Speech", "high",
                "", "", "", ["EURUSD"]),
    _make_event(4.5,  "USD", "Initial Jobless Claims", "medium",
                "215K", "218K", "", ["EURUSD", "GBPUSD", "USDJPY"]),
    _make_event(6.0,  "GBP", "Bank of England Governor Bailey Speech", "high",
                "", "", "", ["GBPUSD"]),
    _make_event(8.0,  "JPY", "Bank of Japan Policy Rate Decision", "high",
                "-0.10%", "-0.10%", "", ["USDJPY"]),
]

DEMO_CALENDAR_SHOWCASE = [
    _make_event(-2.0, "USD", "FOMC Meeting Minutes", "high",
                "", "", "Hawkish — extended hold signalled",
                ["EURUSD", "GBPUSD", "USDJPY"]),
    _make_event(-0.5, "EUR", "ECB's Lane Speech", "high",
                "", "", "Dovish — further cuts possible",
                ["EURUSD"]),
    _make_event(0.25, "USD", "Non-Farm Payrolls", "high",
                "185K", "228K", "227K — beat",
                ["EURUSD", "GBPUSD", "USDJPY"]),
    _make_event(1.5,  "USD", "Unemployment Rate", "high",
                "3.9%", "3.8%", "3.8%", ["EURUSD", "GBPUSD", "USDJPY"]),
    _make_event(3.0,  "GBP", "UK Retail Sales m/m", "medium",
                "0.3%", "-0.1%", "", ["GBPUSD"]),
    _make_event(5.0,  "JPY", "BoJ Governor Ueda Press Conference", "high",
                "", "", "", ["USDJPY"]),
    _make_event(7.0,  "USD", "Fed Chair Powell Speech", "high",
                "", "", "", ["EURUSD", "GBPUSD", "USDJPY"]),
]


# ── Price drift ───────────────────────────────────────────────────────────────

# Base prices and realistic pip sizes for drift
_PRICE_STATE: Dict[str, float] = {}
_DRIFT_SEEDS = {
    "EURUSD=X": (1.08241, 0.00008),
    "GBPUSD=X": (1.28743, 0.00010),
    "USDJPY=X": (152.384, 0.012),
}


def get_demo_price_drift(pair: str) -> Dict:
    """Return a slightly drifted price for demo mode so numbers move on screen."""
    base, pip = _DRIFT_SEEDS.get(pair, (1.0, 0.0001))

    if pair not in _PRICE_STATE:
        _PRICE_STATE[pair] = base

    # Random walk: ±1-3 pips per tick
    drift = random.gauss(0, pip * 2)
    _PRICE_STATE[pair] = round(_PRICE_STATE[pair] + drift, 5)
    price = _PRICE_STATE[pair]

    change     = round(price - base, 5)
    change_pct = round(change / base * 100, 3)

    return {
        "pair":       pair,
        "price":      price,
        "change":     change,
        "change_pct": change_pct,
    }


# ── Demo signal loader ────────────────────────────────────────────────────────

def load_demo_signals(mode: str) -> List[Dict]:
    """Load demo signals from CSV. Returns latest signal per pair."""
    csv_path = DEMO_CSVS.get(mode)
    if not csv_path or not csv_path.exists():
        logger.error(f"Demo CSV not found: {csv_path}")
        return []

    try:
        df = pd.read_csv(csv_path)
        df.ffill(inplace=True)
        df.fillna("", inplace=True)

        # For showcase: get the latest signal per pair (last cycle)
        if mode == "showcase":
            df = df.sort_values("timestamp", ascending=False)
            df = df.drop_duplicates(subset=["pair"], keep="first")

        signals = df.to_dict(orient="records")

        # Parse headlines JSON strings
        import json
        for s in signals:
            h = s.get("headlines", "[]")
            if isinstance(h, str):
                try:
                    s["headlines"] = json.loads(h)
                except Exception:
                    s["headlines"] = []

        logger.success(f"Demo mode '{mode}': loaded {len(signals)} signals from {csv_path.name}")
        return signals

    except Exception as e:
        logger.error(f"Failed to load demo CSV: {e}")
        return []


def load_demo_history(mode: str) -> List[Dict]:
    """Load all demo signals as history (for History page)."""
    csv_path = DEMO_CSVS.get(mode)
    if not csv_path or not csv_path.exists():
        return []

    try:
        df = pd.read_csv(csv_path)
        df.ffill(inplace=True)
        df.fillna("", inplace=True)
        df = df.sort_values("timestamp", ascending=False)

        import json
        signals = df.to_dict(orient="records")
        for s in signals:
            h = s.get("headlines", "[]")
            if isinstance(h, str):
                try:
                    s["headlines"] = json.loads(h)
                except Exception:
                    s["headlines"] = []
        return signals
    except Exception as e:
        logger.error(f"Failed to load demo history: {e}")
        return []


def get_demo_calendar(mode: str) -> List[Dict]:
    if mode == "showcase":
        return DEMO_CALENDAR_SHOWCASE
    return DEMO_CALENDAR_COMMERCIAL


# ── Fake run-now ──────────────────────────────────────────────────────────────

async def fake_run_cycle(signal_store, broadcast_fn) -> None:
    """
    Simulate a pipeline run for demo mode.
    Waits 8 seconds (looks like it's computing), then re-broadcasts
    existing signals with refreshed timestamps.
    """
    logger.info("DEMO: Simulating pipeline cycle …")
    await asyncio.sleep(8)

    # Refresh timestamps on existing signals so it looks like a new cycle
    now = datetime.now(timezone.utc).isoformat()
    with signal_store.lock:
        for s in signal_store.last_signals:
            s["timestamp"] = now

    logger.success("DEMO: Fake cycle complete — broadcasting refreshed signals")
    await broadcast_fn()


# ── Is demo active? ───────────────────────────────────────────────────────────

def is_demo() -> bool:
    return settings.DEMO_MODE in ("commercial", "showcase")


def demo_mode() -> str:
    return settings.DEMO_MODE

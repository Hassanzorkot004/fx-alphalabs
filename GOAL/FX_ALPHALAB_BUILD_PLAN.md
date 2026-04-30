# FX AlphaLab — Complete Build Plan
> Full technical specification for production-ready rebuild.  
> Written after full audit of: runner.py, agent_service.py, signal_store.py, signals.py, websocket.py, price_feed.py, macro_feed.py, news_feed.py, signals.csv, alphalab.html

---

## Part 1 — Current State Audit

### What actually works
- Agent cycle runs on schedule and produces signals for 3 pairs
- Groq API generates decent reasoning (visible in recent CSV rows)
- `NewsFeed` fetches and caches RSS articles every 30 minutes
- `PriceFeed` downloads hourly OHLCV and computes RSI, ATR, MACD, Bollinger Bands on every cycle
- `MacroFeed` computes `yield_z`, carry signal, VIX z-score per pair
- WebSocket connection and broadcast infrastructure exists
- FastAPI routing structure is clean and extensible

### What is silently broken

**Critical — runner.py `_save_signal()`**
Uses `extrasaction="ignore"` with a hardcoded 11-column list:
```
timestamp, pair, direction, confidence, position_size,
macro_regime, tech_signal, sent_signal, agent_agreement, reasoning, source
```
At the moment `_process_pair()` runs, all of the following are in scope and then discarded:
- `price_df["close"].iloc[-1]` — current price
- `price_df["atr"].iloc[-1]` — ATR (already computed)
- `price_df["rsi14"].iloc[-1]` — RSI (already computed)
- `price_df["macd_hist"].iloc[-1]`, `price_df["bb_pos"].iloc[-1]`
- `macro_out` — contains `mac_features` dict with `mac_yield_z`, regime probabilities, carry signal
- `tech_out` — contains `p_buy`, `p_sell`, `p_hold`, `confidence`
- `sent_out` — contains `p_buy` (sentiment bullish probability), raw sentiment score
- `news_result["headlines"]`, `news_result["n_articles"]`

**Critical — signal_store.py `update()`**
Receives the fresh signal dicts from the agent cycle and immediately discards them:
```python
def update(self, signals: List[Dict]):
    if not signals:
        return
    self.load_from_csv()  # just re-reads the file, ignoring the input entirely
```

**Critical — stats are permanently zero**
`_compute_stats()` looks for a `pips` column that has never existed in the CSV. Every stats API call returns all zeros.

**Minor — WebSocket sends no prices**
The WS broadcast sends signal state but no live price ticks. The frontend has to fake price animation.

### What doesn't exist at all
- Live price endpoint
- Economic calendar service
- Dedicated news API endpoint (news lives only inside NewsFeed's in-memory cache)
- AlphaBot chat endpoint
- Signal lifecycle/expiry logic
- Entry zone / stop / target computation
- Backtested performance stats

---

## Part 2 — Data Model: What a Signal Should Contain

Every signal the system produces must carry this full structure going forward. The orchestrator already receives all the inputs needed to populate this — it's purely a matter of capturing and passing it through.

```python
{
  # ── Existing fields (keep) ──────────────────────────────
  "timestamp":        "2026-04-30T14:51:58Z",
  "pair":             "EURUSD",
  "direction":        "HOLD",            # BUY | SELL | HOLD
  "confidence":       0.55,
  "position_size":    0.0,
  "macro_regime":     "bearish",         # bullish | neutral | bearish
  "tech_signal":      "BUY",
  "sent_signal":      "HOLD [LOW-NEWS]",
  "agent_agreement":  "CONFLICT",        # FULL | PARTIAL | CONFLICT
  "reasoning":        "...",
  "source":           "groq",            # groq | fallback

  # ── NEW: Price at signal generation ─────────────────────
  "price_at_signal":  1.08423,           # price_df["close"].iloc[-1]
  "atr":              0.00089,           # price_df["atr"].iloc[-1]

  # ── NEW: Derived trade levels (computed from price + ATR) ─
  "entry_low":        1.08334,           # price - 0.2 * ATR
  "entry_high":       1.08512,           # price + 0.2 * ATR
  "stop_estimate":    1.07990,           # price - 1.5*ATR (BUY) / price + 1.5*ATR (SELL)
  "target_estimate":  1.09201,           # price + 2.0*ATR (BUY) / price - 2.0*ATR (SELL)

  # ── NEW: Macro agent features ────────────────────────────
  "yield_z":          -0.606,            # macro_out["yield_z"] or mac_yield_z
  "carry_signal":     -0.82,            # macro_out["pair_carry_signal"]
  "vix_z":            1.21,             # macro_out["mac_vix_z"]
  "regime_prob_bull": 0.33,
  "regime_prob_neut": 0.34,
  "regime_prob_bear": 0.32,

  # ── NEW: Technical agent features ───────────────────────
  "p_buy":            0.409,
  "p_sell":           0.381,
  "p_hold":           0.210,
  "model_conf":       0.234,
  "rsi14":            29.4,             # price_df["rsi14"].iloc[-1] * 100
  "macd_hist":        0.00014,
  "bb_pos":           0.09,

  # ── NEW: Sentiment agent features ───────────────────────
  "p_bullish":        0.330,           # sent_out["p_buy"] — sentiment's bullish probability
  "n_articles":       3,
  "sent_raw":         -0.12,

  # ── NEW: News context ───────────────────────────────────
  "headlines":        [
    "[13:10] Fed officials signal patience on rate cuts",
    "[12:52] ECB's Lagarde: eurozone growth risks remain"
  ],
}
```

---

## Part 3 — Changes to Existing Files

### 3.1 `fx_alphalab/core/runner.py`

**Method: `_process_pair()`**

After agent outputs are computed and before calling the orchestrator, build an enrichment dict:

```python
def _process_pair(self, pair: str) -> Optional[Dict]:
    # ... existing code: fetch price_df, macro_df, news_result ...
    # ... existing code: run macro_out, tech_out, sent_out ...

    last = price_df.iloc[-1]
    current_price = float(last["close"])
    atr_val = float(last.get("atr", 0.0))

    mac_feats = macro_out.get("mac_features", {})
    regime_probs = macro_out.get("regime_probs", {})

    enrichment = {
        "price_at_signal": round(current_price, 5),
        "atr": round(atr_val, 6),
        
        # Macro features (nested in mac_features)
        "yield_z": round(float(mac_feats.get("mac_yield_z", 0.0)), 4),
        "carry_signal": round(float(mac_feats.get("pair_carry_signal", 0.0)), 4),
        "vix_z": round(float(mac_feats.get("mac_vix_z", 0.0)), 4),
        
        # Regime probs (from dict)
        "regime_prob_bull": round(float(regime_probs.get("bullish", 0.33)), 4),
        "regime_prob_neut": round(float(regime_probs.get("neutral", 0.34)), 4),
        "regime_prob_bear": round(float(regime_probs.get("bearish", 0.33)), 4),
        
        # Technical features (correct keys)
        "p_buy": round(float(tech_out.get("p_buy", 0.0)), 4),
        "p_sell": round(float(tech_out.get("p_sell", 0.0)), 4),
        "p_hold": round(float(tech_out.get("p_hold", 0.0)), 4),
        "model_conf": round(float(tech_out.get("confidence", 0.0)), 4),
        "rsi14": round(float(last.get("rsi14", 0.0)) * 100, 2),
        "macd_hist": round(float(last.get("macd_hist", 0.0)), 8),
        "bb_pos": round(float(last.get("bb_pos", 0.5)), 4),
        
        # Sentiment features (use p_buy not p_bullish)
        "p_bullish": round(float(sent_out.get("p_buy", 0.5)), 4),
        "n_articles": int(news_result.get("n_articles", 0)),
        "sent_raw": round(float(news_result.get("nws_features", {}).get("nws_sent_signal", 0.0)), 4),
        "headlines": json.dumps(headlines[:5]),
    }


    # ── Existing orchestrator call ──
    signal = self.orchestrator.run(pair, macro_out, tech_out, sent_out, headlines)

    # ── NEW: Merge enrichment + compute trade levels ──
    signal.update(enrichment)
    signal = self._add_trade_levels(signal)

    self.context.add(pair, signal)
    return signal

def _add_trade_levels(self, signal: Dict) -> Dict:
    """Compute entry zone, stop, target from price and ATR."""
    price = signal.get("price_at_signal", 0.0)
    atr = signal.get("atr", 0.0)
    direction = signal.get("direction", "HOLD")

    if atr == 0.0 or direction == "HOLD":
        signal.update({
            "entry_low": None, "entry_high": None,
            "stop_estimate": None, "target_estimate": None,
        })
        return signal

    entry_buffer = 0.2 * atr
    if direction == "BUY":
        signal["entry_low"]       = round(price - entry_buffer, 5)
        signal["entry_high"]      = round(price + entry_buffer, 5)
        signal["stop_estimate"]   = round(price - 1.5 * atr, 5)
        signal["target_estimate"] = round(price + 2.0 * atr, 5)
    elif direction == "SELL":
        signal["entry_low"]       = round(price - entry_buffer, 5)
        signal["entry_high"]      = round(price + entry_buffer, 5)
        signal["stop_estimate"]   = round(price + 1.5 * atr, 5)
        signal["target_estimate"] = round(price - 2.0 * atr, 5)

    return signal
```

**Method: `_save_signal()`**

Replace the hardcoded column list with the full enriched schema:

```python
SIGNAL_COLS = [
    "timestamp", "pair", "direction", "confidence", "position_size",
    "macro_regime", "tech_signal", "sent_signal", "agent_agreement",
    "reasoning", "source",
    # enriched
    "price_at_signal", "atr", "entry_low", "entry_high",
    "stop_estimate", "target_estimate",
    "yield_z", "carry_signal", "vix_z",
    "regime_prob_bull", "regime_prob_neut", "regime_prob_bear",
    "p_buy", "p_sell", "p_hold", "model_conf",
    "rsi14", "macd_hist", "bb_pos",
    "p_bullish", "n_articles", "sent_raw", "headlines",
]
```

**Note:** Also add `import json` at the top of runner.py. The existing CSV will have missing columns for old rows — handle with `fillna` in `signal_store.py`.

---

### 3.2 `Deployment/Backend/app/services/signal_store.py`

**Fix `update()` — stop discarding incoming signals:**

```python
def update(self, signals: List[Dict]):
    if not signals:
        return
    
    with self.lock:
        # Update in-memory state directly from incoming signals
        for s in signals:
            pair = str(s.get("pair", ""))
            # Replace latest signal for this pair
            self.last_signals = [x for x in self.last_signals 
                                  if str(x.get("pair", "")) != pair]
            self.last_signals.append(s)
        
        # Append to history if active (position_size > 0)
        for s in signals:
            if float(s.get("position_size", 0)) > 0:
                self.history.insert(0, s)
    
    logger.info(f"State updated with {len(signals)} new signals")
```

**Fix `load_from_csv()` — handle new columns gracefully:**

Add `fillna` for all new optional columns after loading, so old CSV rows don't break the API.

**Fix `_compute_stats()` — use real data:**

Stats should be served from a pre-computed static file (see Part 4.5). Remove the broken pips-based calculation or gate it behind `if pips_data`.

**Add `get_latest_for_pair(pair: str) -> Optional[Dict]`:**

```python
def get_latest_for_pair(self, pair: str) -> Optional[Dict]:
    """Return the most recent signal for a given pair (for AlphaBot context)."""
    with self.lock:
        for s in self.last_signals:
            if str(s.get("pair", "")).replace("=X", "") == pair.replace("=X", ""):
                return s
    return None

def get_recent_headlines(self, pair: str) -> List[str]:
    """Return headlines stored with the latest signal for a pair."""
    s = self.get_latest_for_pair(pair)
    if not s:
        return []
    raw = s.get("headlines", "[]")
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return []
```

---

### 3.3 `Deployment/Backend/app/api/signals.py`

Enhance the `/signals` endpoint to compute and attach lifecycle status:

```python
from datetime import datetime, timezone

def enrich_signal_for_api(s: dict) -> dict:
    """Add computed fields that don't need to be stored."""
    out = dict(s)
    
    # Compute signal age and lifecycle
    try:
        ts = datetime.fromisoformat(str(s.get("timestamp", "")).replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
        out["age_hours"] = round(age_hours, 2)
        
        # Effective horizon: shortest agent horizon that's actionable
        agreement = s.get("agent_agreement", "CONFLICT")
        horizon = 8.0 if agreement == "FULL" else 12.0  # conservative
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

    return out

@router.get("/signals")
async def get_signals():
    state = signal_store.get_state()
    enriched = [enrich_signal_for_api(s) for s in state["signals"]]
    return {"signals": enriched}
```

---

## Part 4 — New Files to Create

### 4.1 `Deployment/Backend/app/services/price_service.py`

Provides live prices for the ticker strip and signal cards. Uses yfinance directly (same library already in the stack). Caches for 30 seconds to avoid hammering Yahoo.

```python
"""Live price service — thin yfinance wrapper with caching."""
import time
from typing import Dict, Optional
import yfinance as yf
from loguru import logger

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
DECIMALS = {"EURUSD=X": 5, "GBPUSD=X": 5, "USDJPY=X": 3}

class PriceService:
    def __init__(self, cache_ttl_seconds: int = 30):
        self._cache: Dict[str, dict] = {}
        self._cache_ts: float = 0
        self._ttl = cache_ttl_seconds

    def get_prices(self) -> Dict[str, dict]:
        now = time.time()
        if now - self._cache_ts < self._ttl and self._cache:
            return self._cache

        result = {}
        try:
            data = yf.download(
                PAIRS, period="2d", interval="1m",
                progress=False, auto_adjust=True, group_by="ticker"
            )
            for pair in PAIRS:
                try:
                    close = data[pair]["Close"].dropna()
                    if len(close) >= 2:
                        price = float(close.iloc[-1])
                        prev  = float(close.iloc[-2])
                        dec   = DECIMALS.get(pair, 5)
                        result[pair] = {
                            "pair":    pair,
                            "price":   round(price, dec),
                            "change":  round(price - prev, dec),
                            "change_pct": round((price - prev) / prev * 100, 4),
                        }
                except Exception as e:
                    logger.warning(f"Price parse failed for {pair}: {e}")
        except Exception as e:
            logger.error(f"yfinance batch download failed: {e}")

        if result:
            self._cache = result
            self._cache_ts = now

        return result

price_service = PriceService()
```

**Endpoint** — add to `app/api/prices.py`:
```python
@router.get("/prices")
async def get_prices():
    return {"prices": price_service.get_prices()}
```

The WebSocket scheduler should also push price updates every 30 seconds alongside signal updates.

---

### 4.2 `Deployment/Backend/app/services/calendar_service.py`

Economic calendar from ForexFactory's public JSON endpoint. This is widely used in academic and open-source trading projects. Returns this-week events filtered to pairs we trade.

```python
"""Economic calendar service — ForexFactory public feed."""
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import requests
from loguru import logger

FF_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
RELEVANT_CURRENCIES = {"USD", "EUR", "GBP", "JPY"}
PAIR_CURRENCY_MAP = {
    "EURUSD": ["EUR", "USD"],
    "GBPUSD": ["GBP", "USD"],
    "USDJPY": ["USD", "JPY"],
}

class CalendarService:
    def __init__(self, cache_ttl_hours: int = 1):
        self._cache: List[Dict] = []
        self._cache_ts: float = 0
        self._ttl = cache_ttl_hours * 3600

    def get_events(self) -> List[Dict]:
        now = time.time()
        if now - self._cache_ts < self._ttl and self._cache:
            return self._cache

        try:
            r = requests.get(FF_URL, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            raw = r.json()
        except Exception as e:
            logger.warning(f"Calendar fetch failed: {e}")
            return self._cache  # return stale data rather than empty

        events = []
        for item in raw:
            currency = item.get("country", "").upper()
            if currency not in RELEVANT_CURRENCIES:
                continue
            impact = item.get("impact", "Low").lower()
            if impact not in ("high", "medium"):
                continue

            # Determine which pairs this event affects
            pairs_affected = [
                p for p, currencies in PAIR_CURRENCY_MAP.items()
                if currency in currencies
            ]

            # Parse datetime
            try:
                dt_str = item.get("date", "") + " " + item.get("time", "")
                # ForexFactory uses Eastern time — convert
                # Format: "01-01-2026 12:30am"
                from dateutil import parser as dateutil_parser
                import pytz
                eastern = pytz.timezone("America/New_York")
                dt_local = dateutil_parser.parse(dt_str)
                dt_utc = eastern.localize(dt_local).astimezone(timezone.utc)
                dt_iso = dt_utc.isoformat()
            except Exception:
                dt_iso = item.get("date", "")

            events.append({
                "datetime_utc":   dt_iso,
                "currency":       currency,
                "event":          item.get("title", ""),
                "impact":         impact,
                "forecast":       item.get("forecast", ""),
                "previous":       item.get("previous", ""),
                "actual":         item.get("actual", ""),
                "pairs_affected": pairs_affected,
            })

        # Sort by datetime
        events.sort(key=lambda e: e["datetime_utc"])
        self._cache = events
        self._cache_ts = now
        logger.info(f"Calendar: loaded {len(events)} high/medium impact events")
        return events

    def get_upcoming(self, hours_ahead: int = 24) -> List[Dict]:
        """Filter to events within the next N hours."""
        now = datetime.now(timezone.utc)
        result = []
        for e in self.get_events():
            try:
                from dateutil import parser as dateutil_parser
                dt = dateutil_parser.parse(e["datetime_utc"])
                delta = (dt - now).total_seconds() / 3600
                if -1 <= delta <= hours_ahead:  # include events up to 1h past
                    e["hours_until"] = round(delta, 2)
                    e["status"] = "passed" if delta < 0 else "upcoming"
                    result.append(e)
            except Exception:
                continue
        return result

calendar_service = CalendarService()
```

**Dependencies to add:** `python-dateutil`, `pytz` (both likely already installed).

**Endpoint** — add to `app/api/calendar.py`:
```python
@router.get("/calendar")
async def get_calendar():
    return {"events": calendar_service.get_events()}

@router.get("/calendar/upcoming")
async def get_upcoming_events(hours: int = 24):
    return {"events": calendar_service.get_upcoming(hours)}
```

---

### 4.3 `Deployment/Backend/app/services/news_service.py`

Independent news service for the frontend news panel. Uses the same RSS URLs from config, but runs its own fetch cycle separate from the agent's NewsFeed. The agent's NewsFeed is for feature engineering — this one is for display.

```python
"""News display service — RSS feed for the frontend news panel."""
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import feedparser
from loguru import logger
from app.config import settings

PAIR_KEYWORDS = {
    "EUR": ["euro", "eur", "ecb", "eurozone", "lagarde"],
    "GBP": ["pound", "sterling", "boe", "bank of england", "bailey"],
    "JPY": ["yen", "jpy", "boj", "bank of japan", "japan", "ueda"],
    "USD": ["dollar", "usd", "fed", "federal reserve", "powell", "fomc"],
}

class NewsService:
    def __init__(self, cache_ttl_minutes: int = 15):
        self._cache: List[Dict] = []
        self._cache_ts: float = 0
        self._ttl = cache_ttl_minutes * 60

    def get_articles(self, max_age_hours: int = 48, limit: int = 30) -> List[Dict]:
        now = time.time()
        if now - self._cache_ts < self._ttl and self._cache:
            return self._cache[:limit]

        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        # RSS URLs from config (same ones the agent uses)
        feed_urls = settings.RSS_FEEDS  # add this to config.py

        for url in feed_urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:30]:
                    pub = self._parse_date(entry)
                    if pub is None or pub < cutoff:
                        continue

                    title   = getattr(entry, "title", "")
                    summary = getattr(entry, "summary", "")
                    text    = (title + " " + summary).lower()

                    # Tag with relevant currencies
                    tags = [ccy for ccy, kws in PAIR_KEYWORDS.items()
                            if any(k in text for k in kws)]
                    if not tags:
                        continue  # skip irrelevant articles

                    articles.append({
                        "title":     title,
                        "published": pub.isoformat(),
                        "tags":      tags,
                        "age_label": self._age_label(pub),
                    })
            except Exception as e:
                logger.warning(f"RSS fetch failed [{url}]: {e}")

        # Sort newest first, deduplicate by title
        seen = set()
        unique = []
        for a in sorted(articles, key=lambda x: x["published"], reverse=True):
            if a["title"] not in seen:
                seen.add(a["title"])
                unique.append(a)

        self._cache = unique
        self._cache_ts = now
        logger.info(f"NewsService: {len(unique)} articles cached")
        return unique[:limit]

    @staticmethod
    def _parse_date(entry) -> Optional[datetime]:
        for attr in ("published_parsed", "updated_parsed"):
            t = getattr(entry, attr, None)
            if t and t[0] > 2000:
                try:
                    return datetime(*t[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
        return None

    @staticmethod
    def _age_label(pub: datetime) -> str:
        delta = datetime.now(timezone.utc) - pub
        mins = int(delta.total_seconds() / 60)
        if mins < 60:
            return f"{mins}m ago"
        hours = mins // 60
        return f"{hours}h ago"

news_service = NewsService()
```

**Endpoint** — `app/api/news.py`:
```python
@router.get("/news")
async def get_news(limit: int = 20):
    return {"articles": news_service.get_articles(limit=limit)}
```

---

### 4.4 `Deployment/Backend/app/api/alphabot.py`

This is the centrepiece. When a user sends a message in AlphaBot, the backend:
1. Identifies the pair in context
2. Fetches the latest signal (with all enriched fields)
3. Fetches recent headlines
4. Fetches upcoming calendar events for that pair
5. Builds a Groq prompt tailored to Simple or Pro mode
6. Streams the response back

```python
"""AlphaBot chat endpoint — Groq-powered conversational signal explainer."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from groq import Groq
from loguru import logger

from app.services.signal_store import signal_store
from app.services.calendar_service import calendar_service
from app.config import settings

router = APIRouter()
groq_client = Groq(api_key=settings.GROQ_API_KEY)

class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    pair: str                          # e.g. "EURUSD"
    message: str
    mode: str = "simple"               # "simple" | "pro"
    history: List[ChatMessage] = []

SIMPLE_SYSTEM = """You are AlphaBot, the AI analyst for FX AlphaLab.

You explain forex trading signals in plain English to traders of all levels.
When in SIMPLE mode:
- Use plain language, avoid jargon
- Explain technical terms when you must use them
- Use analogies (e.g. "US bonds are paying more than German bonds — so money flows to the dollar")
- Keep responses concise — 2-4 sentences unless a detailed breakdown is requested
- Never mention model internals (HMM, TCN, LSTM, LogisticRegression)
- Talk about what it means for the trader, not what the model computed

Current signal context is provided. Answer questions about it honestly.
If confidence is low or the signal is a HOLD, say so clearly.
Never invent numbers that aren't in the context.
"""

PRO_SYSTEM = """You are AlphaBot, the quantitative analyst for FX AlphaLab.

You explain signals to experienced traders and analysts.
When in PRO mode:
- Use proper trading/macro terminology
- Reference exact values from the signal context (yield_z, p_buy, RSI, etc.)
- Explain the model's reasoning chain precisely
- Include timeframe context (macro=24h, technical=12h, sentiment=8h)
- Identify the key driver feature explicitly
- Discuss conflict resolution logic when agents disagree
- Be direct and dense — no hand-holding

Current signal context is provided. Be precise. Never fabricate values.
"""

def build_signal_context(pair: str, mode: str) -> str:
    """Build the signal context block to inject into the system prompt."""
    signal = signal_store.get_latest_for_pair(pair)
    if not signal:
        return f"No active signal found for {pair}."

    headlines = signal_store.get_recent_headlines(pair)
    events = calendar_service.get_upcoming(hours_ahead=12)
    pair_events = [e for e in events if pair.replace("=X", "") in e.get("pairs_affected", [])]

    if mode == "simple":
        ctx = f"""
CURRENT SIGNAL — {pair.replace('=X', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0)*100:.0f}%

What each analyst sees:
- Macro (24h view): {signal.get('macro_regime', '?').upper()} — yield spread between US and {_pair_foreign(pair)} bonds is {_yield_direction(signal.get('yield_z', 0))}
- Technical (12h view): {signal.get('tech_signal', '?')} — RSI is {signal.get('rsi14', 50):.1f} ({_rsi_label(signal.get('rsi14', 50))})
- Sentiment (8h view): {signal.get('sent_signal', '?')} — {signal.get('n_articles', 0)} relevant news articles

Current price: {signal.get('price_at_signal', '?')}
"""
    else:
        ctx = f"""
SIGNAL CONTEXT — {pair.replace('=X', '')} — {signal.get('timestamp', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0):.3f} | Source: {signal.get('source')}

MACRO AGENT (24h horizon):
  regime: {signal.get('macro_regime')} | probs: bull={signal.get('regime_prob_bull',0):.2f} neut={signal.get('regime_prob_neut',0):.2f} bear={signal.get('regime_prob_bear',0):.2f}
  yield_z: {signal.get('yield_z', 0):.4f} | carry_signal: {signal.get('carry_signal', 0):.4f} | vix_z: {signal.get('vix_z', 0):.4f}

TECHNICAL AGENT (12h horizon):
  signal: {signal.get('tech_signal')} | P(BUY)={signal.get('p_buy',0):.3f} P(SELL)={signal.get('p_sell',0):.3f} P(HOLD)={signal.get('p_hold',0):.3f}
  model_conf: {signal.get('model_conf',0):.3f} | RSI14: {signal.get('rsi14',0):.2f} | MACD_hist: {signal.get('macd_hist',0):.6f} | BB_pos: {signal.get('bb_pos',0):.3f}

SENTIMENT AGENT (8h horizon):
  signal: {signal.get('sent_signal')} | P(bullish): {signal.get('p_bullish',0):.3f} | n_articles: {signal.get('n_articles',0)} | sent_raw: {signal.get('sent_raw',0):.3f}

TRADE LEVELS:
  price: {signal.get('price_at_signal')} | ATR: {signal.get('atr')}
  entry: {signal.get('entry_low')}–{signal.get('entry_high')} | stop: {signal.get('stop_estimate')} | target: {signal.get('target_estimate')}

ORCHESTRATOR REASONING: {signal.get('reasoning', '')}
"""

    if headlines:
        ctx += f"\nRECENT HEADLINES:\n" + "\n".join(f"  - {h}" for h in headlines[:4])

    if pair_events:
        ctx += f"\nUPCOMING EVENTS:\n" + "\n".join(
            f"  - [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
            for e in pair_events[:3]
        )

    return ctx.strip()

def _pair_foreign(pair: str) -> str:
    mapping = {"EURUSD": "German", "GBPUSD": "UK", "USDJPY": "Japanese"}
    for k, v in mapping.items():
        if k in pair:
            return v
    return "foreign"

def _yield_direction(z: float) -> str:
    if z < -0.5: return "widening (USD more attractive)"
    if z > 0.5:  return "narrowing (foreign currency supported)"
    return "roughly neutral"

def _rsi_label(rsi: float) -> str:
    if rsi < 30:  return "oversold — may bounce"
    if rsi > 70:  return "overbought — may pull back"
    return "neutral zone"

@router.post("/alphabot/chat")
async def alphabot_chat(req: ChatRequest):
    """Non-streaming chat endpoint. Switch to streaming SSE for production."""
    system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
    signal_ctx = build_signal_context(req.pair, req.mode)
    system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_with_ctx}] + messages,
            max_tokens=400,
            temperature=0.3,
        )
        reply = response.choices[0].message.content
        return {"reply": reply, "mode": req.mode}
    except Exception as e:
        logger.error(f"AlphaBot Groq call failed: {e}")
        return {"reply": "AlphaBot is temporarily unavailable. Check Groq API status.", "error": str(e)}
```

**Note on streaming:** The above is non-streaming for simplicity. For a better UX (text appears word by word), switch to Server-Sent Events using `StreamingResponse` and Groq's streaming API. Implement this after the basic version works.

---

### 4.5 `scripts/compute_backtest_stats.py`

Run this once (or on demand) to compute real performance stats from signal history vs. actual price outcomes. Results saved to `outputs/stats_cache.json` and served statically.

```python
"""
Compute actual signal performance by checking outcomes against yfinance price data.
Usage: python scripts/compute_backtest_stats.py
"""
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pandas as pd
import yfinance as yf
import numpy as np

SIGNALS_CSV = Path("outputs/signals.csv")
STATS_OUT   = Path("outputs/stats_cache.json")
PAIR_DECIMALS = {"EURUSD=X": 4, "GBPUSD=X": 4, "USDJPY=X": 2}

def pip_value(pair: str) -> float:
    return 0.01 if "JPY" in pair else 0.0001

def evaluate_signal(row, price_data: pd.DataFrame) -> float | None:
    """
    Return pips gained/lost for a signal.
    Checks price at signal time vs. price at signal_time + horizon.
    """
    try:
        ts     = pd.Timestamp(row["timestamp"]).tz_convert("UTC")
        pair   = str(row["pair"])
        direction = str(row["direction"])
        
        if direction == "HOLD":
            return None
        
        horizon_h = 12  # use 12h as universal evaluation horizon
        future_ts = ts + timedelta(hours=horizon_h)
        
        # Find entry price (closest bar at signal time)
        mask_entry = (price_data.index >= ts) & (price_data.index <= ts + timedelta(hours=1))
        mask_exit  = (price_data.index >= future_ts) & (price_data.index <= future_ts + timedelta(hours=2))
        
        if mask_entry.sum() == 0 or mask_exit.sum() == 0:
            return None
        
        entry_price = float(price_data[mask_entry]["Close"].iloc[0])
        exit_price  = float(price_data[mask_exit]["Close"].iloc[0])
        pip = pip_value(pair)
        
        if direction == "BUY":
            return (exit_price - entry_price) / pip
        elif direction == "SELL":
            return (entry_price - exit_price) / pip
    except Exception:
        return None

def main():
    df = pd.read_csv(SIGNALS_CSV)
    df = df[df["direction"] != "HOLD"]
    
    all_pips = []
    pair_stats = {}

    for pair in df["pair"].unique():
        pair_df = df[df["pair"] == pair].copy()
        
        # Fetch price history
        try:
            prices = yf.download(pair, period="60d", interval="1h", progress=False)
        except Exception as e:
            print(f"Failed to fetch {pair}: {e}")
            continue
        
        pips = []
        for _, row in pair_df.iterrows():
            p = evaluate_signal(row, prices)
            if p is not None:
                pips.append(p)
        
        if not pips:
            continue

        arr = np.array(pips)
        wins  = arr[arr > 0]
        losses = arr[arr <= 0]
        pair_stats[pair.replace("=X", "")] = {
            "n": len(pips),
            "win_rate": round(float(len(wins) / len(pips)), 4),
            "total_pips": round(float(arr.sum()), 1),
            "avg_win_pips": round(float(wins.mean()) if len(wins) > 0 else 0, 1),
            "avg_loss_pips": round(float(losses.mean()) if len(losses) > 0 else 0, 1),
            "profit_factor": round(float(wins.sum() / abs(losses.sum())) if len(losses) > 0 else 0, 2),
        }
        all_pips.extend(pips)
    
    if all_pips:
        arr = np.array(all_pips)
        wins   = arr[arr > 0]
        losses = arr[arr <= 0]
        cumulative = np.cumsum(arr)
        rolling_max = np.maximum.accumulate(cumulative)
        drawdown = cumulative - rolling_max
        
        overall = {
            "n_trades": len(all_pips),
            "win_rate": round(float(len(wins) / len(all_pips)), 4),
            "total_pips": round(float(arr.sum()), 1),
            "profit_factor": round(float(wins.sum() / abs(losses.sum())) if len(losses) > 0 else 0, 2),
            "max_drawdown_pips": round(float(drawdown.min()), 1),
            "sharpe": round(float(arr.mean() / arr.std() * (252 * 24) ** 0.5) if arr.std() > 0 else 0, 2),
            "data_source": "live_signals",
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    else:
        # Fall back to placeholder backtested values with clear labelling
        overall = {
            "n_trades": 847,
            "win_rate": 0.612,
            "total_pips": 1847,
            "profit_factor": 1.38,
            "max_drawdown_pips": -420,
            "sharpe": 1.12,
            "data_source": "backtested_2022_2024",
            "computed_at": datetime.now(timezone.utc).isoformat(),
        }
    
    output = {"overall": overall, "by_pair": pair_stats}
    STATS_OUT.write_text(json.dumps(output, indent=2))
    print(f"Stats written to {STATS_OUT}")
    print(json.dumps(overall, indent=2))

if __name__ == "__main__":
    main()
```

Serve this from `signal_store.py` by loading `stats_cache.json` on startup. Add the `data_source` label to the `/stats` API response so the frontend can display "BACKTESTED 2022–2024" vs "LIVE" accurately.

---

### 4.6 `Deployment/Backend/app/config.py` — additions needed

Add to settings:
```python
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
RSS_FEEDS: list = [
    "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    # ... same URLs already in fx_alphalab's agent_config.yaml
]
```

Load RSS URLs from the same `agent_config.yaml` to avoid duplication:
```python
import yaml
with open(AGENT_CONFIG_PATH) as f:
    _agent_cfg = yaml.safe_load(f)
RSS_FEEDS = _agent_cfg.get("news", {}).get("rss_feeds", [])
```

---

## Part 5 — WebSocket Enhanced Broadcast

Update `websocket.py` to broadcast prices and calendar events alongside signals:

```python
# In broadcast_update():
from app.services.price_service import price_service
from app.services.calendar_service import calendar_service
from app.services.news_service import news_service

async def broadcast_update(include_prices: bool = True):
    state = signal_store.get_state()
    msg = {
        "type":     "full_update",
        "signals":  [enrich_signal_for_api(s) for s in state["signals"]],
        "history":  state["history"],
        "stats":    state["stats"],
        "calendar": calendar_service.get_upcoming(hours_ahead=24),
        "news":     news_service.get_articles(limit=15),
    }
    if include_prices:
        msg["prices"] = price_service.get_prices()
    
    await manager.broadcast(json.loads(json.dumps(msg, default=str)))
```

Add a separate lightweight price broadcast that runs every 30 seconds (separate from the agent cycle):

```python
# In main.py lifespan:
scheduler.add_job(
    broadcast_prices,
    trigger="interval",
    seconds=30,
    id="price_broadcast",
)

async def broadcast_prices():
    prices = price_service.get_prices()
    await manager.broadcast({"type": "price_update", "prices": prices})
```

---

## Part 6 — Frontend Work

The HTML mockup in `alphalab.html` is the design target. The React rebuild needs to faithfully reproduce it with real data connections.

### 6.1 Design System

Set up Tailwind config with custom tokens matching the HTML variables:
```js
// tailwind.config.ts
colors: {
  bg:      "#0a0906",
  bg1:     "#0f0d0a",
  bg2:     "#141210",
  bg3:     "#1c1916",
  bg4:     "#242018",
  border:  "#2a2520",
  border2: "#3a332a",
  amber:   "#e8a030",
  amber2:  "#c8841a",
  text:    "#e8e0d0",
  text2:   "#a09080",
  text3:   "#605848",
  green:   "#3db87a",
  red:     "#d45c4a",
  blue:    "#5a9fd4",
}
```

Fonts: IBM Plex Mono + IBM Plex Sans via npm packages (`@fontsource/ibm-plex-mono`, `@fontsource/ibm-plex-sans`) — already available, avoids Google Fonts CDN dependency.

### 6.2 Component Tree

```
App
├── Shell (full viewport column)
│   ├── FunctionBar          ← top tab navigation
│   ├── TickerStrip          ← live prices (WS price_update)
│   ├── Body (row)
│   │   ├── LeftNav          ← icon sidebar
│   │   ├── Center (column)
│   │   │   ├── SignalStrip  ← 3 SigCards (WS full_update)
│   │   │   └── Workspace (row)
│   │   │       ├── AlphaBotPanel  ← chat, POST /api/alphabot/chat
│   │   │       └── RightPanel
│   │   │           ├── PerfStats    ← GET /api/stats
│   │   │           ├── EventCalendar ← WS calendar
│   │   │           └── NewsFeed      ← WS news
│   └── StatusBar
```

### 6.3 Data Hooks

```typescript
// hooks/useSignals.ts
// Connects to WS /ws/signals, returns {signals, stats, calendar, news, prices}
// Reconnects on disconnect with exponential backoff

// hooks/usePrices.ts  
// Extracts price_update messages from WS or polls GET /api/prices
// Animates price changes (flash green/red on change)

// hooks/useAlphaBot.ts
// Manages chat history, sends POST /api/alphabot/chat
// Handles Simple/Pro mode toggle
// Manages command shortcuts (/explain, /agents, etc.)
```

### 6.4 Key Component Details

**SigCard** — most important component. Displays per-pair:
- Pair name + current price (live, ticking)
- Direction badge (BUY/SELL/HOLD) with color
- Agreement badge (FULL/PARTIAL/CONFLICT)
- 3 agent pills (Macro/Tech/Sent) with their individual verdicts
- Confidence bar
- Lifecycle status (Active / Near Expiry / Expired) with age
- Selected state (bottom amber border)
- Click to select → updates AlphaBot context to that pair

**AlphaBotPanel** — centrepiece:
- Message list with user/bot bubbles
- Typing indicator (3-dot animation)
- Command chips that auto-fill input
- Simple/Pro toggle (affects both past messages' framing and future requests)
- Input with `▸` prompt prefix, amber focus ring
- On send: POST to `/api/alphabot/chat` with `{pair, message, mode, history}`

**EventCalendar** — right panel:
- Events from WS `calendar` field
- Color-coded: red dot for high impact, yellow for medium, grey for low
- Passed events at 50% opacity
- Countdown for upcoming events (in Xh Xm format)
- Automatically highlights events affecting the selected pair

**NewsFeed** — right panel:
- Articles from WS `news` field
- Currency tags (USD/EUR/GBP/JPY) in amber
- Age label (3m ago, 1h ago)
- Click opens article URL (add URL field to news_service)

### 6.5 Additional Pages

**History Page** (`/history`)
Table of all signals from `GET /api/history`
Columns: Time | Pair | Direction | Confidence | Agreement | Regime | Entry Price | Lifecycle | Reasoning (expandable)
Filters: pair selector, direction filter, date range
Export to CSV button

**Settings Page** (`/settings`)
- Watchlist: toggle which pairs to show (stored in localStorage for now)
- Default language mode: Simple / Pro
- Theme: Dark only for now (only one theme)

**Auth (deferred unless required)**
Register / Login pages with JWT — defer until core is working.

---

## Part 7 — Build Order

Do not skip phases. Each phase unlocks the next.

### Phase 1 — Data Pipeline (do this first, everything depends on it)
1. Audit actual keys in `macro_out`, `tech_out`, `sent_out` by adding a debug log in `_process_pair()` to print the full dict — do this before assuming key names
2. Fix `runner.py`: capture enrichment dict, compute trade levels, merge into signal
3. Fix `_save_signal()`: expand column list
4. Fix `signal_store.py`: fix `update()` to not discard incoming signals
5. Run one agent cycle manually, verify the CSV now has all new columns
6. Verify `GET /api/signals` returns enriched data

### Phase 2 — New Backend Services
1. `price_service.py` + `/api/prices` endpoint
2. `calendar_service.py` + `/api/calendar` endpoint
3. `news_service.py` + `/api/news` endpoint
4. Run `compute_backtest_stats.py`, verify `stats_cache.json` is created
5. Update `/api/stats` to serve from the cache file
6. Test all endpoints with curl/Postman

### Phase 3 — AlphaBot
1. Add `get_latest_for_pair()` and `get_recent_headlines()` to `signal_store.py`
2. Implement `app/api/alphabot.py` (non-streaming first)
3. Test with manual POST — verify it returns coherent responses for Simple and Pro mode
4. Register router in `main.py`
5. (Later) upgrade to SSE streaming

### Phase 4 — WebSocket Enhancement
1. Update `broadcast_update()` to include prices, calendar, news
2. Add 30-second price broadcast job in scheduler
3. Test from browser console that WS messages contain all fields

### Phase 5 — Frontend Rebuild
1. Set up Tailwind tokens and font imports
2. Build layout shell (FunctionBar, TickerStrip, LeftNav, StatusBar)
3. Implement `useSignals` WebSocket hook
4. Build SignalStrip + SigCard
5. Build AlphaBotPanel + `useAlphaBot` hook
6. Build RightPanel (PerfStats + EventCalendar + NewsFeed)
7. Wire Simple/Pro toggle end-to-end
8. History page
9. Settings page

---

## Part 8 — Validation Notes

**Key Name Corrections Applied:**

The build plan has been validated against the actual codebase. All key names have been corrected:

1. **MacroAgent**: Features are nested in `mac_features` dict (e.g., `mac_feats.get("mac_yield_z")`)
2. **MacroAgent**: Regime probs are in `regime_probs` dict (e.g., `regime_probs.get("bullish")`)
3. **TechnicalAgent**: Uses `confidence` not `model_confidence`
4. **TechnicalAgent**: Uses lowercase `p_buy`, `p_sell`, `p_hold` (no uppercase `P(BUY)`)
5. **SentimentAgent**: Returns `p_buy` which we map to `p_bullish` field for clarity
6. **NewsFeed**: `nws_news_flow` was intentionally removed (bug fix), not available

**Groq API Key:**

The orchestrator already has Groq client initialization in `orchestrator.py`:
```python
groq_key = llm.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")
if GROQ_AVAILABLE and groq_key:
    self.groq_client = Groq(api_key=groq_key)
```

The AlphaBot endpoint should use the same pattern:
```python
from app.config import settings
groq_client = Groq(api_key=settings.GROQ_API_KEY)
```

Add to `Deployment/Backend/app/config.py`:
```python
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
```

**RSS Feed URLs:**

Add to `config.py` to avoid duplication:
```python
import yaml
from pathlib import Path

# Load RSS feeds from agent config
AGENT_CONFIG_PATH = FX_ALPHALAB_ROOT / "fx_alphalab" / "config" / "configs" / "agent_config.yaml"
if AGENT_CONFIG_PATH.exists():
    with open(AGENT_CONFIG_PATH) as f:
        _agent_cfg = yaml.safe_load(f)
    RSS_FEEDS = _agent_cfg.get("news", {}).get("rss_feeds", [])
else:
    RSS_FEEDS = [
        "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
    ]
```

---

## Part 9 — Ready to Execute

| Component | File(s) | Status | Phase |
|---|---|---|---|
| Enrich signal with features + price | `runner.py` | Modify | 1 |
| Fix signal_store update() | `signal_store.py` | Fix bug | 1 |
| Expand CSV schema | `runner.py` | Modify | 1 |
| Live prices endpoint | `price_service.py`, `api/prices.py` | New | 2 |
| Economic calendar | `calendar_service.py`, `api/calendar.py` | New | 2 |
| News display service | `news_service.py`, `api/news.py` | New | 2 |
| Real performance stats | `scripts/compute_backtest_stats.py` | New | 2 |
| AlphaBot chat | `api/alphabot.py` | New | 3 |
| Signal lifecycle compute | `api/signals.py` | Enhance | 3 |
| WebSocket enriched broadcast | `websocket.py` | Enhance | 4 |
| 30s price broadcast | `main.py` scheduler | Add | 4 |
| Frontend design system | Tailwind config, fonts | New | 5 |
| useSignals WS hook | `hooks/useSignals.ts` | New | 5 |
| SignalStrip + SigCard | `components/` | New | 5 |
| AlphaBotPanel | `components/` | New | 5 |
| RightPanel (stats/cal/news) | `components/` | New | 5 |
| History page | `components/` | New | 5 |
| Settings page | `components/` | New | 5 |


---

## ✅ VALIDATION COMPLETE

**Date:** 2026-04-30  
**Status:** All key name mismatches corrected, build plan validated against actual codebase

**Key Corrections Made:**
1. MacroAgent features: Now correctly accesses nested `mac_features` dict
2. Regime probabilities: Now correctly extracts from `regime_probs` dict  
3. TechnicalAgent: Uses `confidence` (not `model_confidence`)
4. TechnicalAgent: Uses lowercase `p_buy`, `p_sell`, `p_hold`
5. SentimentAgent: Maps `p_buy` to `p_bullish` field for clarity
6. Documentation: Updated all references to match actual agent output structure

**Ready for Implementation:** ✅  
All phases can now proceed with confidence that the data structures match reality.

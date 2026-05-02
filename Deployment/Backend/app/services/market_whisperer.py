"""
Market Whisperer — Agentic AI that proactively monitors the market
and pushes alerts to the frontend via WebSocket.

Runs every 2 minutes. Detects anomalies silently, speaks only when
something matters.

Compatible with:
  - app.services.signal_store     → get_latest_for_pair(pair)
  - app.services.news_service     → news_service.get_articles()
  - app.services.price_service    → price_service.get_prices()
  - app.services.calendar_service → calendar_service.get_upcoming()
  - app.api.websocket             → manager.broadcast(dict)
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from groq import AsyncGroq
from loguru import logger


# ─────────────────────────────────────────────
#  Alert severity levels
# ─────────────────────────────────────────────
SEVERITY_ALERT       = "ALERT"        # 🔴 price spike / stop hit
SEVERITY_OPPORTUNITY = "OPPORTUNITY"  # ⚡ signal flip / macro event
SEVERITY_WARNING     = "WARNING"      # ⚠️ news spike / sentiment shift


# ─────────────────────────────────────────────
#  Thresholds
# ─────────────────────────────────────────────
PRICE_THRESHOLDS = {
    "EURUSD=X": 0.30,   # ~30 pips
    "GBPUSD=X": 0.35,   # ~35 pips
    "USDJPY=X": 0.25,   # ~25 pips
}
NEWS_SPIKE_COUNT        = 3     # N articles on same pair within window
NEWS_SPIKE_WINDOW_SECS  = 240   # 4 minutes
SIGNAL_CONFIDENCE_FLIP_GAP = 0.20
CALENDAR_LOOKAHEAD_MINS = 30


class MarketWhisperer:
    """
    Proactive monitoring agent. Wired into the same data the main
    pipeline already collects — zero extra external API calls.

    Usage in main.py lifespan:
        from app.services.market_whisperer import market_whisperer
        asyncio.create_task(market_whisperer.start())
    """

    def __init__(
        self,
        pairs: list[str] | None = None,
        interval_secs: int = 120,
    ):
        self.pairs    = pairs or ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
        self.interval = interval_secs

        # State kept between ticks
        self._last_prices:      dict[str, float]          = {}
        self._last_news_ts:     dict[str, float]          = {}
        self._last_signal_conf: dict[str, float]          = {}
        self._last_alert_ts:    dict[str, dict[str, float]] = {}  # ← NEW
        self._running = False

        # Lazy-init Groq so import works before .env is loaded
        self._groq: Optional[AsyncGroq] = None

    # ─────────────────────────────────────────
    #  Lifecycle
    # ─────────────────────────────────────────

    async def start(self):
        self._running = True
        logger.info(f"Market Whisperer started — monitoring every {self.interval}s")
        while self._running:
            try:
                await self._tick()
            except Exception as exc:
                logger.exception(f"Whisperer tick error: {exc}")
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False

    def _get_groq(self) -> AsyncGroq:
        if self._groq is None:
            from app.config import settings
            self._groq = AsyncGroq(api_key=settings.GROQ_API_KEY)
        return self._groq

    # ─────────────────────────────────────────
    #  Cooldown — NEW
    # ─────────────────────────────────────────

    def _cooldown_ok(self, pair: str, alert_type: str, cooldown_secs: int = 600) -> bool:
        """Prevent same alert firing more than once per 10 minutes."""
        last = self._last_alert_ts.get(pair, {}).get(alert_type, 0)
        return (datetime.now(timezone.utc).timestamp() - last) > cooldown_secs

    def _update_cooldown(self, pair: str, alert_type: str):
        if pair not in self._last_alert_ts:
            self._last_alert_ts[pair] = {}
        self._last_alert_ts[pair][alert_type] = datetime.now(timezone.utc).timestamp()

    # ─────────────────────────────────────────
    #  Main tick
    # ─────────────────────────────────────────

    async def _tick(self):
        now   = datetime.now(timezone.utc)
        tasks = [self._check_pair(pair, now) for pair in self.pairs]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _check_pair(self, pair: str, now: datetime):
        clean_pair = pair.replace("=X", "")

        # ── 1. Price spike ──────────────────────────────────────────
        current_price = self._get_price(pair)
        if current_price is not None:
            if self._detect_price_spike(pair, current_price):
                prev     = self._last_prices[pair]
                move_pct = abs(current_price - prev) / prev * 100
                await self._fire_alert(
                    pair=clean_pair,
                    severity=SEVERITY_ALERT,
                    alert_type="PRICE_SPIKE",
                    context={
                        "price":      round(current_price, 5),
                        "prev_price": round(prev, 5),
                        "move_pct":   round(move_pct, 3),
                    },
                )
            self._last_prices[pair] = current_price

        # ── 2. News spike ───────────────────────────────────────────
        spike, articles = self._detect_news_spike(pair, now)
        if spike:
            await self._fire_alert(
                pair=clean_pair,
                severity=SEVERITY_WARNING,
                alert_type="NEWS_SPIKE",
                context={
                    "article_count": len(articles),
                    "sentiment":     self._dominant_sentiment(articles),
                    "headlines":     [a.get("title", "") for a in articles[:3]],
                },
            )
            self._last_news_ts[pair] = now.timestamp()

        # ── 3. Signal flip incoming ─────────────────────────────────
        flip_info = self._detect_signal_flip(pair)
        if flip_info:
            await self._fire_alert(
                pair=clean_pair,
                severity=SEVERITY_OPPORTUNITY,
                alert_type="SIGNAL_FLIP_INCOMING",
                context=flip_info,
            )

        # ── 4. High-impact calendar event in next 30 min ───────────
        event = self._detect_upcoming_event(pair)
        if event:
            await self._fire_alert(
                pair=clean_pair,
                severity=SEVERITY_ALERT,
                alert_type="CALENDAR_RISK",
                context={"event": event},
            )

    # ─────────────────────────────────────────
    #  Detectors
    # ─────────────────────────────────────────

    def _get_price(self, pair: str) -> Optional[float]:
        """Read from price_service.get_prices() — already cached, no API call."""
        try:
            from app.services import price_service
            prices = price_service.get_prices()
            val    = prices.get(pair) or prices.get(pair.replace("=X", ""))
            if val is None:
                return None
            # Handle Price object or plain float
            if isinstance(val, dict):
                return float(val.get("price") or val.get("bid") or val.get("last") or 0)
            return float(val)
        except Exception as e:
            logger.debug(f"_get_price({pair}) failed: {e}")
            return None

    def _detect_price_spike(self, pair: str, current: float) -> bool:
        prev = self._last_prices.get(pair)
        if prev is None or prev == 0:
            return False
        move_pct  = abs(current - prev) / prev * 100
        threshold = PRICE_THRESHOLDS.get(pair, 0.30)  # ← per-pair threshold
        return move_pct >= threshold

    def _detect_news_spike(self, pair: str, now: datetime) -> tuple[bool, list]:
        """Cooldown prevents re-firing the same spike."""
        last = self._last_news_ts.get(pair, 0)
        if now.timestamp() - last < NEWS_SPIKE_WINDOW_SECS:
            return False, []

        try:
            from app.services.news_service import news_service as _ns
            articles = _ns.get_articles(max_age_hours=1, limit=50)
        except Exception as e:
            logger.debug(f"news spike check failed: {e}")
            return False, []

        if not articles:
            return False, []

        pair_clean   = pair.replace("=X", "")
        currency_map = {
            "EURUSD": {"EUR", "USD"},
            "GBPUSD": {"GBP", "USD"},
            "USDJPY": {"JPY", "USD"},
        }
        relevant = currency_map.get(pair_clean, set())
        cutoff   = now.timestamp() - NEWS_SPIKE_WINDOW_SECS
        recent   = [
            a for a in articles
            if self._article_ts(a) >= cutoff
            and bool(relevant & set(a.get("tags", [])))
        ]
        return len(recent) >= NEWS_SPIKE_COUNT, recent

    def _detect_signal_flip(self, pair: str) -> Optional[dict]:
        try:
            from app.services.signal_store import signal_store
            signal = signal_store.get_latest_for_pair(pair.replace("=X", ""))
        except Exception as e:
            logger.debug(f"_detect_signal_flip({pair}) failed: {e}")
            return None

        if signal is None:
            return None

        current_conf = float(signal.get("confidence", 0.5))
        prev_conf    = self._last_signal_conf.get(pair, current_conf)
        self._last_signal_conf[pair] = current_conf

        swing = abs(current_conf - prev_conf)
        if swing >= SIGNAL_CONFIDENCE_FLIP_GAP:
            return {
                "current_direction": signal.get("direction"),
                "confidence_now":    round(current_conf, 3),
                "confidence_prev":   round(prev_conf, 3),
                "swing":             round(swing, 3),
            }
        return None

    def _detect_upcoming_event(self, pair: str) -> Optional[dict]:
        try:
            from app.services import calendar_service
            events = calendar_service.get_upcoming(hours_ahead=1)
        except Exception as e:
            logger.debug(f"_detect_upcoming_event({pair}) failed: {e}")
            return None

        if not events:
            return None

        pair_clean   = pair.replace("=X", "")
        currency_map = {
            "EURUSD": {"EUR", "USD"},
            "GBPUSD": {"GBP", "USD"},
            "USDJPY": {"JPY", "USD"},
        }
        relevant = currency_map.get(pair_clean, set())
        now      = datetime.now(timezone.utc)

        for event in events:
            if str(event.get("impact", "")).upper() not in ("HIGH", "3", "3-STAR", "***"):
                continue
            if str(event.get("currency", "")) not in relevant:
                continue
            event_time = event.get("datetime") or event.get("time") or event.get("date")
            if event_time:
                try:
                    if isinstance(event_time, str):
                        from dateutil import parser as dp
                        event_dt = dp.parse(event_time)
                        if event_dt.tzinfo is None:
                            event_dt = event_dt.replace(tzinfo=timezone.utc)
                    else:
                        event_dt = event_time
                    mins_away = (event_dt - now).total_seconds() / 60
                    if 0 <= mins_away <= CALENDAR_LOOKAHEAD_MINS:
                        return event
                except Exception:
                    pass
        return None

    # ─────────────────────────────────────────
    #  LLM + broadcast
    # ─────────────────────────────────────────

    async def _fire_alert(self, pair: str, severity: str, alert_type: str, context: dict):
        # Cooldown check — don't repeat same alert within 10 min
        if not self._cooldown_ok(pair, alert_type):
            logger.debug(f"[Whisperer] {pair} {alert_type} in cooldown — skipped")
            return

        # Update cooldown
        self._update_cooldown(pair, alert_type)

        message = await self._generate_message(pair, severity, alert_type, context)

        alert = {
            "type":            "whisper_alert",
            "pair":            pair,
            "severity":        severity,
            "alert_type":      alert_type,
            "message":         message,
            "context":         context,
            "timestamp":       datetime.now(timezone.utc).isoformat(),
            "alphabot_prompt": self._build_alphabot_prompt(pair, alert_type, context),
        }

        logger.warning(f"[Whisperer] {severity} | {pair} | {alert_type}")

        try:
            from app.api.websocket import manager
            await manager.broadcast(alert)
        except Exception as e:
            logger.error(f"Whisperer broadcast failed: {e}")

    async def _generate_message(self, pair: str, severity: str, alert_type: str, context: dict) -> str:
        icons = {
            SEVERITY_ALERT:       "🔴",
            SEVERITY_OPPORTUNITY: "⚡",
            SEVERITY_WARNING:     "⚠️",
        }
        icon = icons.get(severity, "ℹ️")
        ts   = datetime.now(timezone.utc).strftime("%H:%M UTC")

        prompt = f"""You are a senior FX analyst. Write a short alert (2-3 sentences max) for a trader.

Pair: {pair}
Alert type: {alert_type}
Context: {context}

Rules:
- Start with the FACT (use numbers from context)
- Add the IMPLICATION for the active trade
- End with one actionable suggestion
- Plain text only, no markdown
- Tone: calm expert"""

        try:
            response = await self._get_groq().chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            raw = response.choices[0].message.content.strip()
            return f"{icon} {severity} — {ts}\n{raw}"
        except Exception as exc:
            logger.warning(f"Groq message generation failed: {exc}")
            return f"{icon} {severity} — {ts}\n{alert_type} detected on {pair}."

    def _build_alphabot_prompt(self, pair: str, alert_type: str, context: dict) -> str:
        templates = {
            "PRICE_SPIKE": (
                f"A sudden price move was detected on {pair} "
                f"({context.get('move_pct', '?')}% in 2 minutes, now at {context.get('price', '?')}). "
                f"What does this mean for the active signal?"
            ),
            "NEWS_SPIKE": (
                f"{context.get('article_count', '?')} {context.get('sentiment', '')} articles "
                f"hit {pair} in 4 minutes. Headlines: {context.get('headlines', [])}. "
                f"Should I be concerned about the current signal?"
            ),
            "SIGNAL_FLIP_INCOMING": (
                f"The {pair} signal confidence shifted from "
                f"{context.get('confidence_prev', 0):.0%} to {context.get('confidence_now', 0):.0%}. "
                f"Current direction: {context.get('current_direction', '?')}. Is a flip likely?"
            ),
            "CALENDAR_RISK": (
                f"High-impact event for {pair} in under {CALENDAR_LOOKAHEAD_MINS} minutes: "
                f"{context.get('event', {})}. What risk management should I apply?"
            ),
        }
        return templates.get(alert_type, f"Tell me more about the {alert_type} alert on {pair}.")

    # ─────────────────────────────────────────
    #  Helpers
    # ─────────────────────────────────────────

    @staticmethod
    def _article_ts(article: dict) -> float:
        for key in ("published_at", "timestamp", "pubDate", "published", "date"):
            val = article.get(key)
            if val is None:
                continue
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                try:
                    from dateutil import parser as dp
                    return dp.parse(val).timestamp()
                except Exception:
                    pass
        return 0.0

    @staticmethod
    def _dominant_sentiment(articles: list[dict]) -> str:
        counts = {"bullish": 0, "bearish": 0, "neutral": 0}
        for a in articles:
            s = str(a.get("sentiment", "neutral")).lower()
            if s in counts:
                counts[s] += 1
        return max(counts, key=counts.get)


# Global instance — import this in main.py
market_whisperer = MarketWhisperer()
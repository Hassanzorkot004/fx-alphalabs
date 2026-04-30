"""
data_feed/news_feed.py
────────────────────────────────────────────────────────────────────────────
Fetches live FX news from free RSS feeds.

FIX: Added debug logging to diagnose why 55 articles → 0 relevant.
  - Logs timestamp range of fetched articles
  - Logs sample article titles to see what's being fetched
  - Loosened keyword filter further: any article with macro/economic terms passes
  - Increased lookback to 48h to catch weekend gaps
  - Falls back gracefully when RSS feeds are stale
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import feedparser
import numpy as np
from loguru import logger


BULLISH_WORDS = [
    "rally", "surge", "rise", "gain", "bull", "strong", "hawkish",
    "hike", "beat", "above", "growth", "record", "optimism", "buy",
    "strength", "recover", "boost", "jump", "climb", "advance",
    "high", "up", "positive", "improve", "better", "exceed", "rebound",
]
BEARISH_WORDS = [
    "fall", "drop", "decline", "sell", "bear", "weak", "dovish",
    "cut", "miss", "below", "recession", "fear", "risk", "loss",
    "slump", "crash", "plunge", "tumble", "slide", "retreat",
    "low", "down", "negative", "worsen", "disappoint", "concern", "warn",
]

# TIER 1: pair-specific — strong FX relevance
PAIR_KEYWORDS_T1 = {
    "EURUSD": ["euro", "eur", "ecb", "eurozone", "european central", "lagarde"],
    "GBPUSD": ["pound", "sterling", "boe", "bank of england", "bailey", "britain", "british"],
    "USDJPY": ["yen", "jpy", "boj", "bank of japan", "ueda", "japan", "japanese"],
}

# TIER 2: general macro — relevant to all FX pairs
GENERAL_KEYWORDS = [
    "dollar", "usd", "fed", "federal reserve", "powell", "fomc",
    "inflation", "cpi", "pce", "interest rate", "rate hike", "rate cut",
    "gdp", "economy", "economic", "central bank", "monetary policy",
    "yield", "treasury", "bond", "deficit", "trade", "tariff",
    "employment", "jobs", "payroll", "unemployment",
    "forex", "fx", "currency", "exchange rate",
    "recession", "growth", "geopolit", "risk",
]


def _score_headline(title: str, summary: str, pair: str) -> Optional[float]:
    """
    Returns sentiment score [-1, +1] if article is relevant to pair, else None.
    Relevance: TIER1 (pair-specific) OR TIER2 (general macro).
    """
    text     = (title + " " + summary).lower()
    pair_key = pair.replace("=X", "")

    t1_match = any(k in text for k in PAIR_KEYWORDS_T1.get(pair_key, []))
    t2_match = any(k in text for k in GENERAL_KEYWORDS)

    if not t1_match and not t2_match:
        return None

    bull  = sum(1 for w in BULLISH_WORDS if w in text)
    bear  = sum(1 for w in BEARISH_WORDS if w in text)
    total = bull + bear
    if total == 0:
        return 0.0
    return float((bull - bear) / total)


class NewsFeed:
    """
    Fetches RSS articles, scores sentiment per pair.
    """

    def __init__(self, cfg: dict) -> None:
        self.feed_urls    = cfg["news"]["rss_feeds"]
        self.max_articles = cfg["news"].get("max_articles", 20)
        self.lookback_h   = cfg["news"].get("lookback_hours", 48)
        self._cache_articles: List[Dict] = []
        self._cache_ts: Optional[datetime] = None
        self._cache_ttl_min = 30

    def fetch(self, pair: str, lookback_hours: Optional[int] = None) -> Dict:
        hours  = lookback_hours or self.lookback_h
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        all_articles = self._get_cached_articles()

        # Log article timestamp range for diagnostics
        if all_articles:
            oldest = min(a["published"] for a in all_articles)
            newest = max(a["published"] for a in all_articles)
            logger.debug(
                f"NewsFeed: articles span {oldest.strftime('%Y-%m-%d %H:%M')} "
                f"→ {newest.strftime('%Y-%m-%d %H:%M')} UTC"
            )

        recent = [a for a in all_articles if a["published"] >= cutoff]

        # Log sample headlines for diagnosis
        if recent and len(recent) > 0:
            logger.debug(f"NewsFeed: sample titles (first 3 recent):")
            for a in recent[:3]:
                logger.debug(f"  [{a['published'].strftime('%H:%M')}] {a['title'][:80]}")

        # Score articles for this pair
        scored = []
        for a in recent:
            s = _score_headline(a["title"], a["summary"], pair)
            if s is not None:
                scored.append((a, s))

        # If still 0 relevant from recent, try wider window (72h)
        if len(scored) == 0 and hours < 72:
            cutoff72 = datetime.now(timezone.utc) - timedelta(hours=72)
            recent72 = [a for a in all_articles if a["published"] >= cutoff72]
            for a in recent72:
                s = _score_headline(a["title"], a["summary"], pair)
                if s is not None:
                    scored.append((a, s))
            if scored:
                logger.debug(f"NewsFeed [{pair.replace('=X','')}]: extended to 72h window")

        n_articles = len(scored)
        scores     = [s for _, s in scored]

        headlines = [
            f"[{a['published'].strftime('%H:%M')}] {a['title']}"
            for a, _ in scored[:5]
        ]
        if not headlines:
            headlines = [f"No relevant FX news for {pair.replace('=X','')} in last {hours}h."]

        logger.info(
            f"NewsFeed [{pair.replace('=X','')}]: "
            f"{n_articles} relevant / {len(recent)} recent articles, "
            f"sent={float(np.mean(scores)) if scores else 0.0:+.2f}"
        )

        # Compute nws_* features
        if scores and n_articles >= 2:
            arr        = np.array(scores)
            sent_mean  = float(np.mean(arr))
            sent_fast  = float(np.mean(arr[-3:])  if len(arr) >= 3  else sent_mean)
            sent_slow  = float(np.mean(arr[-10:]) if len(arr) >= 10 else sent_mean)
            sent_mom   = float(sent_fast - sent_slow)
            news_flow  = float(n_articles)
            bull_c     = float((arr > 0.1).sum())
            bear_c     = float((arr < -0.1).sum())
            imbalance  = float((bull_c - bear_c) / max(n_articles, 1))
            pressure   = float(np.mean(np.abs(arr)))
            press_chg  = float(
                pressure - np.mean(np.abs(arr[:-1])) if len(arr) > 1 else 0.0
            )
            trend_str  = float(abs(sent_mean) * min(news_flow / 5.0, 1.0))
            flow_accel = float(
                n_articles - len([
                    a for a, _ in scored
                    if a["published"] >= cutoff + timedelta(hours=hours // 2)
                ])
            )
        else:
            (sent_mean, sent_fast, sent_slow, sent_mom, news_flow,
             flow_accel, imbalance, pressure, press_chg, trend_str) = (0.0,) * 10

        return {
            "headlines":   headlines,
            "n_articles":  n_articles,
            # "nws_features": {
            #     "nws_sent_signal":     sent_mean,
            #     "nws_sent_mom":        sent_mom,
            #     "nws_sent_fast":       sent_fast,
            #     "nws_sent_slow":       sent_slow,
            #     "nws_news_flow":       news_flow,
            #     "nws_flow_accel":      flow_accel,
            #     "nws_flow_imbalance":  imbalance,
            #     "nws_sent_pressure":   pressure,
            #     "nws_pressure_change": press_chg,
            #     "nws_trend_strength":  trend_str,
            # }
                        "nws_features": {
                "nws_sent_signal":     sent_mean,
                "nws_sent_mom":        sent_mom,
                "nws_sent_fast":       sent_fast,
                "nws_sent_slow":       sent_slow,
                "nws_flow_accel":      flow_accel,
                "nws_sent_pressure":   pressure,
                "nws_pressure_change": press_chg,
                "nws_trend_strength":  trend_str,
            },
        }

    def _get_cached_articles(self) -> List[Dict]:
        now = datetime.now(timezone.utc)
        if (self._cache_ts is not None and
                (now - self._cache_ts).total_seconds() < self._cache_ttl_min * 60):
            return self._cache_articles

        articles = []
        for url in self.feed_urls:
            try:
                feed = feedparser.parse(url)
                n_before = len(articles)
                for entry in feed.entries[:40]:
                    pub = self._parse_date(entry)
                    if pub is None:
                        continue
                    articles.append({
                        "title":     getattr(entry, "title",   ""),
                        "summary":   getattr(entry, "summary", ""),
                        "published": pub,
                    })
                n_fetched = len(articles) - n_before
                logger.debug(f"RSS [{url[:50]}...]: {n_fetched} entries")
            except Exception as e:
                logger.warning(f"RSS fetch failed [{url}]: {e}")

        articles.sort(key=lambda a: a["published"], reverse=True)
        self._cache_articles = articles
        self._cache_ts       = now
        logger.debug(f"NewsFeed: {len(articles)} total articles from RSS")
        return articles

    @staticmethod
    def _parse_date(entry) -> Optional[datetime]:
        for attr in ("published_parsed", "updated_parsed"):
            t = getattr(entry, attr, None)
            if t and t[0] > 2000:  # sanity check: year must be > 2000
                try:
                    return datetime(*t[:6], tzinfo=timezone.utc)
                except Exception:
                    pass
        # Do NOT fallback to now() — that gives fake timestamps
        return None
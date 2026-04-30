"""News display service — RSS feed for the frontend news panel."""
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import feedparser
from loguru import logger

PAIR_KEYWORDS = {
    "EUR": ["euro", "eur", "ecb", "eurozone", "lagarde"],
    "GBP": ["pound", "sterling", "boe", "bank of england", "bailey"],
    "JPY": ["yen", "jpy", "boj", "bank of japan", "japan", "ueda"],
    "USD": ["dollar", "usd", "fed", "federal reserve", "powell", "fomc"],
}

# Default RSS feeds (will be overridden by config)
DEFAULT_RSS_FEEDS = [
    "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
]


class NewsService:
    def __init__(self, rss_feeds: List[str] = None, cache_ttl_minutes: int = 15):
        self._cache: List[Dict] = []
        self._cache_ts: float = 0
        self._ttl = cache_ttl_minutes * 60
        self._feeds = rss_feeds or DEFAULT_RSS_FEEDS

    def get_articles(self, max_age_hours: int = 48, limit: int = 30) -> List[Dict]:
        now = time.time()
        if now - self._cache_ts < self._ttl and self._cache:
            return self._cache[:limit]

        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        for url in self._feeds:
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


# Global service instance (will be initialized with config in main.py)
news_service = NewsService()

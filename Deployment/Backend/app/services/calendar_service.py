"""Economic calendar service — ForexFactory public feed."""
import time
from datetime import datetime, timezone
from typing import Dict, List

import pytz
import requests
from dateutil import parser as dateutil_parser
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
                dt = dateutil_parser.parse(e["datetime_utc"])
                delta = (dt - now).total_seconds() / 3600
                if -1 <= delta <= hours_ahead:  # include events up to 1h past
                    e["hours_until"] = round(delta, 2)
                    e["status"] = "passed" if delta < 0 else "upcoming"
                    result.append(e)
            except Exception:
                continue
        return result


# Global service instance
calendar_service = CalendarService()

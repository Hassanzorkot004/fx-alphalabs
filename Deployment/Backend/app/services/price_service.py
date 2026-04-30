"""Live price service — thin yfinance wrapper with caching."""
import time
from typing import Dict

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
                            "pair":       pair,
                            "price":      round(price, dec),
                            "change":     round(price - prev, dec),
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


# Global service instance
price_service = PriceService()

"""
data_feed/macro_feed.py
────────────────────────────────────────────────────────────────────────────
Fetches macro data from FRED and derives mac_* features.
IMPROVEMENT: Also fetches pair-specific foreign 10Y yield to compute
pair_carry_signal — the pair-specific yield differential feature.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests
from loguru import logger


FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

# Foreign 10Y government bond FRED series per pair
PAIR_FOREIGN_YIELD = {
    "EURUSD": "IRLTLT01DEM156N",   # Germany
    "GBPUSD": "IRLTLT01GBM156N",   # UK
    "USDJPY": "IRLTLT01JPM156N",   # Japan
}
# Sign convention: positive carry = USD relatively more attractive
PAIR_USD_IS_BASE = {"EURUSD": False, "GBPUSD": False, "USDJPY": True}


def _fetch_fred_series(series_id: str, api_key: str, days: int = 400) -> pd.Series:
    start = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    params = {
        "series_id":         series_id,
        "api_key":           api_key,
        "file_type":         "json",
        "observation_start": start,
    }
    try:
        r = requests.get(FRED_BASE, params=params, timeout=10)
        r.raise_for_status()
        obs  = r.json().get("observations", [])
        vals = {o["date"]: float(o["value"]) if o["value"] != "." else np.nan
                for o in obs}
        s = pd.Series(vals)
        s.index = pd.to_datetime(s.index)
        return s.ffill().bfill()
    except Exception as e:
        logger.warning(f"FRED fetch failed for {series_id}: {e}")
        return pd.Series(dtype=float)


def _to_datetime_index(ts) -> pd.DatetimeIndex:
    if isinstance(ts, pd.DatetimeIndex):
        return ts
    if isinstance(ts, pd.Series):
        return pd.DatetimeIndex(ts)
    return pd.DatetimeIndex(ts)


class MacroFeed:

    def __init__(self, cfg: dict) -> None:
        self.api_key   = cfg.get("fred", {}).get("api_key", "")
        self.series    = cfg.get("fred", {}).get("series", {})
        self._cache: Optional[pd.DataFrame]   = None
        self._cache_ts: Optional[datetime]    = None
        self._pair_cache: Dict[str, pd.Series] = {}  # pair → carry series
        self._cache_ttl_h = 4

    def fetch(self, hourly_index, pair: str = "") -> pd.DataFrame:
        idx  = _to_datetime_index(hourly_index)
        cols = [
            "mac_yield_z", "mac_yield_mom", "mac_yield_accel",
            "mac_cb_tone_z", "mac_cb_shock_z", "mac_macro_strength",
            "mac_vix_global", "mac_vix_z", "mac_missing",
            "pair_yield_diff", "pair_yield_diff_z",
            "pair_yield_diff_mom", "pair_carry_signal",
        ]
        empty = pd.DataFrame(0.0, index=idx, columns=cols)
        empty["mac_missing"] = 1

        if not self.api_key or self.api_key == "YOUR_FRED_API_KEY":
            return empty

        now = datetime.utcnow()
        cache_fresh = (
            self._cache is not None and self._cache_ts is not None and
            (now - self._cache_ts).total_seconds() < self._cache_ttl_h * 3600
        )

        if cache_fresh:
            result = self._align(self._cache, idx, cols[:-4])  # US macro cols
        else:
            try:
                y10 = _fetch_fred_series(self.series.get("yield_10y_us", "DGS10"),  self.api_key)
                y2  = _fetch_fred_series(self.series.get("yield_2y_us",  "DGS2"),   self.api_key)
                vix = _fetch_fred_series(self.series.get("vix",          "VIXCLS"), self.api_key)
            except Exception as e:
                logger.error(f"MacroFeed fetch error: {e}")
                return empty

            if y10.empty or y2.empty or vix.empty:
                return empty

            daily = pd.DataFrame({"yield_10y": y10, "yield_2y": y2, "vix": vix}).ffill().bfill()

            spread     = daily["yield_10y"] - daily["yield_2y"]
            spread_mu  = spread.rolling(252, min_periods=20).mean()
            spread_std = spread.rolling(252, min_periods=20).std().replace(0, np.nan)
            daily["mac_yield_z"]     = ((spread - spread_mu) / spread_std).clip(-4, 4)
            daily["mac_yield_mom"]   = daily["mac_yield_z"].diff(5)
            daily["mac_yield_accel"] = daily["mac_yield_mom"].diff(5)

            vix_mu  = daily["vix"].rolling(252, min_periods=20).mean()
            vix_std = daily["vix"].rolling(252, min_periods=20).std().replace(0, np.nan)
            daily["mac_vix_global"] = daily["vix"]
            daily["mac_vix_z"]      = ((daily["vix"] - vix_mu) / vix_std).clip(-4, 4)

            y2_mom = daily["yield_2y"].diff(5)
            y2_std = y2_mom.rolling(252, min_periods=20).std().replace(0, np.nan)
            daily["mac_cb_tone_z"]  = (y2_mom / y2_std).clip(-4, 4)
            daily["mac_cb_shock_z"] = daily["mac_cb_tone_z"].diff(1)
            daily["mac_macro_strength"] = (
                0.5 * daily["mac_yield_z"] - 0.5 * daily["mac_vix_z"]
            ).clip(-4, 4)
            daily["mac_missing"] = 0
            daily.ffill(inplace=True)
            daily.fillna(0, inplace=True)

            self._cache    = daily
            self._cache_ts = now
            self._pair_cache = {}  # invalidate pair cache too
            logger.info(f"MacroFeed: fetched {len(daily)} daily observations")
            result = self._align(daily, idx, cols[:-4])

        # Add pair-specific carry features
        pair_key = pair.replace("=X", "")
        result = self._add_carry_features(result, idx, pair_key)

        return result

    def _add_carry_features(self, df: pd.DataFrame, idx: pd.DatetimeIndex,
                             pair: str) -> pd.DataFrame:
        """Fetch and align pair-specific carry signal."""
        pair_cols = ["pair_yield_diff", "pair_yield_diff_z",
                     "pair_yield_diff_mom", "pair_carry_signal"]
        for col in pair_cols:
            if col not in df.columns:
                df[col] = 0.0

        fred_id = PAIR_FOREIGN_YIELD.get(pair)
        if not fred_id or not self.api_key:
            return df

        # Use cached carry series if available
        if pair not in self._pair_cache:
            us_10y   = _fetch_fred_series("DGS10", self.api_key, days=800)
            foreign  = _fetch_fred_series(fred_id, self.api_key, days=800)
            if us_10y.empty or foreign.empty:
                return df

            daily_pair = pd.DataFrame({
                "us": us_10y, "foreign": foreign
            }).ffill().bfill().dropna()

            spread   = daily_pair["us"] - daily_pair["foreign"]
            mu       = spread.rolling(252, min_periods=20).mean()
            std      = spread.rolling(252, min_periods=20).std().replace(0, np.nan)
            diff_z   = ((spread - mu) / std).clip(-4, 4)
            diff_mom = diff_z.diff(5)
            sign     = 1.0 if PAIR_USD_IS_BASE.get(pair, False) else -1.0
            carry    = (diff_z * sign).clip(-4, 4)

            daily_pair["pair_yield_diff"]     = spread.values
            daily_pair["pair_yield_diff_z"]   = diff_z.values
            daily_pair["pair_yield_diff_mom"]  = diff_mom.values
            daily_pair["pair_carry_signal"]    = carry.values
            daily_pair = daily_pair.ffill().fillna(0)
            self._pair_cache[pair] = daily_pair

        carry_daily = self._pair_cache[pair]
        aligned = self._align(carry_daily, idx, pair_cols)
        for col in pair_cols:
            df[col] = aligned[col].values

        return df

    @staticmethod
    def _align(daily: pd.DataFrame, idx: pd.DatetimeIndex, cols: list) -> pd.DataFrame:
        daily_tz = daily.copy()
        if daily_tz.index.tz is None:
            daily_tz.index = daily_tz.index.tz_localize("UTC")
        hourly_tz = idx if idx.tz is not None else idx.tz_localize("UTC")

        combined = daily_tz.reindex(daily_tz.index.union(hourly_tz)).ffill()
        result   = combined.reindex(hourly_tz)

        out = pd.DataFrame(index=idx)
        for col in cols:
            out[col] = result[col].values if col in result.columns else 0.0
        out.ffill(inplace=True)
        out.fillna(0, inplace=True)
        return out
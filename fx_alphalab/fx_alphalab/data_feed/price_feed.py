"""
data_feed/price_feed.py
────────────────────────────────────────────────────────────────────────────
Live OHLCV price feed using yfinance.
Fetches the last N bars for a given pair at hourly resolution.
Also computes all technical indicators needed by the technical agent.
"""
from __future__ import annotations

import warnings
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

warnings.filterwarnings("ignore")


# ── Technical indicator helpers ───────────────────────────────────────────────

def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()

def _sma(s: pd.Series, n: int) -> pd.Series:
    return s.rolling(n, min_periods=1).mean()

def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    gain = d.clip(lower=0).ewm(span=n, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(span=n, adjust=False).mean()
    rs   = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def _atr(h: pd.Series, l: pd.Series, c: pd.Series, n: int = 14) -> pd.Series:
    tr = pd.concat([
        h - l,
        (h - c.shift()).abs(),
        (l - c.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.ewm(span=n, adjust=False).mean()

def _macd(s: pd.Series):
    fast = _ema(s, 12)
    slow = _ema(s, 26)
    line = fast - slow
    sig  = _ema(line, 9)
    hist = line - sig
    std  = line.rolling(100, min_periods=10).std().replace(0, np.nan)
    return line / std, hist / std

def _bbands(c: pd.Series, n: int = 20):
    mid   = _sma(c, n)
    std   = c.rolling(n, min_periods=1).std()
    upper = mid + 2 * std
    lower = mid - 2 * std
    pos   = (c - lower) / (upper - lower + 1e-9)
    width = (upper - lower) / (mid + 1e-9)
    return pos.clip(0, 1), width

def _cmf(h, l, c, v, n: int = 20) -> pd.Series:
    mfm = ((c - l) - (h - c)) / (h - l + 1e-9)
    mfv = mfm * v
    return mfv.rolling(n, min_periods=1).sum() / v.rolling(n, min_periods=1).sum().replace(0, np.nan)

def _time_features(ts: pd.Series):
    hour = ts.dt.hour
    dow  = ts.dt.dayofweek
    h_sin = np.sin(2 * np.pi * hour / 24)
    h_cos = np.cos(2 * np.pi * hour / 24)
    d_sin = np.sin(2 * np.pi * dow  / 7)
    d_cos = np.cos(2 * np.pi * dow  / 7)
    return h_sin, h_cos, d_sin, d_cos

def _session_flags(ts: pd.Series):
    hour = ts.dt.hour
    tokyo   = ((hour >= 0)  & (hour < 9 )).astype(int)
    london  = ((hour >= 8)  & (hour < 17)).astype(int)
    newyork = ((hour >= 13) & (hour < 22)).astype(int)
    overlap = (london & newyork).astype(int)
    return tokyo, london, newyork, overlap


def compute_technical_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all technical indicator columns to an OHLCV dataframe.
    Input columns required: open, high, low, close, volume, timestamp_utc
    """
    o, h, l, c, v = (df["open"], df["high"], df["low"],
                     df["close"], df["volume"])

    # Trend
    ema8   = _ema(c, 8)
    ema21  = _ema(c, 21)
    ema50  = _ema(c, 50)
    sma200 = _sma(c, 200)
    sma10  = _sma(c, 10)
    sma50  = _sma(c, 50)

    df["ema_cross"]       = (ema8 - ema21) / (c + 1e-9)
    df["price_vs_ema50"]  = (c - ema50)    / (c + 1e-9)
    df["price_vs_sma200"] = (c - sma200)   / (c + 1e-9)
    df["sma10_slope"]     = sma10.diff(3)  / (c + 1e-9)
    df["sma50_slope"]     = sma50.diff(6)  / (c + 1e-9)

    # Momentum
    df["rsi14"] = _rsi(c, 14) / 100.0
    df["rsi28"] = _rsi(c, 28) / 100.0
    df["macd_norm"], df["macd_hist"] = _macd(c)
    df["roc1"] = c.pct_change(1)
    df["roc3"] = c.pct_change(3)
    df["roc5"] = c.pct_change(5)

    # Volatility
    atr_raw = _atr(h, l, c)
    df["atr"]     = atr_raw
    df["atr_pct"] = atr_raw / (c + 1e-9)
    atr_sma = _sma(atr_raw, 20)
    df["atr_ratio"] = atr_raw / (atr_sma + 1e-9)
    df["bb_pos"], df["bb_width"] = _bbands(c)

    # Candle structure
    body   = (c - o).abs()
    candle = (h - l + 1e-9)
    df["body_ratio"]   = body / candle
    df["upper_shadow"] = (h - pd.concat([c, o], axis=1).max(axis=1)) / candle
    df["lower_shadow"] = (pd.concat([c, o], axis=1).min(axis=1) - l) / candle

    # Volume
    vol_sma = _sma(v.astype(float), 20)
    df["vol_sma20"] = vol_sma
    df["vol_ratio"] = v.astype(float) / (vol_sma + 1e-9)
    df["cmf"]       = _cmf(h, l, c, v.astype(float))

    # Time
    ts = pd.to_datetime(df["timestamp_utc"])
    (df["hour_sin"], df["hour_cos"],
     df["dow_sin"],  df["dow_cos"]) = _time_features(ts)
    (df["is_tokyo"], df["is_london"],
     df["is_newyork"], df["is_overlap"]) = _session_flags(ts)
    df["is_dead"] = (
        (ts.dt.hour >= 22) | (ts.dt.hour < 2) |
        (ts.dt.dayofweek >= 5)
    ).astype(int)

    # Forward-fill then zero-fill any remaining NaN
    df.ffill(inplace=True)
    df.fillna(0, inplace=True)

    return df


class PriceFeed:
    """
    Fetches live OHLCV data from Yahoo Finance and computes all
    technical features. Returns a clean DataFrame ready for the agents.

    Usage:
        feed = PriceFeed(cfg)
        df   = feed.fetch("EURUSD=X", n_bars=720)
    """

    def __init__(self, cfg: dict) -> None:
        self.interval    = cfg["system"]["bar_interval"]
        self.lookback    = cfg["system"]["lookback_bars"]

    def fetch(
        self,
        pair: str,
        n_bars: Optional[int] = None,
    ) -> Optional[pd.DataFrame]:
        """
        Download the last n_bars hourly candles for `pair`.
        Returns a DataFrame with OHLCV + all technical features,
        or None if the download fails.
        """
        n = n_bars or self.lookback
        period = self._bars_to_period(n)

        try:
            raw = yf.download(
                pair,
                period=period,
                interval=self.interval,
                progress=False,
                auto_adjust=True,
            )
            if raw.empty:
                logger.warning(f"No data returned for {pair}")
                return None
        except Exception as e:
            logger.error(f"yfinance download failed for {pair}: {e}")
            return None

        # Normalise columns
        raw.columns = [c.lower() if isinstance(c, str) else c[0].lower()
                       for c in raw.columns]
        raw = raw.rename(columns={"adj close": "close"})
        raw.index.name = "timestamp_utc"
        raw = raw.reset_index()
        raw["timestamp_utc"] = pd.to_datetime(raw["timestamp_utc"], utc=True)
        raw["pair"]          = pair.replace("=X", "")

        # Drop incomplete last bar (may still be forming)
        raw = raw.iloc[:-1]

        # Compute technical features
        raw = compute_technical_features(raw)

        logger.info(
            f"PriceFeed [{pair}]: {len(raw)} bars "
            f"[{raw['timestamp_utc'].iloc[0]} → {raw['timestamp_utc'].iloc[-1]}]"
        )
        return raw

    @staticmethod
    def _bars_to_period(n_bars: int) -> str:
        """Convert bar count to yfinance period string (hourly bars)."""
        days = max(int(n_bars / 16) + 5, 7)   # ~16 trading hours/day + buffer
        if   days <= 7:   return "7d"
        elif days <= 30:  return "30d"
        elif days <= 60:  return "60d"
        elif days <= 90:  return "90d"
        else:             return "730d"
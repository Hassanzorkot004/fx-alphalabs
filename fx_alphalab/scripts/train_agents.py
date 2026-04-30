"""
train_agents.py
────────────────────────────────────────────────────────────────────────────
IMPROVEMENTS IN THIS VERSION:
  1. 4-year training data — two 730-day chunks merged per pair
     (~34,000 bars each vs ~17,000 before)
  2. Pair-specific yield differentials:
       EURUSD: US10Y - Germany10Y  (IRLTLT01DEM156N)
       GBPUSD: US10Y - UK10Y       (IRLTLT01GBM156N)
       USDJPY: US10Y - Japan10Y    (IRLTLT01JPM156N)
     Each pair now has economically meaningful carry signal features
     instead of all sharing the same US-only yield curve.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import yfinance as yf
import yaml
from loguru import logger

from agents.macro_agent     import MacroAgent
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent
from data_feed.price_feed   import compute_technical_features
from data_feed.macro_feed   import _fetch_fred_series


CFG_PATH = "configs/agent_config.yaml"

# Foreign 10Y bond series per pair (FRED)
PAIR_FOREIGN_YIELD = {
    "EURUSD": "IRLTLT01DEM156N",   # Germany long-term gov bond (monthly)
    "GBPUSD": "IRLTLT01GBM156N",   # UK long-term gov bond (monthly)
    "USDJPY": "IRLTLT01JPM156N",   # Japan long-term gov bond (monthly)
}

# True when USD is the base currency of the pair
# Wider US-foreign spread = USD stronger
#   → bearish for EUR/GBP (USD is quote) → sign=-1
#   → bullish for USD/JPY (USD is base)  → sign=+1
PAIR_USD_IS_BASE = {
    "EURUSD": False,
    "GBPUSD": False,
    "USDJPY": True,
}


def load_cfg() -> dict:
    with open(CFG_PATH) as f:
        return yaml.safe_load(f)


# ── Step 1: Download ~4 years via two 730-day chunks ─────────────────────────

def download_ohlcv_chunked(pairs: list) -> pd.DataFrame:
    """
    yfinance caps hourly data at 730 days per request.
    Download two chunks and merge:
      Chunk A: period="730d"  (most recent 730 days)
      Chunk B: start/end dates targeting the 730 days before chunk A
    """
    all_dfs = []

    for pair in pairs:
        frames = []

        # Chunk A — recent 730 days (always works)
        logger.info(f"  [{pair}] chunk 1/2 — recent 730 days …")
        df_a = _download_yf(pair, period="730d")
        if df_a is not None:
            frames.append(df_a)
            oldest_a = df_a["timestamp_utc"].min()
        else:
            oldest_a = pd.Timestamp.now(tz="UTC")

        # Chunk B — the 730 days before chunk A using explicit start/end
        end_b   = oldest_a - pd.Timedelta(hours=1)
        start_b = end_b - pd.Timedelta(days=729)
        logger.info(
            f"  [{pair}] chunk 2/2 — "
            f"{start_b.date()} → {end_b.date()} …"
        )
        df_b = _download_yf_range(pair, start_b, end_b)
        if df_b is not None and len(df_b) > 0:
            frames.append(df_b)

        if not frames:
            logger.warning(f"  [{pair}] no data — skipping")
            continue

        combined = pd.concat(frames, ignore_index=True)
        combined = combined.drop_duplicates(subset=["timestamp_utc"])
        combined = combined.sort_values("timestamp_utc").reset_index(drop=True)

        logger.info(
            f"  [{pair}]: {len(combined):,} bars total "
            f"[{combined['timestamp_utc'].iloc[0].date()} → "
            f"{combined['timestamp_utc'].iloc[-1].date()}]"
        )
        all_dfs.append(combined)

    if not all_dfs:
        raise RuntimeError("No data downloaded.")
    return pd.concat(all_dfs, ignore_index=True)


def _download_yf(pair: str, period: str) -> pd.DataFrame | None:
    try:
        raw = yf.download(pair, period=period, interval="1h",
                          progress=False, auto_adjust=True)
        if raw.empty:
            return None
        return _clean_yf(raw, pair)
    except Exception as e:
        logger.warning(f"  yfinance error [{pair}]: {e}")
        return None


def _download_yf_range(pair: str, start, end) -> pd.DataFrame | None:
    try:
        raw = yf.download(
            pair,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            interval="1h",
            progress=False,
            auto_adjust=True,
        )
        if raw.empty:
            return None
        return _clean_yf(raw, pair)
    except Exception as e:
        logger.warning(f"  yfinance range error [{pair}]: {e}")
        return None


def _clean_yf(raw: pd.DataFrame, pair: str) -> pd.DataFrame:
    raw.columns = [
        c.lower() if isinstance(c, str) else c[0].lower()
        for c in raw.columns
    ]
    raw.index.name = "timestamp_utc"
    raw = raw.reset_index()
    raw["timestamp_utc"] = pd.to_datetime(raw["timestamp_utc"], utc=True)
    raw["pair"] = pair.replace("=X", "")
    raw = compute_technical_features(raw)
    return raw


# ── Step 2: Shared US macro features ─────────────────────────────────────────

def add_macro_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    api_key = cfg.get("fred", {}).get("api_key", "")
    mac_cols = [
        "mac_yield_z", "mac_yield_mom", "mac_yield_accel",
        "mac_cb_tone_z", "mac_cb_shock_z", "mac_macro_strength",
        "mac_vix_global", "mac_vix_z", "mac_missing",
    ]

    if not api_key or api_key == "YOUR_FRED_API_KEY":
        logger.warning("No FRED API key — mac_* features will be zeros.")
        for col in mac_cols:
            df[col] = 0.0
        df["mac_missing"] = 1
        return df

    logger.info("  Fetching US FRED data (yield curve + VIX, 1600 days) …")
    y10 = _fetch_fred_series("DGS10",  api_key, days=1600)
    y2  = _fetch_fred_series("DGS2",   api_key, days=1600)
    vix = _fetch_fred_series("VIXCLS", api_key, days=1600)

    daily = pd.DataFrame({"yield_10y": y10, "yield_2y": y2, "vix": vix}).ffill().bfill()
    daily = MacroAgent.compute_mac_features(daily)

    df = _align_daily_to_hourly(df, daily, mac_cols)

    n_nz = (df["mac_yield_z"] != 0).sum()
    logger.info(
        f"  US macro: {len(daily)} daily obs → {len(df):,} hourly bars, "
        f"{n_nz:,} non-zero yield_z rows"
    )
    return df


# ── Step 3: Pair-specific yield differential features ─────────────────────────

def add_pair_macro_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Adds 4 columns per pair:
      pair_yield_diff      raw US-foreign 10Y spread (%)
      pair_yield_diff_z    z-scored spread (252-day rolling)
      pair_yield_diff_mom  5-day momentum of z-scored spread
      pair_carry_signal    direction-adjusted carry for this pair
                           positive = USD attractive = favor USD side
    """
    api_key = cfg.get("fred", {}).get("api_key", "")
    pair_cols = [
        "pair_yield_diff", "pair_yield_diff_z",
        "pair_yield_diff_mom", "pair_carry_signal",
    ]

    # Initialise all to zero
    for col in pair_cols:
        df[col] = 0.0

    if not api_key or api_key == "YOUR_FRED_API_KEY":
        return df

    logger.info("  Fetching pair-specific yield differentials …")
    us_10y = _fetch_fred_series("DGS10", api_key, days=1600)

    for pair in df["pair"].unique():
        fred_id = PAIR_FOREIGN_YIELD.get(pair)
        if not fred_id:
            logger.warning(f"  [{pair}] no foreign yield series — skipping")
            continue

        logger.info(f"  [{pair}] → {fred_id} …")
        foreign = _fetch_fred_series(fred_id, api_key, days=1600)

        if foreign.empty:
            logger.warning(f"  [{pair}] fetch failed — using zeros")
            continue

        daily = pd.DataFrame({"us": us_10y, "foreign": foreign}).ffill().bfill().dropna()
        spread   = daily["us"] - daily["foreign"]
        mu       = spread.rolling(252, min_periods=20).mean()
        std      = spread.rolling(252, min_periods=20).std().replace(0, np.nan)
        diff_z   = ((spread - mu) / std).clip(-4, 4)
        diff_mom = diff_z.diff(5)

        sign  = 1.0 if PAIR_USD_IS_BASE.get(pair, False) else -1.0
        carry = (diff_z * sign).clip(-4, 4)

        daily["pair_yield_diff"]     = spread.values
        daily["pair_yield_diff_z"]   = diff_z.values
        daily["pair_yield_diff_mom"] = diff_mom.values
        daily["pair_carry_signal"]   = carry.values
        daily = daily.ffill().fillna(0)

        mask       = df["pair"] == pair
        pair_slice = df[mask].copy()
        aligned    = _align_daily_to_hourly(pair_slice, daily, pair_cols)
        for col in pair_cols:
            df.loc[mask, col] = aligned[col].values

        n_nz = (df.loc[mask, "pair_yield_diff_z"] != 0).sum()
        logger.info(
            f"  [{pair}] spread={spread.iloc[-1]:.2f}%  "
            f"carry={carry.iloc[-1]:+.3f}  "
            f"{n_nz:,} non-zero rows"
        )

    df.ffill(inplace=True)
    df.fillna(0, inplace=True)
    return df


def _align_daily_to_hourly(df: pd.DataFrame, daily: pd.DataFrame,
                            cols: list) -> pd.DataFrame:
    ts = df["timestamp_utc"].copy()
    if ts.dt.tz is None:
        ts = ts.dt.tz_localize("UTC")

    daily_tz = daily.copy()
    if daily_tz.index.tz is None:
        daily_tz.index = daily_tz.index.tz_localize("UTC")
    daily_tz.index = daily_tz.index.astype("datetime64[us, UTC]")
    ts_norm   = ts.astype("datetime64[us, UTC]")
    daily_ts  = daily_tz.index.values
    hourly_ts = ts_norm.values
    idx = np.clip(
        np.searchsorted(daily_ts, hourly_ts, side="right") - 1,
        0, len(daily_ts) - 1
    )
    result = df.copy()
    for col in cols:
        result[col] = daily_tz[col].values[idx] if col in daily_tz.columns else 0.0
    result.ffill(inplace=True)
    result.fillna(0, inplace=True)
    return result


# ── Step 4: Sentiment proxy ───────────────────────────────────────────────────

def add_sentiment_features(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("  Computing proxy sentiment features …")
    price_sig = np.sign(df["roc1"].fillna(0))
    df["nws_sent_signal"]     = price_sig.rolling(3,  min_periods=1).mean().fillna(0)
    df["nws_sent_fast"]       = price_sig.ewm(span=3 ).mean().fillna(0)
    df["nws_sent_slow"]       = price_sig.ewm(span=12).mean().fillna(0)
    df["nws_sent_mom"]        = (df["nws_sent_fast"] - df["nws_sent_slow"]).fillna(0)
    df["nws_sent_pressure"]   = df["nws_sent_signal"].abs().rolling(6,  min_periods=1).mean().fillna(0)
    df["nws_pressure_change"] = df["nws_sent_pressure"].diff(1).fillna(0)
    df["nws_flow_accel"]      = df["nws_sent_mom"].diff(1).fillna(0)
    df["nws_flow_imbalance"]  = (df["nws_sent_fast"] - df["nws_sent_slow"]).fillna(0)
    df["nws_trend_strength"]  = df["nws_sent_signal"].abs().rolling(12, min_periods=1).mean().fillna(0)
    logger.info("  Sentiment proxy features done")
    return df


# ── Step 5: Targets ───────────────────────────────────────────────────────────

def compute_target(df: pd.DataFrame, horizon: int = 12) -> pd.DataFrame:
    def _per_pair(grp):
        fwd = np.log(grp["close"].shift(-horizon) / grp["close"])
        t   = pd.Series(0, index=grp.index, dtype=int)
        t[fwd < fwd.quantile(0.35)]  = -1
        t[fwd > fwd.quantile(0.65)]  =  1
        t[fwd.isna()]                =  0
        return t

    df["target"] = df.groupby("pair", group_keys=False).apply(_per_pair)
    counts = df["target"].value_counts().sort_index()
    logger.info(
        f"  Targets: SELL={int(counts.get(-1,0)):,}  "
        f"HOLD={int(counts.get(0,0)):,}  "
        f"BUY={int(counts.get(1,0)):,}"
    )
    return df


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║   FX AlphaLab v2  ·  Training  (4yr + pair yields)      ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")

    cfg   = load_cfg()
    pairs = cfg["system"]["pairs"]

    logger.info("Step 1/6 — Downloading ~4 years OHLCV (2 chunks/pair) …")
    df = download_ohlcv_chunked(pairs)
    logger.info(f"  Total: {len(df):,} bars across {df['pair'].nunique()} pairs")

    logger.info("Step 2/6 — Adding shared US macro features …")
    df = add_macro_features(df, cfg)

    logger.info("Step 3/6 — Adding pair-specific yield differentials …")
    df = add_pair_macro_features(df, cfg)

    logger.info("Step 4/6 — Adding sentiment proxy features …")
    df = add_sentiment_features(df)

    logger.info("Step 5/6 — Computing targets …")
    df = compute_target(df, horizon=12)

    logger.info("Step 6/6 — Training agents …")

    logger.info("  → MacroAgent …")
    macro = MacroAgent(cfg)
    macro.fit(df, ret_24h=df["mac_yield_z"])
    macro.save()

    logger.info("  → TechnicalAgent (per-pair, ~2x data) …")
    tech = TechnicalAgent(cfg)
    tech.fit(df, epochs=60)
    tech.save()

    logger.info("  → SentimentAgent …")
    sent = SentimentAgent(cfg)
    sent.fit(df)
    sent.save()

    logger.info("")
    logger.info("═" * 60)
    logger.info("  ALL AGENTS TRAINED SUCCESSFULLY")
    logger.info("═" * 60)
    logger.info(f"  Macro  → {cfg['paths']['macro_model']}")
    logger.info(f"  Tech   → {cfg['paths']['tech_model']}")
    logger.info(f"  Sent   → {cfg['paths']['sent_model']}")
    logger.info("")
    logger.info("  python run_agent.py --once")
    logger.info("  python run_agent.py")
    logger.info("═" * 60)


if __name__ == "__main__":
    main()
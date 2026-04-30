"""
backtest.py
────────────────────────────────────────────────────────────────────────────
Backtesting script pour FX AlphaLab v2/v3.

Principe :
  Pour chaque signal BUY/SELL actif (position_size > 0) :
    - Fetch le prix à l'heure du signal (entry)
    - Fetch le prix +12h après (exit) — correspond à l'horizon TechAgent
    - Calcule le P&L en pips et en % selon direction et position_size
    - Agrège : win rate, Sharpe, Max Drawdown, P&L par paire et par session

USAGE:
  python backtest.py
  python backtest.py --signals outputs/signals.csv
  python backtest.py --signals outputs/signals.csv --horizon 12
  python backtest.py --signals outputs/signals.csv --since 2026-04-28
"""
import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger


# ── Config ────────────────────────────────────────────────────────────────────

DEFAULT_SIGNALS = "outputs/signals.csv"
DEFAULT_HORIZON = 12       # heures — horizon TechAgent
PIP_SIZE = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
}
SESSION_HOURS = {
    "Tokyo":  (0,  8),
    "London": (8,  17),
    "NY":     (13, 22),
}


# ── Fetch prix historique ─────────────────────────────────────────────────────

def fetch_price_at(pair: str, ts: datetime, cache: dict) -> float | None:
    """Retourne le prix close le plus proche de ts pour la paire donnée."""
    pair_yf = pair if pair.endswith("=X") else f"{pair}=X"
    key     = pair_yf

    if key not in cache:
        logger.info(f"  Fetching price history for {pair_yf} …")
        try:
            df = yf.download(pair_yf, period="30d", interval="1h",
                             progress=False, auto_adjust=True)
            if df.empty:
                logger.warning(f"  No data for {pair_yf}")
                cache[key] = None
                return None
            df.columns = [c.lower() if isinstance(c, str) else c[0].lower()
                          for c in df.columns]
            df.index = pd.to_datetime(df.index, utc=True)
            cache[key] = df
        except Exception as e:
            logger.warning(f"  yfinance error for {pair_yf}: {e}")
            cache[key] = None
            return None

    df = cache[key]
    if df is None:
        return None

    # Trouver la barre la plus proche de ts
    ts_utc = ts.astimezone(timezone.utc) if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    ts_utc = ts_utc.replace(tzinfo=timezone.utc)

    idx = df.index.asof(pd.Timestamp(ts_utc))
    if pd.isna(idx):
        return None
    return float(df.loc[idx, "close"])


def get_session(ts: datetime) -> str:
    hour = ts.hour
    if 8 <= hour < 17:
        if 13 <= hour < 17:
            return "London/NY Overlap"
        return "London"
    elif 13 <= hour < 22:
        return "NY"
    elif 0 <= hour < 8:
        return "Tokyo"
    return "Dead"


# ── Calcul P&L par trade ──────────────────────────────────────────────────────

def compute_pnl(direction: str, entry: float, exit_: float,
                pair: str, position_size: float) -> dict:
    """
    Calcule le P&L d'un trade.
    Retourne dict avec pips, pct, won.
    """
    pip = PIP_SIZE.get(pair, 0.0001)

    if direction == "BUY":
        pips = (exit_ - entry) / pip
        pct  = (exit_ - entry) / entry * 100 * position_size
    else:  # SELL
        pips = (entry - exit_) / pip
        pct  = (entry - exit_) / entry * 100 * position_size

    return {
        "pips":     round(pips, 1),
        "pct":      round(pct, 4),
        "won":      pips > 0,
        "entry":    entry,
        "exit":     exit_,
    }


# ── Main backtest ─────────────────────────────────────────────────────────────

def run_backtest(signals_path: str, horizon_h: int = 12,
                 since: str = None) -> pd.DataFrame:

    logger.info(f"Loading signals from {signals_path} …")
    df = pd.read_csv(signals_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

    # Filtrer depuis une date si demandé
    if since:
        since_dt = pd.Timestamp(since, tz="UTC")
        df = df[df["timestamp"] >= since_dt]
        logger.info(f"Filtered to signals since {since}: {len(df)} rows")

    # Garder uniquement les signaux actifs (position_size > 0)
    active = df[
        (df["direction"].isin(["BUY", "SELL"])) &
        (df["position_size"] > 0)
    ].copy().reset_index(drop=True)

    logger.info(f"Active signals (BUY/SELL with size>0): {len(active)}")

    if len(active) == 0:
        logger.warning("No active signals to backtest.")
        return pd.DataFrame()

    # Cache prix yfinance
    price_cache = {}

    results = []
    for _, row in active.iterrows():
        pair     = row["pair"].replace("=X", "")
        pair_yf  = row["pair"]
        ts_entry = row["timestamp"].to_pydatetime()
        ts_exit  = ts_entry + timedelta(hours=horizon_h)
        direction = row["direction"]
        pos_size  = float(row["position_size"])
        conf      = float(row["confidence"])
        source    = row.get("source", "unknown")
        agreement = row.get("agent_agreement", "PARTIAL")
        session   = get_session(ts_entry)

        # Fetch prix entry et exit
        entry_price = fetch_price_at(pair_yf, ts_entry, price_cache)
        exit_price  = fetch_price_at(pair_yf, ts_exit,  price_cache)

        if entry_price is None or exit_price is None:
            logger.warning(
                f"  [{pair}] {ts_entry.strftime('%Y-%m-%d %H:%M')} "
                f"— missing price data, skipping"
            )
            continue

        pnl = compute_pnl(direction, entry_price, exit_price, pair, pos_size)

        results.append({
            "timestamp":   ts_entry,
            "pair":        pair,
            "direction":   direction,
            "confidence":  conf,
            "position_size": pos_size,
            "agreement":   agreement,
            "source":      source,
            "session":     session,
            "entry":       entry_price,
            "exit":        exit_price,
            "pips":        pnl["pips"],
            "pct":         pnl["pct"],
            "won":         pnl["won"],
        })

        status = "✓ WIN" if pnl["won"] else "✗ LOSS"
        logger.info(
            f"  [{pair}] {direction} {ts_entry.strftime('%m-%d %H:%M')} "
            f"→ {ts_exit.strftime('%H:%M')} | "
            f"entry={entry_price:.5f} exit={exit_price:.5f} | "
            f"{pnl['pips']:+.1f} pips | {status}"
        )

    if not results:
        logger.warning("No results computed.")
        return pd.DataFrame()

    return pd.DataFrame(results)


# ── Métriques ─────────────────────────────────────────────────────────────────

def compute_metrics(results: pd.DataFrame) -> None:
    if results.empty:
        logger.warning("No results to compute metrics on.")
        return

    n         = len(results)
    n_win     = results["won"].sum()
    win_rate  = n_win / n * 100
    total_pip = results["pips"].sum()
    total_pct = results["pct"].sum()
    avg_win   = results[results["won"]]["pips"].mean() if n_win > 0 else 0
    avg_loss  = results[~results["won"]]["pips"].mean() if (~results["won"]).sum() > 0 else 0

    # Sharpe (annualisé approximatif sur rendements horaires)
    pct_returns = results["pct"].values
    if pct_returns.std() > 0:
        sharpe = (pct_returns.mean() / pct_returns.std()) * np.sqrt(24 * 252)
    else:
        sharpe = 0.0

    # Max Drawdown
    cumulative = results["pct"].cumsum()
    rolling_max = cumulative.cummax()
    drawdown    = cumulative - rolling_max
    max_dd      = drawdown.min()

    # Profit factor
    gross_profit = results[results["pct"] > 0]["pct"].sum()
    gross_loss   = abs(results[results["pct"] < 0]["pct"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    print()
    print("═" * 60)
    print("  BACKTEST RESULTS — FX AlphaLab")
    print("═" * 60)
    print(f"  Période     : {results['timestamp'].min().strftime('%Y-%m-%d')} → "
          f"{results['timestamp'].max().strftime('%Y-%m-%d')}")
    print(f"  Horizon     : {DEFAULT_HORIZON}h par trade")
    print(f"  Trades      : {n}")
    print()
    print(f"  Win Rate    : {win_rate:.1f}% ({n_win}/{n})")
    print(f"  Total Pips  : {total_pip:+.1f}")
    print(f"  Total P&L   : {total_pct:+.4f}%")
    print(f"  Avg Win     : {avg_win:+.1f} pips")
    print(f"  Avg Loss    : {avg_loss:+.1f} pips")
    print(f"  Profit Factor: {profit_factor:.2f}")
    print(f"  Sharpe      : {sharpe:.2f}")
    print(f"  Max Drawdown: {max_dd:.4f}%")
    print()

    # Par paire
    print("  ── Par paire ──")
    for pair in results["pair"].unique():
        sub       = results[results["pair"] == pair]
        wr        = sub["won"].mean() * 100
        pips      = sub["pips"].sum()
        print(f"    {pair:<8} : {len(sub)} trades | "
              f"WR={wr:.0f}% | {pips:+.1f} pips")

    print()

    # Par session
    print("  ── Par session ──")
    for session in results["session"].unique():
        sub  = results[results["session"] == session]
        wr   = sub["won"].mean() * 100
        pips = sub["pips"].sum()
        print(f"    {session:<20} : {len(sub)} trades | "
              f"WR={wr:.0f}% | {pips:+.1f} pips")

    print()

    # Par source LLM
    print("  ── Par source LLM ──")
    for src in results["source"].unique():
        sub  = results[results["source"] == src]
        wr   = sub["won"].mean() * 100
        pips = sub["pips"].sum()
        print(f"    {src:<12} : {len(sub)} trades | "
              f"WR={wr:.0f}% | {pips:+.1f} pips")

    print()

    # Par agreement
    print("  ── Par agreement ──")
    for ag in results["agreement"].unique():
        sub  = results[results["agreement"] == ag]
        wr   = sub["won"].mean() * 100
        pips = sub["pips"].sum()
        print(f"    {ag:<10} : {len(sub)} trades | "
              f"WR={wr:.0f}% | {pips:+.1f} pips")

    print()
    print("═" * 60)

    # Avertissement si peu de données
    if n < 30:
        print(f"  ⚠ ATTENTION : seulement {n} trades.")
        print("  Les métriques ne sont pas statistiquement significatives.")
        print("  Il faut au minimum 30-50 trades pour des conclusions fiables.")
        print("  Continue à faire tourner run_agent.py pour accumuler des données.")
    print("═" * 60)


# ── Sauvegarder les résultats ─────────────────────────────────────────────────

def save_results(results: pd.DataFrame, path: str = "outputs/backtest_results.csv") -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(path, index=False)
    logger.info(f"Results saved to {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FX AlphaLab Backtester")
    parser.add_argument("--signals",  type=str, default=DEFAULT_SIGNALS)
    parser.add_argument("--horizon",  type=int, default=DEFAULT_HORIZON,
                        help="Exit horizon in hours (default: 12)")
    parser.add_argument("--since",    type=str, default=None,
                        help="Only backtest signals since this date (YYYY-MM-DD)")
    parser.add_argument("--save",     action="store_true",
                        help="Save results to outputs/backtest_results.csv")
    args = parser.parse_args()

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║   FX AlphaLab  ·  Backtester                            ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"  Signals : {args.signals}")
    logger.info(f"  Horizon : {args.horizon}h")
    if args.since:
        logger.info(f"  Since   : {args.since}")

    results = run_backtest(args.signals, args.horizon, args.since)

    if not results.empty:
        compute_metrics(results)
        if args.save:
            save_results(results)


if __name__ == "__main__":
    main()
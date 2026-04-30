"""
run_agent.py
────────────────────────────────────────────────────────────────────────────
Live agent loop. Run this after train_agents.py completes.

What happens every hour:
  1. Fetch live OHLCV for all pairs (yfinance)
  2. Fetch live macro data (FRED API)
  3. Fetch live news headlines (RSS feeds)
  4. Run all three specialist agents
  5. LLM orchestrator reasons over outputs
  6. Print structured signal to terminal
  7. Save signal to outputs/signals.csv
  8. Sleep until next bar

Usage:
    python run_agent.py              # runs all pairs every hour
    python run_agent.py --once       # runs one cycle and exits (for testing)
    python run_agent.py --pair EURUSD  # runs one specific pair
"""

import argparse
import csv
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import yaml
from loguru import logger

from agents.macro_agent      import MacroAgent
from agents.technical_agent  import TechnicalAgent
from agents.sentiment_agent  import SentimentAgent
from data_feed.price_feed    import PriceFeed
from data_feed.macro_feed    import MacroFeed
from data_feed.news_feed     import NewsFeed
from orchestrator.orchestrator import Orchestrator
from memory.context_store    import ContextStore


CFG_PATH = "configs/agent_config.yaml"

# ── Signal output formatting ──────────────────────────────────────────────────

DIRECTION_COLORS = {"BUY": "\033[92m", "SELL": "\033[91m", "HOLD": "\033[93m"}
RESET = "\033[0m"


def print_signal(signal: dict) -> None:
    pair      = signal.get("pair",      "???")
    direction = signal.get("direction", "HOLD")
    conf      = signal.get("confidence",   0.0)
    size      = signal.get("position_size",0.0)
    regime    = signal.get("macro_regime", "?")
    reasoning = signal.get("reasoning",    "")
    agreement = signal.get("agent_agreement", "?")
    tech_sig  = signal.get("tech_signal",  "?")
    sent_sig  = signal.get("sent_signal",  "?")
    ts        = signal.get("timestamp",    "")[:16]
    color     = DIRECTION_COLORS.get(direction, "")

    print()
    print("─" * 60)
    print(f"  {ts}  |  {pair}")
    print(f"  Signal   : {color}{direction}{RESET}  "
          f"(conf={conf:.2f}  size={size:.2f})")
    print(f"  Regime   : {regime}")
    print(f"  Agents   : macro={regime}  tech={tech_sig}  sent={sent_sig}")
    print(f"  Agreement: {agreement}")
    print(f"  Reasoning: {reasoning}")
    print("─" * 60)


def save_signal_csv(signal: dict, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    exists = Path(path).exists()
    cols   = [
        "timestamp", "pair", "direction", "confidence",
        "position_size", "macro_regime", "tech_signal", "sent_signal",
        "agent_agreement", "reasoning", "source",
    ]
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow(signal)


# ── Main loop ─────────────────────────────────────────────────────────────────

def run_cycle(
    pairs:      list,
    price_feed: PriceFeed,
    macro_feed: MacroFeed,
    news_feed:  NewsFeed,
    macro_agent:TechnicalAgent,
    tech_agent: TechnicalAgent,
    sent_agent: SentimentAgent,
    orchestrator: Orchestrator,
    context:    ContextStore,
    cfg:        dict,
) -> list:
    """Run one full analysis cycle for all pairs. Returns list of signals."""
    signals = []
    ts      = datetime.now(timezone.utc)
    logger.info(f"\n{'═'*60}")
    logger.info(f"  Cycle start: {ts.strftime('%Y-%m-%d %H:%M UTC')}")
    logger.info(f"{'═'*60}")

    for pair in pairs:
        logger.info(f"\n  ── {pair} ──")

        # 1. Price data + technical features
        price_df = price_feed.fetch(pair)
        if price_df is None or len(price_df) < 50:
            logger.warning(f"  Insufficient price data for {pair} — skipping")
            continue

        # 2. Macro data aligned to price timestamps
        macro_df = macro_feed.fetch(price_df["timestamp_utc"], pair=pair)

        # Merge macro into price df
        for col in macro_df.columns:
            price_df[col] = macro_df[col].values

        # 3. News data
        news_result = news_feed.fetch(pair)
        headlines   = news_result["headlines"]
        nws_feats   = news_result["nws_features"]

        # 4. Run specialist agents
        logger.info("  Running specialist agents …")
        macro_out = macro_agent.predict_live(price_df)
        tech_out  = tech_agent.predict_live(price_df)
        sent_out  = sent_agent.predict_live(nws_feats)

        logger.info(
            f"  macro={macro_out['regime_label']} "
            f"tech={tech_out['signal']} "
            f"sent={sent_out['signal']}"
        )

        # 5. LLM orchestrator
        logger.info("  LLM orchestrator reasoning …")
        signal = orchestrator.run(pair, macro_out, tech_out, sent_out, headlines)

        # 6. Display + save
        print_signal(signal)
        save_signal_csv(signal, cfg["paths"]["signals_csv"])

        # 7. Store in memory
        context.add(pair, signal)
        signals.append(signal)

    return signals


def main():
    parser = argparse.ArgumentParser(description="FX AlphaLab v2 Live Agent")
    parser.add_argument("--once",   action="store_true",
                        help="Run one cycle then exit")
    parser.add_argument("--pair",   type=str, default=None,
                        help="Run only this pair (e.g. EURUSD=X)")
    args = parser.parse_args()

    # ── Load config ──────────────────────────────────────────────────────────
    with open(CFG_PATH) as f:
        cfg = yaml.safe_load(f)

    pairs = [args.pair] if args.pair else cfg["system"]["pairs"]
    interval_s = cfg["system"]["run_every_mins"] * 60

    # ── Load trained agents ───────────────────────────────────────────────────
    logger.info("Loading trained agents …")
    try:
        macro_agent = MacroAgent(cfg).load()
        tech_agent  = TechnicalAgent(cfg).load()
        sent_agent  = SentimentAgent(cfg).load()
    except FileNotFoundError as e:
        logger.error(
            f"Model files not found: {e}\n"
            "Run training first:  python train_agents.py"
        )
        sys.exit(1)

    # ── Init data feeds ───────────────────────────────────────────────────────
    price_feed   = PriceFeed(cfg)
    macro_feed   = MacroFeed(cfg)
    news_feed    = NewsFeed(cfg)
    orchestrator = Orchestrator(cfg)
    context      = ContextStore(path=str(Path(cfg["paths"]["outputs_dir"]) / "context.json"))

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║     FX AlphaLab v2  ·  Live Agent Running               ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"  Pairs    : {pairs}")
    logger.info(f"  Interval : {cfg['system']['run_every_mins']} min")
    logger.info(f"  LLM      : {cfg['llm']['model']}")
    logger.info(f"  Signals  → {cfg['paths']['signals_csv']}")
    logger.info("")

    # ── Main loop ─────────────────────────────────────────────────────────────
    cycle = 0
    while True:
        cycle += 1
        logger.info(f"Cycle #{cycle}")
        try:
            run_cycle(
                pairs, price_feed, macro_feed, news_feed,
                macro_agent, tech_agent, sent_agent,
                orchestrator, context, cfg,
            )
        except KeyboardInterrupt:
            logger.info("\nAgent stopped by user.")
            break
        except Exception as e:
            logger.error(f"Cycle error: {e}")
            import traceback
            traceback.print_exc()

        if args.once:
            logger.info("--once flag set. Exiting.")
            break

        logger.info(f"\n  Next cycle in {cfg['system']['run_every_mins']} min. "
                    "Press Ctrl+C to stop.")
        try:
            time.sleep(interval_s)
        except KeyboardInterrupt:
            logger.info("\nAgent stopped by user.")
            break


if __name__ == "__main__":
    main()
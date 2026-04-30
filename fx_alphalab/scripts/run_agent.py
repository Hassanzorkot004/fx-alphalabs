#!/usr/bin/env python
"""
run_agent.py - CLI wrapper for AgentRunner

This is a thin wrapper around fx_alphalab.core.runner.AgentRunner
that provides the same CLI interface as before.

Usage:
    python scripts/run_agent.py              # runs all pairs every hour
    python scripts/run_agent.py --once       # runs one cycle and exits
    python scripts/run_agent.py --pair EURUSD=X  # runs one specific pair
    
Or after installation:
    fx-run
    fx-run --once
    fx-run --pair EURUSD=X
"""

import argparse
import sys
import time
from pathlib import Path

# Add parent directory to path for development
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger
from fx_alphalab.core.runner import AgentRunner


# ── Signal output formatting ──────────────────────────────────────────────────

DIRECTION_COLORS = {"BUY": "\033[92m", "SELL": "\033[91m", "HOLD": "\033[93m"}
RESET = "\033[0m"


def print_signal(signal: dict) -> None:
    """Pretty print a signal to terminal"""
    pair = signal.get("pair", "???")
    direction = signal.get("direction", "HOLD")
    conf = signal.get("confidence", 0.0)
    size = signal.get("position_size", 0.0)
    regime = signal.get("macro_regime", "?")
    reasoning = signal.get("reasoning", "")
    agreement = signal.get("agent_agreement", "?")
    tech_sig = signal.get("tech_signal", "?")
    sent_sig = signal.get("sent_signal", "?")
    ts = signal.get("timestamp", "")[:16]
    color = DIRECTION_COLORS.get(direction, "")

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


def main():
    parser = argparse.ArgumentParser(description="FX AlphaLab Live Agent")
    parser.add_argument("--once", action="store_true",
                        help="Run one cycle then exit")
    parser.add_argument("--pair", type=str, default=None,
                        help="Run only this pair (e.g. EURUSD=X)")
    args = parser.parse_args()

    # Initialize agent runner
    try:
        runner = AgentRunner()
    except Exception as e:
        logger.error(f"Failed to initialize AgentRunner: {e}")
        sys.exit(1)

    pairs = [args.pair] if args.pair else None
    interval_mins = runner.config["system"]["run_every_mins"]

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║     FX AlphaLab  ·  Live Agent Running                  ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"  Pairs    : {pairs or runner.config['system']['pairs']}")
    logger.info(f"  Interval : {interval_mins} min")
    logger.info(f"  LLM      : {runner.config['llm']['model']}")
    logger.info(f"  Signals  → {runner.config['paths']['signals_csv']}")
    logger.info("")

    # Main loop
    cycle = 0
    while True:
        cycle += 1
        logger.info(f"Cycle #{cycle}")
        
        try:
            signals = runner.run_cycle(pairs=pairs)
            
            # Print signals to terminal
            for signal in signals:
                print_signal(signal)
                
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

        logger.info(f"\n  Next cycle in {interval_mins} min. Press Ctrl+C to stop.")
        try:
            time.sleep(interval_mins * 60)
        except KeyboardInterrupt:
            logger.info("\nAgent stopped by user.")
            break


if __name__ == "__main__":
    main()

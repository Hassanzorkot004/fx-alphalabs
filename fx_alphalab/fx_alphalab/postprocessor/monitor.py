"""
postprocessor/monitor.py
────────────────────────────────────────────────────────────────────────────
BalanceMonitor — tracks rolling signal distribution and alerts on skew.

Runs every 6 bars per pair. If SELL or BUY exceeds 45% of the last
48 signals, it fires an alert. This is your live feedback loop —
it tells you when to adjust the conviction threshold.
"""
from collections import deque
from typing import Dict, List


class BalanceMonitor:
    """
    Tracks rolling signal distribution and fires alerts when skewed.

    Usage:
        monitor = BalanceMonitor("EURUSD")
        monitor.record("SELL")       # call after every corrected signal
        health = monitor.check()     # call every 6 bars
        if not health['healthy']:
            for alert in health['alerts']:
                logger.warning(alert)
    """

    def __init__(self, pair: str, window: int = 48, skew_threshold: float = 0.45):
        self.pair           = pair
        self.window         = window
        self.skew_threshold = skew_threshold
        self._history: deque = deque(maxlen=window)
        self._bar_count      = 0

    def record(self, signal: str) -> None:
        """Record a corrected signal. Call after every bar."""
        self._history.append(signal)
        self._bar_count += 1

    def check(self) -> Dict:
        """
        Check signal distribution health.

        Returns:
            {
                "healthy": bool,
                "alerts": list of warning strings,
                "distribution": {"BUY": pct, "SELL": pct, "HOLD": pct},
                "total_bars": int,
            }
        """
        if len(self._history) < 12:
            return {"healthy": True, "alerts": [], "distribution": {}, "total_bars": len(self._history)}

        total  = len(self._history)
        counts = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for s in self._history:
            counts[s] = counts.get(s, 0) + 1

        dist = {k: round(v / total, 3) for k, v in counts.items()}

        alerts  = []
        healthy = True

        # Check for directional skew
        directional = counts["BUY"] + counts["SELL"]
        if directional > 0:
            sell_pct = counts["SELL"] / directional
            buy_pct  = counts["BUY"]  / directional

            if sell_pct > self.skew_threshold:
                alerts.append(
                    f"[{self.pair}] SELL skew detected: {sell_pct:.0%} of directional "
                    f"signals are SELL (last {total} bars). Consider raising conviction threshold."
                )
                healthy = False

            if buy_pct > self.skew_threshold + 0.10:   # slightly more lenient for BUY
                alerts.append(
                    f"[{self.pair}] BUY skew detected: {buy_pct:.0%} of directional "
                    f"signals are BUY (last {total} bars)."
                )
                healthy = False

        # Check for signal drought (too many HOLDs)
        hold_pct = counts["HOLD"] / total
        if hold_pct > 0.95:
            alerts.append(
                f"[{self.pair}] Signal drought: {hold_pct:.0%} HOLDs in last {total} bars. "
                f"Consider lowering conviction threshold."
            )
            healthy = False

        return {
            "healthy":      healthy,
            "alerts":       alerts,
            "distribution": dist,
            "total_bars":   total,
        }

    @property
    def stats(self) -> Dict:
        """Quick stats without health check."""
        return self.check()

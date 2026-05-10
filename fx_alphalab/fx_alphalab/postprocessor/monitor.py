"""
BalanceMonitor — tracks rolling signal distribution and alerts on skew.

Runs every 6 bars per pair. If SELL or BUY exceeds 45% of the last
48 signals, it fires an alert. This is your live feedback loop —
it tells you when to adjust the conviction threshold.
"""
from collections import deque


class BalanceMonitor:
    """
    Tracks rolling signal distribution and fires alerts when skewed.
    
    Usage:
        monitor = BalanceMonitor("EURUSD")
        monitor.record("SELL")     # call after every corrected signal
        health = monitor.check()   # call every 6 bars
        if not health['healthy']:
            for alert in health['alerts']:
                log_alert(alert)
    """

    def __init__(self, pair: str, window: int = 48, alert_ratio: float = 3.0):
        self.pair = pair
        self.window = window
        self.alert_ratio = alert_ratio
        self._history = deque(maxlen=window)

    def record(self, signal: str):
        """Call after every corrected signal is produced."""
        self._history.append(signal)

    def check(self) -> dict:
        """
        Check if the distribution is healthy.
        Call every 6 bars (every 6 hours for hourly signals).
        
        Returns:
            dict with keys: pair, window, sell_pct, buy_pct, hold_pct,
                           alerts (list of warning strings), healthy (bool)
        """
        if len(self._history) < 12:
            return {
                'pair': self.pair,
                'window': len(self._history),
                'status': 'insufficient_data',
                'sell_pct': 0,
                'buy_pct': 0,
                'hold_pct': 0,
                'alerts': [],
                'healthy': True,
            }

        sells = self._history.count('SELL')
        buys  = self._history.count('BUY')
        holds = self._history.count('HOLD')
        total = len(self._history)

        sell_pct = sells / total
        buy_pct  = buys  / total
        hold_pct = holds / total

        alerts = []

        # Direction dominance check
        if buys > 0 and sells / buys > self.alert_ratio:
            alerts.append(
                f'[{self.pair}] SELL dominance: {sells} SELLs vs {buys} BUYs '
                f'in last {total} bars (ratio={sells/buys:.1f}:1)'
            )
        if sells > 0 and buys / sells > self.alert_ratio:
            alerts.append(
                f'[{self.pair}] BUY dominance: {buys} BUYs vs {sells} SELLs '
                f'in last {total} bars (ratio={buys/sells:.1f}:1)'
            )

        # Absolute percentage checks
        if sell_pct > 0.45:
            alerts.append(
                f'[{self.pair}] SELL rate={sell_pct:.0%} over last {total} bars '
                f'— consider raising conviction_threshold by 0.5'
            )
        if buy_pct > 0.45:
            alerts.append(
                f'[{self.pair}] BUY rate={buy_pct:.0%} over last {total} bars '
                f'— consider lowering conviction_threshold by 0.5'
            )

        return {
            'pair': self.pair,
            'window': total,
            'sell_pct': round(sell_pct, 3),
            'buy_pct': round(buy_pct, 3),
            'hold_pct': round(hold_pct, 3),
            'alerts': alerts,
            'healthy': len(alerts) == 0,
        }

    @property
    def distribution(self) -> dict:
        """Current distribution for frontend display."""
        if len(self._history) == 0:
            return {'SELL': 0, 'BUY': 0, 'HOLD': 0}
        total = len(self._history)
        return {
            'SELL': self._history.count('SELL') / total,
            'BUY': self._history.count('BUY') / total,
            'HOLD': self._history.count('HOLD') / total,
        }


# ── Quick self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    import random

    print("=" * 60)
    print("Testing BalanceMonitor")
    print("=" * 60)

    # Test 1: Balanced distribution
    print("\n1. Balanced distribution (16 each):")
    monitor = BalanceMonitor("TEST")
    for _ in range(16):
        monitor.record("SELL")
        monitor.record("BUY")
        monitor.record("HOLD")
    health = monitor.check()
    print(f"   SELL: {health['sell_pct']:.0%}, BUY: {health['buy_pct']:.0%}, HOLD: {health['hold_pct']:.0%}")
    print(f"   Healthy: {health['healthy']}, Alerts: {len(health['alerts'])}")
    assert health['healthy'], "Balanced should be healthy!"
    print("   ✅ Passed")

    # Test 2: SELL-dominated distribution
    print("\n2. SELL-dominated (30 SELL, 9 BUY, 9 HOLD):")
    monitor2 = BalanceMonitor("TEST")
    for _ in range(30):
        monitor2.record("SELL")
    for _ in range(9):
        monitor2.record("BUY")
        monitor2.record("HOLD")
    health2 = monitor2.check()
    print(f"   SELL: {health2['sell_pct']:.0%}, BUY: {health2['buy_pct']:.0%}, HOLD: {health2['hold_pct']:.0%}")
    print(f"   Healthy: {health2['healthy']}")
    for alert in health2['alerts']:
        print(f"   ⚠️  {alert}")
    assert not health2['healthy'], "SELL-dominated should trigger alerts!"
    print("   ✅ Passed")

    # Test 3: Insufficient data
    print("\n3. Insufficient data (only 5 signals):")
    monitor3 = BalanceMonitor("TEST")
    for _ in range(5):
        monitor3.record("HOLD")
    health3 = monitor3.check()
    print(f"   Status: {health3['status']}")
    assert health3['healthy'], "Insufficient data should not alert!"
    print("   ✅ Passed")

    print(f"\n{'='*60}")
    print("✅ All BalanceMonitor tests passed!")
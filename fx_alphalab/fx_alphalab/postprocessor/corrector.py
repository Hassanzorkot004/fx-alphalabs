"""
SignalCorrector — applies the conviction gate to every technical signal.

Sits between the TCN+LSTM model and the technical LLM analyst.
Every original ML field is preserved. The corrector only changes
what gets propagated forward.

Four gates, applied in order:
  1. Dynamic symmetry — if SELL dominates recent bars, tighten SELL threshold
  2. Tokyo session filter — pure Tokyo has worst signal quality, raise threshold
  3. Dead session — force HOLD regardless
  4. Conviction gate — requires 3+ features to agree
"""
from collections import deque
from dataclasses import dataclass

from .conviction import compute_conviction


@dataclass
class CorrectorConfig:
    """Configuration for the SignalCorrector. Tune these, not the code."""
    conviction_threshold: float = 3.0       # min score to fire directional signal
    session_suppress_tokyo: bool = True     # raise threshold in pure Tokyo
    symmetry_window: int = 24               # bars to check for direction dominance
    symmetry_ratio: float = 2.0             # if SELL > 2x BUY, tighten SELL
    buy_upgrade_from_hold: bool = True      # allow HOLD→BUY when conviction high
    buy_upgrade_threshold: float = 3.5      # higher bar for upgrading


class SignalCorrector:
    """
    Sits between model output and signal broadcast.
    Receives the raw ML output dict + the current feature row.
    Returns a corrected signal dict. Never modifies the ML output in-place.
    """

    def __init__(self, pair: str, config: CorrectorConfig = None):
        self.pair = pair
        self.config = config or CorrectorConfig()
        self._recent = deque(maxlen=self.config.symmetry_window)

    def correct(self, ml_output: dict, features: dict) -> dict:
        """
        Apply all four gates and return a corrected signal dict.
        
        Args:
            ml_output: raw model output with 'signal', 'p_buy', 'p_sell', etc.
            features: current bar features as a dict
        
        Returns:
            corrected dict with all original fields + correction metadata
        """
        # Compute conviction scores for both directions
        conv_sell = compute_conviction(features, -1)
        conv_buy  = compute_conviction(features, 1)

        # ── Gate 1: Dynamic symmetry ───────────────────────────────────
        # If one direction dominated the last N bars, raise its threshold.
        # This catches "stuck in one direction" failure mode live.
        threshold = self.config.conviction_threshold
        sells = sum(1 for s in self._recent if s == 'SELL')
        buys  = sum(1 for s in self._recent if s == 'BUY')
        symmetry_active = False
        
        if (len(self._recent) >= 12 and buys > 0 
                and sells / buys > self.config.symmetry_ratio):
            threshold += 0.5  # raise bar for SELLs specifically
            symmetry_active = True

        # ── Gate 2: Tokyo session filter ───────────────────────────────
        # Pure Tokyo (no London/NY overlap) has worst signal quality.
        # Data shows SELL accuracy drops ~30% in pure Tokyo hours.
        in_pure_tokyo = (features.get('is_tokyo', 0) == 1
                         and features.get('is_overlap', 0) == 0
                         and features.get('is_london', 0) == 0)
        tokyo_active = False
        if self.config.session_suppress_tokyo and in_pure_tokyo:
            threshold = max(threshold, 4.0)  # need maximum conviction
            tokyo_active = True

        # ── Gate 3: Dead session ───────────────────────────────────────
        # No meaningful price action → force HOLD regardless
        if features.get('is_dead', 0) == 1:
            self._recent.append('HOLD')
            return self._build(ml_output, 'HOLD', conv_sell, conv_buy,
                               'dead session — no meaningful price action',
                               symmetry_active, tokyo_active)

        # ── Gate 4: Conviction gate ────────────────────────────────────
        raw = ml_output.get('signal', 'HOLD')
        corrected = raw
        reason = None

        if raw == 'SELL' and conv_sell < threshold:
            corrected = 'HOLD'
            reason = (f'SELL suppressed: conviction={conv_sell:.2f} '
                      f'< threshold={threshold:.1f}')
        
        elif raw == 'BUY' and conv_buy < self.config.conviction_threshold:
            corrected = 'HOLD'
            reason = (f'BUY suppressed: conviction={conv_buy:.2f} '
                      f'< threshold={self.config.conviction_threshold:.1f}')
        
        elif raw == 'HOLD' and self.config.buy_upgrade_from_hold:
            # Conservative upgrade: only upgrade HOLD→BUY when ALL agree
            macro_agrees = (features.get('mac_yield_mom', 0) > 0
                            and features.get('mac_yield_accel', 0) > 0)
            if (conv_buy >= self.config.buy_upgrade_threshold
                    and macro_agrees
                    and features.get('roc1', 0) > 0.0002):
                corrected = 'BUY'
                reason = f'HOLD upgraded to BUY: conviction={conv_buy:.2f}, macro confirms'

        # Track for symmetry gate
        self._recent.append(corrected)

        return self._build(ml_output, corrected, conv_sell, conv_buy,
                           reason, symmetry_active, tokyo_active)

    def _build(self, ml_output: dict, corrected: str, conv_sell: float,
               conv_buy: float, reason: str, symmetry: bool, tokyo: bool) -> dict:
        """Build the output dict. Preserves all original fields."""
        return {
            # Original ML output — never hidden, always stored
            **ml_output,

            # Corrected signal — what the system acts on
            'signal': corrected,

            # Correction metadata — for explainability on the website
            'ml_raw_signal': ml_output.get('signal', 'HOLD'),
            'corrected': corrected != ml_output.get('signal', 'HOLD'),
            'correction_reason': reason,
            'conviction_sell': conv_sell,
            'conviction_buy': conv_buy,
            'symmetry_gate_active': symmetry,
            'tokyo_gate_active': tokyo,
        }

    @property
    def recent_signals(self) -> list:
        """For monitoring — see what the corrector has been doing."""
        return list(self._recent)


# ── Quick self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Testing SignalCorrector")
    print("=" * 60)

    corrector = SignalCorrector("TEST")

    # Simulate: model says SELL, features strongly agree with SELL
    ml_sell = {'signal': 'SELL', 'p_sell': 0.68, 'p_buy': 0.18, 
               'p_hold': 0.14, 'confidence': 0.31}
    feat_sell = {'roc1': -0.0025, 'roc3': -0.0018, 'bb_pos': 0.22,
                 'mac_yield_mom': -0.004, 'nws_flow_imbalance': 0.05,
                 'is_tokyo': 0, 'is_london': 1, 'is_overlap': 1,
                 'is_newyork': 0, 'is_dead': 0}
    
    result1 = corrector.correct(ml_sell, feat_sell)
    print(f"\n1. Model=SELL, Features=SELL:")
    print(f"   Signal: {result1['signal']} | Corrected: {result1['corrected']}")
    print(f"   Conviction SELL: {result1['conviction_sell']:.2f}, BUY: {result1['conviction_buy']:.2f}")
    assert result1['signal'] == 'SELL', "Strong SELL should pass!"
    print("   ✅ Passed")

    # Simulate: model says SELL, features are weak/neutral
    ml_sell2 = {'signal': 'SELL', 'p_sell': 0.45, 'p_buy': 0.30,
                'p_hold': 0.25, 'confidence': 0.15}
    feat_neutral = {'roc1': 0.00001, 'roc3': 0.00002, 'bb_pos': 0.51,
                    'mac_yield_mom': 0.001, 'nws_flow_imbalance': 0.01,
                    'is_tokyo': 0, 'is_london': 1, 'is_overlap': 1,
                    'is_newyork': 0, 'is_dead': 0}
    
    result2 = corrector.correct(ml_sell2, feat_neutral)
    print(f"\n2. Model=SELL, Features=NEUTRAL:")
    print(f"   Signal: {result2['signal']} | Corrected: {result2['corrected']}")
    print(f"   Reason: {result2['correction_reason']}")
    print(f"   Conviction SELL: {result2['conviction_sell']:.2f}, BUY: {result2['conviction_buy']:.2f}")
    assert result2['signal'] == 'HOLD', "Weak SELL should be suppressed!"
    print("   ✅ Passed")

    # Simulate: model says HOLD but BUY conviction is very strong
    ml_hold = {'signal': 'HOLD', 'p_buy': 0.40, 'p_sell': 0.35,
               'p_hold': 0.25, 'confidence': 0.10}
    feat_buy = {'roc1': 0.0040, 'roc3': 0.0035, 'bb_pos': 0.82,
                'mac_yield_mom': 0.008, 'mac_yield_accel': 0.003,
                'nws_flow_imbalance': 0.30,
                'is_tokyo': 0, 'is_london': 1, 'is_overlap': 1,
                'is_newyork': 0, 'is_dead': 0}
    
    result3 = corrector.correct(ml_hold, feat_buy)
    print(f"\n3. Model=HOLD, Features=Strong BUY:")
    print(f"   Signal: {result3['signal']} | Corrected: {result3['corrected']}")
    print(f"   Reason: {result3['correction_reason']}")
    assert result3['signal'] == 'BUY', "Strong BUY should upgrade HOLD!"
    print("   ✅ Passed")

    # Simulate: dead session
    feat_dead = {'roc1': 0, 'roc3': 0, 'bb_pos': 0.5, 'mac_yield_mom': 0,
                 'nws_flow_imbalance': 0, 'is_tokyo': 0, 'is_london': 0,
                 'is_overlap': 0, 'is_newyork': 0, 'is_dead': 1}
    result4 = corrector.correct(ml_sell, feat_dead)
    print(f"\n4. Dead session:")
    print(f"   Signal: {result4['signal']} | Reason: {result4['correction_reason']}")
    assert result4['signal'] == 'HOLD', "Dead session must be HOLD!"
    print("   ✅ Passed")

    print(f"\n{'='*60}")
    print("✅ All SignalCorrector tests passed!")
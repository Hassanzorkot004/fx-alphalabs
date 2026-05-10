"""
agents/conviction_gate.py
────────────────────────────────────────────────────────────────────────────
Stage 4 of 5 — Conviction Gate

OPTION 2 FIX — Minimum tech confidence before macro can amplify:
  Macro can only push a signal to directional if tech confidence >= 0.15.
  Below that threshold, macro agreement is ignored and the signal stays HOLD.
  This prevents a weak tech reading (p_sell=0.366, conf=0.016) from being
  amplified into a SELL just because macro happens to be bearish.

OPTION 3 FIX — Regime-conditional confidence floor:
  In a bearish macro regime, the minimum confidence required to produce a
  SELL signal is raised to 0.60 (vs 0.50 for neutral/bullish regimes).
  Rationale: the training data shows BUY is MORE common than SELL even
  when yield_z ~ -1.0 (21.8% BUY vs 17.3% SELL). A bearish macro regime
  does not mean prices go down — it means risk is elevated. Requiring
  higher conviction before acting in a bearish regime reduces false signals.

  Regime floors:
    bearish  → min_confidence = 0.62  (high bar — macro alone isn't enough)
    neutral  → min_confidence = 0.52  (standard)
    bullish  → min_confidence = 0.52  (standard)
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
from loguru import logger

# Minimum tech model confidence before macro can amplify a signal.
# Below this, macro agreement is ignored → direction stays HOLD.
MIN_TECH_CONF_FOR_MACRO_AMPLIFICATION = 0.15

# Regime-conditional confidence floors
REGIME_MIN_CONFIDENCE = {
    "bearish": 0.62,   # higher bar — macro bearish ≠ price goes down
    "neutral": 0.52,
    "bullish": 0.52,
}


# ── Macro direction helper ────────────────────────────────────────────────────

def effective_macro_dir(macro: Dict) -> Tuple[str, int]:
    """
    Return (effective_label, direction_int).
    Corrects for cluster mislabelling: if yield_z strongly contradicts
    the label, downgrade to neutral. Uses conservative thresholds to
    avoid suppressing valid signals on marginal macro readings.
    """
    label   = macro.get("regime_label", "neutral")
    feats   = macro.get("mac_features", {})
    yield_z = feats.get("mac_yield_z", 0.0)

    # Only override if yield_z strongly contradicts the label
    if label == "bearish" and yield_z > 0.30:
        label = "neutral"
    elif label == "bullish" and yield_z < -0.30:
        label = "neutral"

    direction = 1 if label == "bullish" else (-1 if label == "bearish" else 0)
    return label, direction


# ── Direction logic ───────────────────────────────────────────────────────────

def rule_based_direction(macro: Dict, tech: Dict, sent: Dict) -> str:
    """
    Deterministic direction from agent outputs. No LLM involved.

    Option 2: macro can only amplify a tech signal if tech confidence
    is above MIN_TECH_CONF_FOR_MACRO_AMPLIFICATION. A weak tech reading
    cannot be pushed to directional by macro agreement alone.
    """
    _, macro_dir = effective_macro_dir(macro)
    tech_dir     = tech.get("direction", 0)
    tech_conf    = float(tech.get("confidence", 0.0))
    sent_dir     = sent.get("direction", 0)
    sent_real    = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

    # No tech signal → no trade
    if tech_dir == 0:
        return "HOLD"

    # Tech + Sentiment agree → follow regardless of macro (sentiment is real-time)
    if sent_real and sent_dir == tech_dir:
        return "BUY" if tech_dir == 1 else "SELL"

    # Option 2: macro can only amplify if tech has minimum conviction
    tech_strong_enough = tech_conf >= MIN_TECH_CONF_FOR_MACRO_AMPLIFICATION

    if tech_strong_enough:
        # Tech + Macro agree → follow
        if macro_dir == tech_dir:
            return "BUY" if tech_dir == 1 else "SELL"

        # Direct conflict tech vs macro, no sentiment tiebreaker → HOLD
        if macro_dir == -tech_dir and macro_dir != 0:
            return "HOLD"

    # Tech alone (macro neutral, or tech too weak for macro to matter)
    # Still require minimum confidence — handled by conviction gate floor
    return "BUY" if tech_dir == 1 else "SELL"


# ── Confidence computation ────────────────────────────────────────────────────

def compute_conviction(
    direction: str,
    macro: Dict,
    tech: Dict,
    sent: Dict,
    min_confidence: float = 0.50,
) -> Tuple[float, float, str]:
    """
    Compute (confidence, position_size, agreement_tier).

    Returns:
        confidence:    float [0.35, 0.88]
        position_size: float [0.0, 0.88]
        agreement:     "FULL" | "PARTIAL" | "SOLO" | "CONFLICT"
    """
    if direction == "HOLD":
        return 0.50, 0.0, "CONFLICT"

    primary    = 1 if direction == "BUY" else -1
    tech_dir   = tech.get("direction", 0)
    tech_conf  = float(tech.get("confidence", 0.0))

    # Clamp negative confidence (model uncertain about both directions)
    tech_conf  = max(tech_conf, 0.0)

    sent_dir   = sent.get("direction", 0)
    sent_conf  = float(sent.get("confidence", 0.0))
    sent_real  = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

    eff_label, macro_dir = effective_macro_dir(macro)
    macro_conf = float(macro.get("regime_conf", 0.50))

    votes_agree  = 0
    votes_oppose = 0
    conf_sum     = 0.0

    # Technical — highest weight (primary signal)
    if tech_dir == primary:
        votes_agree += 1
        conf_sum += tech_conf * 1.5
    elif tech_dir == -primary:
        votes_oppose += 1
        conf_sum -= tech_conf * 0.5

    # Sentiment — medium weight (only if real news)
    if sent_real:
        if sent_dir == primary:
            votes_agree += 1
            conf_sum += sent_conf * 1.0
        elif sent_dir == -primary:
            votes_oppose += 1
            conf_sum -= sent_conf * 0.5

    # Macro — lower weight (lags price action)
    if macro_dir == primary:
        votes_agree += 1
        conf_sum += macro_conf * 0.4
    elif macro_dir == -primary:
        votes_oppose += 1
        conf_sum -= macro_conf * 0.4

    total_votes = votes_agree + votes_oppose

    # Base confidence by agreement tier
    if votes_agree == 3 and votes_oppose == 0:
        base  = 0.78
        agree = "FULL"
    elif votes_agree == 2 and votes_oppose == 0:
        base  = 0.65
        agree = "PARTIAL"
    elif votes_agree == 2 and votes_oppose == 1:
        base  = 0.58
        agree = "PARTIAL"
    elif votes_agree == 1 and votes_oppose == 0:
        base  = 0.52
        agree = "SOLO"
    elif votes_agree == 1 and votes_oppose == 1:
        base  = 0.46
        agree = "CONFLICT"
    else:
        base  = 0.50
        agree = "PARTIAL"

    # Fine-tune ±0.08 by normalised confidence sum
    norm_adj = float(np.clip(conf_sum / max(total_votes, 1) - 0.4, -0.08, 0.08))
    final    = round(float(np.clip(base + norm_adj, 0.35, 0.88)), 3)

    # Position size — scaled by conviction tier
    if agree == "CONFLICT" or final < min_confidence:
        pos_size = 0.0
    elif agree == "FULL":
        pos_size = round(min(final * 0.95, 0.88), 2)
    elif agree == "PARTIAL":
        pos_size = round(min(final * 0.78, 0.65), 2)
    else:  # SOLO
        pos_size = round(min(final * 0.60, 0.50), 2)

    logger.debug(
        f"  ConvictionGate: dir={direction} agree={agree} "
        f"votes={votes_agree}/{total_votes} conf={final:.3f} size={pos_size:.2f}"
    )

    return final, pos_size, agree


# ── Main gate entry point ─────────────────────────────────────────────────────

class ConvictionGate:
    """
    Stage 4: Combines agent outputs into a final tradeable signal.
    Pure Python — no LLM, fully deterministic and testable.
    """

    def __init__(self, min_confidence: float = 0.50):
        self.min_confidence = min_confidence

    def evaluate(
        self,
        macro: Dict,
        tech: Dict,
        sent: Dict,
    ) -> Dict:
        """
        Returns:
            direction:     "BUY" | "SELL" | "HOLD"
            confidence:    float
            position_size: float
            agreement:     str
            eff_macro:     str
        """
        direction = rule_based_direction(macro, tech, sent)
        confidence, position_size, agreement = compute_conviction(
            direction, macro, tech, sent, self.min_confidence
        )

        # Option 3: regime-conditional confidence floor
        # In a bearish regime, require higher conviction before acting.
        # Data shows BUY > SELL even when yield_z ~ -1.0, so bearish macro
        # alone is not sufficient justification for a low-confidence SELL.
        eff_label, _ = effective_macro_dir(macro)
        regime_floor = REGIME_MIN_CONFIDENCE.get(eff_label, self.min_confidence)
        effective_floor = max(self.min_confidence, regime_floor)

        if direction != "HOLD" and confidence < effective_floor:
            logger.debug(
                f"  ConvictionGate: conf={confidence:.3f} < "
                f"floor={effective_floor:.2f} (regime={eff_label}) → HOLD"
            )
            direction     = "HOLD"
            position_size = 0.0

        return {
            "direction":     direction,
            "confidence":    confidence,
            "position_size": position_size,
            "agreement":     agreement,
            "eff_macro":     eff_label,
        }

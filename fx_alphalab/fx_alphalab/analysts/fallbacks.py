"""
Deterministic fallbacks for every LLM analyst call.

If the hosted Llama is slow, down, or returns malformed JSON,
these produce a valid AnalystPacket with reduced confidence.
The system keeps running — never crashes due to LLM failure.
"""
import sys
from pathlib import Path

# Ensure the shared module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.analyst_packet import AnalystPacket


# ── Macro fallback ──────────────────────────────────────────────────────────

def macro_fallback(pair: str, macro_raw: dict) -> AnalystPacket:
    """
    Produces a macro packet without the LLM.
    Echoes the ML model's signal with discounted confidence.
    """
    regime_label = macro_raw.get("regime_label", "neutral")
    ml_signal = _regime_to_signal(regime_label)

    return AnalystPacket(
        agent="macro",
        pair=pair,
        timestamp_utc=macro_raw.get("timestamp_utc", ""),
        ml_signal=ml_signal,
        ml_conf=macro_raw.get("regime_conf", 0.5),
        ml_probs=macro_raw.get("regime_probs", {"BUY": 0.33, "SELL": 0.33, "HOLD": 0.34}),
        llm_signal=ml_signal,
        llm_conf=macro_raw.get("regime_conf", 0.5) * 0.7,  # discount for no LLM
        reasoning="LLM analyst unavailable. Signal reflects ML model output only.",
        key_drivers=[],
        risk_flags=["llm_fallback=True"],
        override_flag=False,
        override_reason=None,
        regime_label=regime_label,
        regime_conf=macro_raw.get("regime_conf", 0.5),
        macro_weight=0.5,  # neutral weight when LLM is down
        headline=f"{pair} — {ml_signal} · ML only (LLM unavailable)",
        confidence_bar=macro_raw.get("regime_conf", 0.5) * 0.7,
        agent_color="purple",
    )


# ── Technical fallback ──────────────────────────────────────────────────────

def tech_fallback(pair: str, tech_corrected: dict, macro_packet: AnalystPacket) -> AnalystPacket:
    """
    Produces a technical packet without the LLM.
    Uses the conviction-corrected signal with discounted confidence.
    """
    return AnalystPacket(
        agent="technical",
        pair=pair,
        timestamp_utc=tech_corrected.get("timestamp_utc", ""),
        ml_signal=tech_corrected.get("signal", "HOLD"),
        ml_conf=tech_corrected.get("confidence", 0.0),
        ml_probs={
            "BUY": tech_corrected.get("p_buy", 0.33),
            "SELL": tech_corrected.get("p_sell", 0.33),
            "HOLD": tech_corrected.get("p_hold", 0.34),
        },
        ml_raw_signal=tech_corrected.get("ml_raw_signal"),
        corrected=tech_corrected.get("corrected", False),
        correction_reason=tech_corrected.get("correction_reason"),
        conviction_sell=tech_corrected.get("conviction_sell"),
        conviction_buy=tech_corrected.get("conviction_buy"),
        llm_signal=tech_corrected.get("signal", "HOLD"),
        llm_conf=tech_corrected.get("confidence", 0.0) * 0.7,
        reasoning="LLM analyst unavailable. Signal reflects corrected ML output.",
        key_drivers=[],
        risk_flags=["llm_fallback=True"],
        override_flag=False,
        override_reason=None,
        regime_label=macro_packet.regime_label,
        regime_conf=macro_packet.regime_conf,
        macro_weight=macro_packet.macro_weight,
        headline=f"{pair} — {tech_corrected.get('signal', 'HOLD')} · ML only (LLM unavailable)",
        confidence_bar=tech_corrected.get("confidence", 0.0) * 0.7,
        agent_color="teal",
    )


# ── Sentiment fallback ──────────────────────────────────────────────────────

def sent_fallback(pair: str, sent_raw: dict, macro_packet: AnalystPacket) -> AnalystPacket:
    """
    Produces a sentiment packet without the LLM.
    Uses the raw ML signal with discounted confidence.
    """
    return AnalystPacket(
        agent="sentiment",
        pair=pair,
        timestamp_utc=sent_raw.get("timestamp_utc", ""),
        ml_signal=sent_raw.get("signal", "HOLD"),
        ml_conf=sent_raw.get("confidence", 0.0),
        ml_probs={
            "BUY": sent_raw.get("p_bullish", 0.33),
            "SELL": sent_raw.get("p_bearish", 0.33),
            "HOLD": sent_raw.get("p_neutral", 0.34),
        },
        llm_signal=sent_raw.get("signal", "HOLD"),
        llm_conf=sent_raw.get("confidence", 0.0) * 0.7,
        flow_dir="NEUTRAL",
        sent_dir="NEUTRAL",
        divergence=False,
        reasoning="LLM analyst unavailable. Signal reflects ML output only.",
        key_drivers=[],
        risk_flags=["llm_fallback=True"],
        override_flag=False,
        override_reason=None,
        regime_label=macro_packet.regime_label,
        regime_conf=macro_packet.regime_conf,
        macro_weight=macro_packet.macro_weight,
        headline=f"{pair} — {sent_raw.get('signal', 'HOLD')} · ML only (LLM unavailable)",
        confidence_bar=sent_raw.get("confidence", 0.0) * 0.7,
        agent_color="coral",
    )


# ── Orchestrator fallback ───────────────────────────────────────────────────

def orchestrator_fallback(
    pair: str,
    macro_pkt: AnalystPacket,
    tech_pkt: AnalystPacket,
    sent_pkt: AnalystPacket,
) -> dict:
    """
    Rule-based fallback for the orchestrator.
    Weighted majority vote: macro * macro_weight + tech * (1-weight)*0.6 + sent * (1-weight)*0.4
    """
    w = macro_pkt.macro_weight
    votes = {"BUY": 0.0, "SELL": 0.0, "HOLD": 0.0}

    # Macro vote weighted by macro_weight
    votes[macro_pkt.llm_signal] += w * macro_pkt.llm_conf

    # Technical vote (60% of non-macro weight)
    votes[tech_pkt.llm_signal] += (1 - w) * 0.6 * tech_pkt.llm_conf

    # Sentiment vote (40% of non-macro weight)
    votes[sent_pkt.llm_signal] += (1 - w) * 0.4 * sent_pkt.llm_conf

    direction = max(votes, key=votes.get)
    confidence = max(votes.values())

    # Agreement detection
    signals = [macro_pkt.llm_signal, tech_pkt.llm_signal, sent_pkt.llm_signal]
    unique = len(set(signals))
    if unique == 1:
        agreement = "full"
    elif unique == 2:
        agreement = "partial"
    else:
        agreement = "none"

    return {
        "pair": pair,
        "direction": direction,
        "position_size": 0.5 if agreement != "none" else 0.0,
        "confidence": round(min(confidence, 0.75), 3),
        "key_driver": "MACRO" if w >= 0.7 else "TECHNICAL",
        "narrative": "Orchestrator LLM unavailable. Used rule-based weighted vote fallback.",
        "risk_note": "LLM fallback active — verify signal manually before trading.",
        "agent_agreement": agreement,
        "suppressed_by_regime": False,
        "headline": f"{pair} — {direction} · weighted vote (LLM fallback)",
    }


# ── Helpers ──────────────────────────────────────────────────────────────────

def _regime_to_signal(regime_label: str) -> str:
    """Convert regime label to trading signal."""
    label = regime_label.lower()
    if "bull" in label:
        return "BUY"
    if "bear" in label:
        return "SELL"
    return "HOLD"


# ── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Fallbacks")
    print("=" * 60)

    # Test macro fallback
    macro_raw = {
        "regime_label": "bearish",
        "regime_conf": 0.65,
        "regime_probs": {"BUY": 0.15, "SELL": 0.65, "HOLD": 0.20},
        "timestamp_utc": "2026-05-05T14:00:00Z",
    }
    macro_pkt = macro_fallback("EURUSD", macro_raw)
    print(f"\n1. Macro fallback:")
    print(f"   Signal: {macro_pkt.llm_signal} (conf={macro_pkt.llm_conf:.2f})")
    print(f"   Risk flags: {macro_pkt.risk_flags}")
    assert macro_pkt.llm_signal == "SELL"
    assert "llm_fallback=True" in macro_pkt.risk_flags
    print("   ✅ Passed")

    # Test orchestrator fallback
    tech_pkt = AnalystPacket(
        agent="technical", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL", ml_conf=0.31, ml_probs={"BUY": 0.18, "SELL": 0.68, "HOLD": 0.14},
        llm_signal="SELL", llm_conf=0.65,
    )
    sent_pkt = AnalystPacket(
        agent="sentiment", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="HOLD", ml_conf=0.0, ml_probs={"BUY": 0.33, "SELL": 0.33, "HOLD": 0.34},
        llm_signal="HOLD", llm_conf=0.0,
    )
    orch_signal = orchestrator_fallback("EURUSD", macro_pkt, tech_pkt, sent_pkt)
    print(f"\n2. Orchestrator fallback:")
    print(f"   Direction: {orch_signal['direction']}, Agreement: {orch_signal['agent_agreement']}")
    print(f"   Headline: {orch_signal['headline']}")
    assert "direction" in orch_signal
    print("   ✅ Passed")

    print(f"\n{'='*60}")
    print("✅ All Fallback tests passed!")
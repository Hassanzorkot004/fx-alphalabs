"""
Sentiment LLM Analyst — interprets news flow and order flow data
in the context of the macro regime.

Runs in PARALLEL with technical (Stage 4).
Receives: raw XGBoost sentiment output + macro packet.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.analyst_packet import AnalystPacket
from shared.llm_client import get_llm_client, MODEL
from .fallbacks import sent_fallback


SENT_SYSTEM_PROMPT = """You are a senior sentiment and order-flow analyst for FX markets.
You interpret news flow, narrative pressure, and flow imbalance in the context of macro regime.

Rules:
- You receive XGBoost sentiment model output and raw news/flow features.
- Output ONLY valid JSON. No preamble, no markdown.
- nws_news_flow < 0.2 means the LOW-NEWS gate is active (very few articles).
  In this case, reduce llm_conf significantly and note it in risk_flags.
- flow_dir: your read of ORDER FLOW direction based on nws_flow_imbalance and nws_flow_accel.
  One of: BUY, SELL, NEUTRAL.
- sent_dir: your read of NARRATIVE direction based on nws_sent_signal and nws_sent_pressure.
  One of: BUY, SELL, NEUTRAL.
- When flow_dir and sent_dir diverge, follow flow_dir — order flow cannot be faked, narrative can.
  Set divergence to true in this case.
- reasoning: exactly 2 sentences. First — what the narrative picture shows.
  Second — what the flow picture shows and which dominates.
- override_flag: true only if you clearly disagree with the model's signal directionally.
- key_drivers: 3 feature names with values most responsible for this assessment.

Output ONLY this JSON:
{
  "llm_signal": "HOLD",
  "llm_conf": 0.25,
  "flow_dir": "NEUTRAL",
  "sent_dir": "NEUTRAL",
  "divergence": false,
  "reasoning": "News flow is minimal with only 2 articles this hour. Order flow shows slight buying but volume is too low to trust.",
  "key_drivers": ["nws_news_flow=0.15", "nws_flow_imbalance=0.08", "nws_sent_signal=0.03"],
  "risk_flags": ["low_news_flow", "sentiment_unreliable"],
  "override_flag": false,
  "override_reason": null,
  "headline": "EURUSD HOLD · low news flow · sentiment inconclusive"
}"""


def build_sent_user_message(pair: str, sent_raw: dict, macro_packet: AnalystPacket) -> str:
    """Build the user prompt with macro context + sentiment features."""
    f = sent_raw.get("features_snapshot", {})
    low_news = sent_raw.get("confidence", 0) == 0.0

    return f"""Pair: {pair}

MACRO REGIME CONTEXT:
  Regime: {macro_packet.regime_label}
  Macro weight: {macro_packet.macro_weight:.2f} (0.9=macro dominates, 0.3=defer to others)
  Macro reasoning: {macro_packet.reasoning}

XGBoost sentiment model output:
  Signal: {sent_raw.get('signal', 'HOLD')}
  P(bullish)={sent_raw.get('p_bullish', 0):.3f}
  P(bearish)={sent_raw.get('p_bearish', 0):.3f}
  P(neutral)={sent_raw.get('p_neutral', 0):.3f}
  Model confidence: {sent_raw.get('confidence', 0):.2f}
  LOW-NEWS gate active: {low_news}
  (When active, there are very few relevant articles — treat as NEUTRAL/unreliable)

News and flow features:
  nws_sent_signal: {f.get('nws_sent_signal', 0):.4f}       (overall sentiment score, -1 to +1)
  nws_sent_mom: {f.get('nws_sent_mom', 0):.4f}             (sentiment momentum)
  nws_sent_fast: {f.get('nws_sent_fast', 0):.4f}           (fast sentiment EMA)
  nws_sent_slow: {f.get('nws_sent_slow', 0):.4f}           (slow sentiment EMA)
  nws_news_flow: {f.get('nws_news_flow', 0):.4f}           (news volume — <0.2 = low news)
  nws_flow_accel: {f.get('nws_flow_accel', 0):.4f}         (flow acceleration)
  nws_flow_imbalance: {f.get('nws_flow_imbalance', 0):.4f}  (order flow imbalance, >0 = more buying)
  nws_sent_pressure: {f.get('nws_sent_pressure', 0):.4f}    (narrative pressure)
  nws_pressure_change: {f.get('nws_pressure_change', 0):.4f} (pressure change rate)
  nws_trend_strength: {f.get('nws_trend_strength', 0):.4f}  (trend persistence)

Interpretation:
  - nws_news_flow < 0.2: very few articles → LOW-NEWS → reduce confidence
  - nws_flow_imbalance > 0.10: more buyers than sellers → bullish flow
  - nws_flow_imbalance < -0.10: more sellers than buyers → bearish flow
  - nws_sent_signal > 0.10: narrative is bullish
  - nws_sent_signal < -0.10: narrative is bearish
  - flow_dir vs sent_dir divergence: trust flow over narrative

Produce the JSON now."""


def run_sent_analyst(pair: str, sent_raw: dict, macro_packet: AnalystPacket) -> AnalystPacket:
    """Run the sentiment LLM analyst."""
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": SENT_SYSTEM_PROMPT},
                {"role": "user", "content": build_sent_user_message(pair, sent_raw, macro_packet)},
            ],
            max_tokens=300,
            temperature=0.15,
        )
        parsed = json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"⚠️  Sentiment analyst LLM failed for {pair}: {e}")
        return sent_fallback(pair, sent_raw, macro_packet)

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
        llm_signal=parsed.get("llm_signal", sent_raw.get("signal", "HOLD")),
        llm_conf=float(parsed.get("llm_conf", 0.3)),
        flow_dir=parsed.get("flow_dir", "NEUTRAL"),
        sent_dir=parsed.get("sent_dir", "NEUTRAL"),
        divergence=parsed.get("divergence", False),
        reasoning=parsed.get("reasoning", ""),
        key_drivers=parsed.get("key_drivers", []),
        risk_flags=parsed.get("risk_flags", []),
        override_flag=parsed.get("override_flag", False),
        override_reason=parsed.get("override_reason"),
        regime_label=macro_packet.regime_label,
        regime_conf=macro_packet.regime_conf,
        macro_weight=macro_packet.macro_weight,
        headline=parsed.get("headline", f"{pair} — {sent_raw.get('signal', 'HOLD')}"),
        confidence_bar=float(parsed.get("llm_conf", 0.3)),
        agent_color="coral",
    )


# ── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from analysts.fallbacks import sent_fallback
    from shared.analyst_packet import AnalystPacket

    print("=" * 60)
    print("Testing Sentiment Analyst (fallback mode)")
    print("=" * 60)

    sent_raw = {
        "signal": "HOLD",
        "p_bullish": 0.41,
        "p_bearish": 0.29,
        "p_neutral": 0.30,
        "confidence": 0.0,
        "timestamp_utc": "2026-05-05T14:00:00Z",
        "features_snapshot": {
            "nws_sent_signal": 0.08,
            "nws_sent_mom": -0.12,
            "nws_sent_fast": 0.15,
            "nws_sent_slow": 0.22,
            "nws_news_flow": 0.15,
            "nws_flow_accel": -0.08,
            "nws_flow_imbalance": 0.04,
            "nws_sent_pressure": 0.11,
            "nws_pressure_change": -0.19,
            "nws_trend_strength": 0.18,
        },
    }

    macro_pkt = AnalystPacket(
        agent="macro", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL", ml_conf=0.65,
        ml_probs={"BUY": 0.15, "SELL": 0.65, "HOLD": 0.20},
        llm_signal="SELL", llm_conf=0.70,
        reasoning="Yield curve flattening signals risk-off.",
        regime_label="bearish", regime_conf=0.65, macro_weight=0.7,
    )

    pkt = sent_fallback("EURUSD", sent_raw, macro_pkt)
    print(f"\n1. Sentiment fallback:")
    print(f"   Signal: {pkt.llm_signal} | Flow: {pkt.flow_dir} | Sent: {pkt.sent_dir}")
    print(f"   Headline: {pkt.headline}")
    assert pkt.agent_color == "coral"
    print("   ✅ Passed")

    # Test LOW-NEWS detection in user message
    msg = build_sent_user_message("EURUSD", sent_raw, macro_pkt)
    assert "LOW-NEWS gate active: True" in msg
    print(f"\n2. LOW-NEWS detected in user message: ✅")
    print(f"   nws_news_flow=0.15 → correctly flagged as low news")

    print(f"\n{'='*60}")
    print("✅ Sentiment analyst tests passed")
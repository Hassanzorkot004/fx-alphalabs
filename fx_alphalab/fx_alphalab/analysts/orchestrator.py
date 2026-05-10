"""
Orchestrator LLM — synthesizes three analyst packets into a final signal.

Runs LAST (Stage 5). Receives only the macro, technical, and sentiment
packets — never raw features. Applies the soft regime gate and produces
the final BUY/SELL/HOLD with position size, narrative, and risk note.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.llm_client import get_llm_client, MODEL
from .fallbacks import orchestrator_fallback


ORCHESTRATOR_SYSTEM_PROMPT = """You are the head of an FX trading desk.
Three specialist analysts have submitted their reports. Synthesize them into a final trading signal.

Rules:
- Read all three reports carefully. Identify agreement and contradiction.
- Apply the soft regime gate: if macro_weight >= 0.7 and macro contradicts technical,
  reduce position_size to 0.5 but do NOT flip the direction unless macro_weight >= 0.9.
  Let the stronger conviction side win when macro_weight < 0.9.
- All three agents agree: full conviction, position_size = 1.0.
- Technical and macro agree, sentiment disagrees: proceed but flag it, position_size = 0.7.
- Technical and sentiment agree, macro contradicts: reduce position_size to 0.5 and flag it.
- No two agents agree: output HOLD, position_size = 0.0.
- override_flag on any analyst packet means an analyst overruled their own ML model. Mention it in the narrative.
- key_driver: which single agent's reasoning most determined your call. One of: MACRO, TECHNICAL, SENTIMENT.
- position_size: ONLY 0.0, 0.5, 0.7, or 1.0.
- narrative: 3 sentences maximum. Suitable for a trading dashboard. No jargon.
- risk_note: the single most important thing that could invalidate this signal in the next 4 hours.
- agent_agreement: "full" (all 3 same), "partial" (2 same), or "none" (all different).
- suppressed_by_regime: true if you reversed or suppressed a signal because of the macro regime gate.
- headline: short summary for the signal card. Format: "PAIR DIRECTION · reason"

Output ONLY this JSON:
{
  "direction": "SELL",
  "position_size": 0.7,
  "confidence": 0.65,
  "key_driver": "TECHNICAL",
  "narrative": "Three sentences max...",
  "risk_note": "The single biggest risk...",
  "agent_agreement": "partial",
  "suppressed_by_regime": false,
  "headline": "EURUSD SELL · technical breakdown with macro confirmation"
}"""


def build_orchestrator_message(pair, macro_pkt, tech_pkt, sent_pkt, headlines):
    """Build the orchestrator prompt from three analyst packets + headlines."""
    return f"""Pair: {pair}

━━━ MACRO ANALYST REPORT ━━━
  ML signal: {macro_pkt.ml_signal} (conf {macro_pkt.ml_conf:.2f})
  LLM signal: {macro_pkt.llm_signal} (conf {macro_pkt.llm_conf:.2f})
  Regime: {macro_pkt.regime_label} · macro_weight: {macro_pkt.macro_weight:.2f}
  Reasoning: {macro_pkt.reasoning}
  Key drivers: {', '.join(macro_pkt.key_drivers) if macro_pkt.key_drivers else 'none'}
  Risk flags: {', '.join(macro_pkt.risk_flags) if macro_pkt.risk_flags else 'none'}
  Override: {macro_pkt.override_flag}{' — ' + macro_pkt.override_reason if macro_pkt.override_flag else ''}

━━━ TECHNICAL ANALYST REPORT ━━━
  Raw ML signal: {tech_pkt.ml_raw_signal} → corrected to {tech_pkt.ml_signal}
  Correction reason: {tech_pkt.correction_reason or 'none'}
  LLM signal: {tech_pkt.llm_signal} (conf {tech_pkt.llm_conf:.2f})
  Conviction scores: SELL={tech_pkt.conviction_sell or 0:.2f}/4.0, BUY={tech_pkt.conviction_buy or 0:.2f}/4.0
  Reasoning: {tech_pkt.reasoning}
  Key drivers: {', '.join(tech_pkt.key_drivers) if tech_pkt.key_drivers else 'none'}
  Risk flags: {', '.join(tech_pkt.risk_flags) if tech_pkt.risk_flags else 'none'}
  Override: {tech_pkt.override_flag}{' — ' + tech_pkt.override_reason if tech_pkt.override_flag else ''}

━━━ SENTIMENT ANALYST REPORT ━━━
  ML signal: {sent_pkt.ml_signal} (conf {sent_pkt.ml_conf:.2f})
  LLM signal: {sent_pkt.llm_signal} (conf {sent_pkt.llm_conf:.2f})
  Flow direction: {sent_pkt.flow_dir} · Narrative direction: {sent_pkt.sent_dir}
  Divergence: {sent_pkt.divergence}
  Reasoning: {sent_pkt.reasoning}
  Key drivers: {', '.join(sent_pkt.key_drivers) if sent_pkt.key_drivers else 'none'}
  Risk flags: {', '.join(sent_pkt.risk_flags) if sent_pkt.risk_flags else 'none'}
  Override: {sent_pkt.override_flag}{' — ' + sent_pkt.override_reason if sent_pkt.override_flag else ''}

━━━ LIVE HEADLINES (last hour) ━━━
{chr(10).join(f'  - {h}' for h in headlines[:5]) if headlines else '  none available'}

Synthesize these three reports into your final decision. Produce the JSON now."""


def run_orchestrator(pair, macro_pkt, tech_pkt, sent_pkt, headlines):
    """Run the orchestrator LLM."""
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": build_orchestrator_message(
                    pair, macro_pkt, tech_pkt, sent_pkt, headlines)},
            ],
            max_tokens=350,
            temperature=0.15,
        )
        parsed = json.loads(response.choices[0].message.content.strip())
        parsed["pair"] = pair
        return parsed
    except Exception as e:
        print(f"⚠️  Orchestrator LLM failed for {pair}: {e}")
        return orchestrator_fallback(pair, macro_pkt, tech_pkt, sent_pkt)


# ── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from shared.analyst_packet import AnalystPacket
    from analysts.fallbacks import orchestrator_fallback

    print("=" * 60)
    print("Testing Orchestrator (fallback mode)")
    print("=" * 60)

    # Create three analyst packets simulating a real scenario
    macro_pkt = AnalystPacket(
        agent="macro", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL", ml_conf=0.65,
        ml_probs={"BUY": 0.15, "SELL": 0.65, "HOLD": 0.20},
        llm_signal="SELL", llm_conf=0.70,
        reasoning="Yield curve flattening (yield_z=-0.74) with VIX elevated. Risk-off supports USD strength.",
        key_drivers=["mac_yield_z=-0.74", "mac_vix_z=1.18", "mac_macro_strength=-0.42"],
        risk_flags=["vix_spiking", "fed_speak_tomorrow"],
        regime_label="bearish", regime_conf=0.65, macro_weight=0.7,
        headline="EURUSD SELL · risk-off regime · yield curve flattening",
        agent_color="purple",
    )

    tech_pkt = AnalystPacket(
        agent="technical", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL", ml_conf=0.31,
        ml_probs={"BUY": 0.18, "SELL": 0.68, "HOLD": 0.14},
        ml_raw_signal="SELL", corrected=False,
        conviction_sell=3.75, conviction_buy=0.50,
        llm_signal="SELL", llm_conf=0.65,
        reasoning="Price broke below SMA50 with expanding volume. Risk-off regime confirms trend continuation.",
        key_drivers=["roc1=-0.0025", "bb_pos=0.22", "sma50_slope=-0.0003"],
        risk_flags=["rsi_near_30", "atr_expanding"],
        regime_label="bearish", regime_conf=0.65, macro_weight=0.7,
        headline="EURUSD SELL · breakdown below SMA50 · regime confirms",
        agent_color="teal",
    )

    sent_pkt = AnalystPacket(
        agent="sentiment", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="HOLD", ml_conf=0.0,
        ml_probs={"BUY": 0.33, "SELL": 0.33, "HOLD": 0.34},
        llm_signal="HOLD", llm_conf=0.0,
        flow_dir="NEUTRAL", sent_dir="NEUTRAL", divergence=False,
        reasoning="Low news flow this hour. No clear directional signal from sentiment.",
        key_drivers=["nws_news_flow=0.15"],
        risk_flags=["low_news_flow"],
        regime_label="bearish", regime_conf=0.65, macro_weight=0.7,
        headline="EURUSD HOLD · low news · sentiment inconclusive",
        agent_color="coral",
    )

    # Test fallback
    signal = orchestrator_fallback("EURUSD", macro_pkt, tech_pkt, sent_pkt)
    print(f"\n1. Orchestrator fallback:")
    print(f"   Direction: {signal['direction']}")
    print(f"   Position size: {signal['position_size']}")
    print(f"   Agreement: {signal['agent_agreement']}")
    print(f"   Headline: {signal['headline']}")
    assert signal['direction'] in ('BUY', 'SELL', 'HOLD')
    assert signal['agent_agreement'] in ('full', 'partial', 'none')
    print("   ✅ Passed")

    # Test user message builder
    msg = build_orchestrator_message("EURUSD", macro_pkt, tech_pkt, sent_pkt, 
                                      ["ECB Lagarde speaks tomorrow", "Oil surges on supply fears"])
    print(f"\n2. User message built: {len(msg)} chars")
    assert "MACRO ANALYST REPORT" in msg
    assert "TECHNICAL ANALYST REPORT" in msg
    assert "SENTIMENT ANALYST REPORT" in msg
    assert "ECB Lagarde" in msg
    print("   ✅ Passed")

    # Test agreement detection in fallback
    # All three agree → full
    macro_pkt2 = AnalystPacket(agent="macro", pair="EURUSD", timestamp_utc="", 
                                ml_signal="BUY", ml_conf=0.7, ml_probs={},
                                llm_signal="BUY", llm_conf=0.8, macro_weight=0.5)
    tech_pkt2 = AnalystPacket(agent="technical", pair="EURUSD", timestamp_utc="",
                               ml_signal="BUY", ml_conf=0.6, ml_probs={},
                               llm_signal="BUY", llm_conf=0.7, macro_weight=0.5)
    sent_pkt2 = AnalystPacket(agent="sentiment", pair="EURUSD", timestamp_utc="",
                               ml_signal="BUY", ml_conf=0.5, ml_probs={},
                               llm_signal="BUY", llm_conf=0.6, macro_weight=0.5)
    signal2 = orchestrator_fallback("EURUSD", macro_pkt2, tech_pkt2, sent_pkt2)
    print(f"\n3. All agree test:")
    print(f"   Agreement: {signal2['agent_agreement']} (expected: full)")
    assert signal2['agent_agreement'] == 'full'
    print("   ✅ Passed")

    print(f"\n{'='*60}")
    print("✅ Orchestrator tests passed")
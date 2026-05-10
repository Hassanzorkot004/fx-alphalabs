"""
Technical LLM Analyst — interprets the TCN+LSTM model output
in the context of the macro regime.

Runs in PARALLEL with sentiment (Stage 4).
Receives: conviction-corrected ML output + macro packet.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.analyst_packet import AnalystPacket
from shared.llm_client import get_llm_client, MODEL
from .fallbacks import tech_fallback


TECH_SYSTEM_PROMPT = """You are a senior technical analyst specialising in FX markets.
You interpret price action and momentum indicators in the context of the macro regime.

Rules:
- You receive TCN+LSTM model output AFTER conviction gate correction, plus features and macro context.
- Output ONLY valid JSON. No preamble, no markdown.
- llm_signal: your final directional call after considering regime context.
- llm_conf: 0.0-1.0. Reduce confidence if regime and technicals conflict.
- reasoning: exactly 2 sentences. First — what the chart pattern shows. Second — how regime modifies the read.
- key_drivers: 3 indicator names with values most responsible for this signal.
- risk_flags: technical conditions that could invalidate the signal quickly.
- key_levels: nearest support and resistance as strings (e.g. "1.0820", "1.0865").
- override_flag: true only if your directional read clearly differs from the corrected ML signal.
- If correction_reason is set, factor in why the conviction gate fired.
- If symmetry_gate_active or tokyo_gate_active is true, mention it in risk_flags.

Regime adjustments:
- volatile-range: technicals unreliable, prefer HOLD unless signal is very strong.
- risk-off flight: trend-following signals more reliable than mean-reversion.
- range-carry: oscillator signals (RSI, BB) more reliable than momentum signals.
- risk-on trend: momentum signals (MACD, ROC) carry more weight.

Output ONLY this JSON:
{
  "llm_signal": "SELL",
  "llm_conf": 0.65,
  "reasoning": "Price broke below SMA50 with expanding volume. Risk-off regime confirms trend follow.",
  "key_drivers": ["roc1=-0.0025", "bb_pos=0.22", "sma50_slope=-0.0003"],
  "risk_flags": ["rsi_approaching_30", "atr_spiking"],
  "key_levels": {"support": "1.0820", "resistance": "1.0865"},
  "override_flag": false,
  "override_reason": null,
  "headline": "EURUSD SELL · trend breakdown · regime confirms"
}"""


def build_tech_user_message(pair: str, tech_corrected: dict, macro_packet: AnalystPacket) -> str:
    """Build the user prompt with macro context + conviction gate output + price features."""
    f = tech_corrected.get("features_snapshot", {})
    
    return f"""Pair: {pair}

MACRO REGIME CONTEXT (treat as ground truth this bar):
  Regime: {macro_packet.regime_label}
  Macro confidence: {macro_packet.regime_conf:.2f}
  Macro reasoning: {macro_packet.reasoning}
  Macro risk flags: {', '.join(macro_packet.risk_flags) if macro_packet.risk_flags else 'none'}
  Macro weight this bar: {macro_packet.macro_weight:.2f}
  (0.9 = macro dominates, 0.5 = balanced, 0.3 = defer to technicals)

CONVICTION GATE OUTPUT:
  Raw model signal: {tech_corrected.get('ml_raw_signal', '?')}
  Corrected signal: {tech_corrected.get('signal', '?')}
  Was corrected: {tech_corrected.get('corrected', False)}
  Reason: {tech_corrected.get('correction_reason') or 'no correction needed'}
  Conviction SELL score: {tech_corrected.get('conviction_sell', 0):.2f} / 4.0
  Conviction BUY score: {tech_corrected.get('conviction_buy', 0):.2f} / 4.0
  Symmetry gate active: {tech_corrected.get('symmetry_gate_active', False)}
  Tokyo gate active: {tech_corrected.get('tokyo_gate_active', False)}

TCN+LSTM model probabilities:
  P(BUY)={tech_corrected.get('p_buy', 0):.3f}
  P(SELL)={tech_corrected.get('p_sell', 0):.3f}
  P(HOLD)={tech_corrected.get('p_hold', 0):.3f}
  Model confidence: {tech_corrected.get('confidence', 0):.2f}

Price features (current bar):
  rsi14: {f.get('rsi14', 0):.1f}
  rsi28: {f.get('rsi28', 0):.1f}
  macd_hist: {f.get('macd_hist', 0):.5f}
  macd_norm: {f.get('macd_norm', 0):.4f}
  bb_pos: {f.get('bb_pos', 0):.3f}
  bb_width: {f.get('bb_width', 0):.4f}
  ema_cross: {f.get('ema_cross', 0):.5f}
  price_vs_ema50: {f.get('price_vs_ema50', 0):.5f}
  sma10_slope: {f.get('sma10_slope', 0):.5f}
  atr_pct: {f.get('atr_pct', 0):.4f}
  vol_ratio: {f.get('vol_ratio', 0):.3f}
  roc1: {f.get('roc1', 0):.5f}
  roc5: {f.get('roc5', 0):.5f}

Session indicators: tokyo={f.get('is_tokyo',0)} london={f.get('is_london',0)} ny={f.get('is_newyork',0)} overlap={f.get('is_overlap',0)}

Produce the JSON now."""


def run_tech_analyst(pair: str, tech_corrected: dict, macro_packet: AnalystPacket) -> AnalystPacket:
    """Run the technical LLM analyst."""
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": TECH_SYSTEM_PROMPT},
                {"role": "user", "content": build_tech_user_message(pair, tech_corrected, macro_packet)},
            ],
            max_tokens=300,
            temperature=0.15,
        )
        parsed = json.loads(response.choices[0].message.content.strip())
    except Exception as e:
        print(f"⚠️  Technical analyst LLM failed for {pair}: {e}")
        return tech_fallback(pair, tech_corrected, macro_packet)

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
        corrected=tech_corrected.get("corrected"),
        correction_reason=tech_corrected.get("correction_reason"),
        conviction_sell=tech_corrected.get("conviction_sell"),
        conviction_buy=tech_corrected.get("conviction_buy"),
        llm_signal=parsed.get("llm_signal", tech_corrected.get("signal", "HOLD")),
        llm_conf=float(parsed.get("llm_conf", 0.5)),
        reasoning=parsed.get("reasoning", ""),
        key_drivers=parsed.get("key_drivers", []),
        risk_flags=parsed.get("risk_flags", []),
        override_flag=parsed.get("override_flag", False),
        override_reason=parsed.get("override_reason"),
        regime_label=macro_packet.regime_label,
        regime_conf=macro_packet.regime_conf,
        macro_weight=macro_packet.macro_weight,
        headline=parsed.get("headline", f"{pair} — {tech_corrected.get('signal', 'HOLD')}"),
        confidence_bar=float(parsed.get("llm_conf", 0.5)),
        agent_color="teal",
        key_levels=parsed.get("key_levels"),
    )


# ── Quick self-test ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    from analysts.fallbacks import tech_fallback
    from shared.analyst_packet import AnalystPacket

    print("=" * 60)
    print("Testing Technical Analyst (fallback mode)")
    print("=" * 60)

    tech_corrected = {
        "signal": "SELL",
        "ml_raw_signal": "SELL",
        "corrected": False,
        "correction_reason": None,
        "conviction_sell": 3.75,
        "conviction_buy": 0.50,
        "symmetry_gate_active": False,
        "tokyo_gate_active": False,
        "p_buy": 0.18,
        "p_sell": 0.68,
        "p_hold": 0.14,
        "confidence": 0.31,
        "timestamp_utc": "2026-05-05T14:00:00Z",
        "features_snapshot": {
            "rsi14": 38.2, "rsi28": 42.1,
            "macd_hist": -0.0012, "macd_norm": -0.34,
            "bb_pos": 0.22, "bb_width": 0.0045,
            "ema_cross": -0.0008, "price_vs_ema50": -0.0015,
            "sma10_slope": -0.0003, "atr_pct": 0.0021,
            "vol_ratio": 1.34, "roc1": -0.0025, "roc5": -0.0041,
            "is_tokyo": 0, "is_london": 1, "is_newyork": 0, "is_overlap": 1,
        },
    }

    macro_pkt = AnalystPacket(
        agent="macro", pair="EURUSD", timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL", ml_conf=0.65,
        ml_probs={"BUY": 0.15, "SELL": 0.65, "HOLD": 0.20},
        llm_signal="SELL", llm_conf=0.70,
        reasoning="Yield curve flattening signals risk-off.",
        key_drivers=["mac_yield_z=-0.74"],
        regime_label="bearish", regime_conf=0.65, macro_weight=0.7,
    )

    pkt = tech_fallback("EURUSD", tech_corrected, macro_pkt)
    print(f"\n1. Tech fallback:")
    print(f"   Signal: {pkt.llm_signal} | Conviction: SELL={pkt.conviction_sell}, BUY={pkt.conviction_buy}")
    print(f"   Headline: {pkt.headline}")
    assert pkt.agent_color == "teal"
    print("   ✅ Passed")

    print(f"\n{'='*60}")
    print("✅ Technical analyst tests passed")
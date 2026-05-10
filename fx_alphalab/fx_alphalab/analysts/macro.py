"""
Macro LLM Analyst — interprets the KMeans regime model output.

Runs FIRST in the pipeline (Stage 3). Its output gates everything:
  - regime_label tells downstream agents what regime we're in
  - macro_weight tells them how much to weight the macro signal

The LLM receives the raw KMeans output + macro features.
It returns a structured AnalystPacket with reasoning, key drivers,
risk flags, and an optional override if the features contradict the model.
"""
import json
import sys
from pathlib import Path

# Ensure shared module is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.analyst_packet import AnalystPacket
from shared.llm_client import get_llm_client, MODEL
from .fallbacks import macro_fallback


# ── System Prompt ───────────────────────────────────────────────────────────

MACRO_SYSTEM_PROMPT = """You are a senior macro analyst at an FX trading desk.
You interpret macro regime data and explain what it means for currency direction.

Rules:
- You receive the output of a KMeans regime model and the raw macro features.
- Output ONLY valid JSON. No preamble, no markdown, no code fences.
- llm_signal: BUY, SELL, or HOLD. BUY means the base currency strengthens vs USD.
- llm_conf: your own confidence 0.0 to 1.0 in the direction.
- override_flag: true ONLY if the raw features clearly contradict the model's regime label.
  For example: model says "bullish" but yield_z is strongly negative with VIX spiking.
- reasoning: exactly 2 sentences. First sentence — what the regime means for macro conditions.
  Second sentence — what it implies for this pair's direction.
- key_drivers: list exactly 3 feature names WITH their values most responsible for this regime.
  Format: "feature_name=value" (e.g. "mac_yield_z=-0.74")
- risk_flags: features that could invalidate this regime in the next 4-8 hours.
  Examples: "vix_spiking", "cb_speech_today", "yield_curve_inverting_fast"
- macro_weight: how much should downstream agents weight the macro signal this bar?
  0.7 = extreme risk-off flight (VIX > 30 AND yield_z < -1.0)
  0.5 = moderate risk-off or trending (macro is important but technicals also matter)
  0.4 = range-carry or mild regime (macro provides backdrop, technicals lead)
  0.2 = volatile/choppy range (macro unreliable, defer to technicals)
- headline: one short line summarizing this for a trading dashboard.
  Format: "PAIR DIRECTION · key reason · regime"

Output ONLY this JSON structure:
{
  "llm_signal": "BUY",
  "llm_conf": 0.70,
  "reasoning": "Two sentences...",
  "key_drivers": ["mac_yield_z=-0.74", "mac_vix_z=1.18", "mac_cb_tone_z=-0.55"],
  "risk_flags": ["vix_spiking", "fed_speak_today"],
  "override_flag": false,
  "override_reason": null,
  "macro_weight": 0.7,
  "headline": "EURUSD SELL · yield curve flattening · risk-off"
}"""


# ── User Message Builder ─────────────────────────────────────────────────────

def build_macro_user_message(pair: str, macro_raw: dict) -> str:
    """
    Builds the user prompt from raw macro model output.
    Injects all feature values so the LLM can reason about specific numbers.
    """
    f = macro_raw.get("mac_features", {})
    p = macro_raw.get("regime_probs", {})
    
    return f"""Pair: {pair}

KMeans regime model output:
  Regime label: {macro_raw.get('regime_label', 'unknown')}
  Model confidence: {macro_raw.get('regime_conf', 0):.2f}
  Regime probabilities: 
    bullish={p.get('bullish', 0):.2f}
    neutral={p.get('neutral', 0):.2f}
    bearish={p.get('bearish', 0):.2f}

Raw macro features (these drove the model output):
  mac_yield_z: {f.get('mac_yield_z', 0):.3f}        (yield spread 10Y-2Y z-score; >0=steepening/USD bullish)
  mac_yield_mom: {f.get('mac_yield_mom', 0):.3f}     (5-bar yield momentum)
  mac_yield_accel: {f.get('mac_yield_accel', 0):.3f} (yield momentum acceleration)
  mac_cb_tone_z: {f.get('mac_cb_tone_z', 0):.3f}     (central bank tone differential z-score)
  mac_cb_shock_z: {f.get('mac_cb_shock_z', 0):.3f}   (CB surprise magnitude)
  mac_macro_strength: {f.get('mac_macro_strength', 0):.3f}  (composite macro indicator)
  mac_vix_global: {f.get('mac_vix_global', 0):.2f}   (VIX level, raw)
  mac_vix_z: {f.get('mac_vix_z', 0):.3f}             (VIX z-score; >0=above normal fear)
  pair_carry_signal: {f.get('pair_carry_signal', 0):.3f}  (pair-specific yield differential)

Interpretation guide:
  - yield_z > 0: yield curve steepening → USD bullish (higher US yields attract capital)
  - yield_z < 0: yield curve flattening/inverting → risk-off, USD may strengthen as safe haven
  - vix_z > 1.0: fear above normal → risk-off, JPY/USD bid
  - cb_tone_z > 0: hawkish central bank → currency positive
  - macro_strength > 0: broad macro strength → risk-on

Produce the JSON now."""



# ── Helpers ──────────────────────────────────────────────────────────────────

def _regime_to_signal(regime_label: str) -> str:
    """Convert regime label to trading signal."""
    label = regime_label.lower()
    if "bull" in label:
        return "BUY"
    if "bear" in label:
        return "SELL"
    return "HOLD"


# ── Main Analyst Function ────────────────────────────────────────────────────

def run_macro_analyst(pair: str, macro_raw: dict) -> AnalystPacket:
    """
    Run the macro LLM analyst on one bar.
    
    Args:
        pair: currency pair string (e.g. "EURUSD")
        macro_raw: raw output dict from macro_agent.predict_live()
    
    Returns:
        AnalystPacket with LLM analysis (or fallback if LLM fails)
    """
    try:
        client = get_llm_client()
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": MACRO_SYSTEM_PROMPT},
                {"role": "user", "content": build_macro_user_message(pair, macro_raw)},
            ],
            max_tokens=300,
            temperature=0.15,
        )
        
        raw_text = response.choices[0].message.content.strip()
        
        # Parse JSON — the LLM should return only JSON
        parsed = json.loads(raw_text)
        
    except (json.JSONDecodeError, Exception) as e:
        # LLM failed or returned bad JSON — use deterministic fallback
        print(f"⚠️  Macro analyst LLM failed for {pair}: {e}")
        return macro_fallback(pair, macro_raw)

    # Convert regime label to signal
    ml_signal = _regime_to_signal(macro_raw.get("regime_label", "neutral"))

    return AnalystPacket(
        # Identity
        agent="macro",
        pair=pair,
        timestamp_utc=macro_raw.get("timestamp_utc", ""),
        
        # Frozen ML output
        ml_signal=ml_signal,
        ml_conf=macro_raw.get("regime_conf", 0.5),
        ml_probs=macro_raw.get("regime_probs", {}),
        
        # LLM analyst output
        llm_signal=parsed.get("llm_signal", ml_signal),
        llm_conf=float(parsed.get("llm_conf", 0.5)),
        reasoning=parsed.get("reasoning", ""),
        key_drivers=parsed.get("key_drivers", []),
        risk_flags=parsed.get("risk_flags", []),
        override_flag=parsed.get("override_flag", False),
        override_reason=parsed.get("override_reason"),
        
        # Macro context
        regime_label=macro_raw.get("regime_label", "neutral"),
        regime_conf=macro_raw.get("regime_conf", 0.5),
        macro_weight=float(parsed.get("macro_weight", 0.5)),
        
        # Frontend
        headline=parsed.get("headline", f"{pair} — {ml_signal}"),
        confidence_bar=float(parsed.get("llm_conf", 0.5)),
        agent_color="purple",
    )


# ── Quick self-test (runs without LLM — only tests parsing + fallback) ──────
if __name__ == "__main__":
    print("=" * 60)
    print("Testing Macro Analyst (fallback mode — no LLM call)")
    print("=" * 60)

    # Simulate a real macro output
    macro_raw = {
        "regime_label": "bearish",
        "regime_conf": 0.65,
        "regime_probs": {"bullish": 0.10, "neutral": 0.25, "bearish": 0.65},
        "mac_features": {
            "mac_yield_z": -0.74,
            "mac_yield_mom": -0.031,
            "mac_yield_accel": -0.012,
            "mac_cb_tone_z": -0.55,
            "mac_cb_shock_z": 0.12,
            "mac_macro_strength": -0.42,
            "mac_vix_global": 22.3,
            "mac_vix_z": 1.18,
            "pair_carry_signal": -0.15,
        },
        "timestamp_utc": "2026-05-05T14:00:00Z",
    }

    # Test the user message builder
    msg = build_macro_user_message("EURUSD", macro_raw)
    print("\n1. User message built:")
    print(f"   Length: {len(msg)} chars")
    assert "mac_yield_z: -0.740" in msg
    assert "bearish" in msg
    print("   ✅ Passed")

    # Test the fallback (simulates LLM failure)
    pkt = macro_fallback("EURUSD", macro_raw)
    print(f"\n2. Macro fallback packet:")
    print(f"   Agent: {pkt.agent} | Color: {pkt.agent_color}")
    print(f"   ML Signal: {pkt.ml_signal} | LLM Signal: {pkt.llm_signal}")
    print(f"   Headline: {pkt.headline}")
    print(f"   Risk flags: {pkt.risk_flags}")
    assert pkt.llm_signal == "SELL"
    assert "llm_fallback=True" in pkt.risk_flags
    print("   ✅ Passed")

    # Test round-trip serialization
    d = pkt.to_dict()
    restored = AnalystPacket.from_dict(d)
    print(f"\n3. Round-trip serialization:")
    print(f"   Original: {pkt.headline}")
    print(f"   Restored: {restored.headline}")
    assert restored.headline == pkt.headline
    print("   ✅ Passed")

    print(f"\n{'='*60}")
    print("✅ Macro analyst tests passed (fallback mode)")
    print("   To test with LLM: call run_macro_analyst('EURUSD', macro_raw)")
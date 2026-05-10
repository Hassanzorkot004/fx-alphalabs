"""
AnalystPacket — the shared data contract for every LLM analyst.

Every agent (macro, technical, sentiment) produces one of these.
The orchestrator consumes three of them.
The frontend receives all three + the orchestrator's final output.
"""
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional, List


@dataclass
class AnalystPacket:
    """
    Universal packet returned by every LLM analyst.

    Identity:
        agent: which analyst produced this (macro/technical/sentiment)
        pair: currency pair (e.g. "EURUSD")
        timestamp_utc: ISO timestamp of this bar

    Frozen ML output (never modified after ML inference):
        ml_signal: BUY/SELL/HOLD from the raw model
        ml_conf: model's confidence 0-1
        ml_probs: full probability dict {"BUY": x, "SELL": y, "HOLD": z}

    Conviction gate (technical agent only, None for others):
        ml_raw_signal: what the model said before correction
        corrected: True if the corrector changed the signal
        correction_reason: why it was corrected
        conviction_sell: SELL conviction score 0-4
        conviction_buy: BUY conviction score 0-4

    LLM analyst output:
        llm_signal: the analyst's directional call
        llm_conf: analyst's confidence 0-1
        reasoning: 2-3 sentence explanation
        key_drivers: list of "feature=value" strings
        risk_flags: list of warning strings
        override_flag: True if LLM disagrees with ML model
        override_reason: why the LLM overrode
        headline: one-line summary for dashboard

    Macro context (set by macro analyst, copied to others):
        regime_label: bullish/neutral/bearish
        regime_conf: regime confidence 0-1
        macro_weight: how much macro matters this bar 0-1

    Frontend display:
        confidence_bar: same as llm_conf, for UI
        agent_color: purple/teal/coral for consistent visuals
    """

    # ── Identity ──────────────────────────────────────────────────────
    agent: Literal["macro", "technical", "sentiment"]
    pair: str
    timestamp_utc: str

    # ── Frozen ML output ──────────────────────────────────────────────
    ml_signal: Literal["BUY", "SELL", "HOLD"]
    ml_conf: float
    ml_probs: dict  # {"BUY": 0.x, "SELL": 0.y, "HOLD": 0.z}

    # ── Conviction gate (technical only) ──────────────────────────────
    ml_raw_signal: Optional[str] = None
    corrected: Optional[bool] = None
    correction_reason: Optional[str] = None
    conviction_sell: Optional[float] = None
    conviction_buy: Optional[float] = None

    # ── LLM analyst output ────────────────────────────────────────────
    llm_signal: Literal["BUY", "SELL", "HOLD"] = "HOLD"
    llm_conf: float = 0.0
    reasoning: str = ""
    key_drivers: List[str] = field(default_factory=list)
    risk_flags: List[str] = field(default_factory=list)
    override_flag: bool = False
    override_reason: Optional[str] = None

    # ── Sentiment-specific fields ─────────────────────────────────────
    flow_dir: str = "NEUTRAL"
    sent_dir: str = "NEUTRAL"
    divergence: bool = False

    # ── Macro context ─────────────────────────────────────────────────
    regime_label: str = "neutral"
    regime_conf: float = 0.0
    macro_weight: float = 0.5

    # ── Frontend display ──────────────────────────────────────────────
    headline: str = ""
    confidence_bar: float = 0.0
    agent_color: str = "gray"
    key_levels: Optional[dict] = None  # {"support": "...", "resistance": "..."}

    def to_dict(self) -> dict:
        """Convert to dict for JSON serialization, Parquet storage, and WebSocket broadcast."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AnalystPacket":
        """Reconstruct from a dict (for loading from Parquet/history)."""
        return cls(**data)


# ── Quick self-test ────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Testing AnalystPacket")
    print("=" * 60)

    # Create a macro packet
    macro = AnalystPacket(
        agent="macro",
        pair="EURUSD",
        timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL",
        ml_conf=0.65,
        ml_probs={"BUY": 0.15, "SELL": 0.65, "HOLD": 0.20},
        llm_signal="SELL",
        llm_conf=0.70,
        reasoning="Yield curve is flattening (yield_z=-0.74), signaling risk-off. "
                   "This supports a bearish USD outlook against EUR.",
        key_drivers=["mac_yield_z=-0.74", "mac_vix_z=1.18", "mac_cb_tone_z=-0.55"],
        risk_flags=["event_flag=tomorrow_ECB_speech", "vix_spiking"],
        regime_label="bearish",
        regime_conf=0.65,
        macro_weight=0.7,
        headline="EURUSD SELL · yield spread widening · risk-off regime",
        confidence_bar=0.70,
        agent_color="purple",
    )

    # Create a technical packet (with conviction data)
    tech = AnalystPacket(
        agent="technical",
        pair="EURUSD",
        timestamp_utc="2026-05-05T14:00:00Z",
        ml_signal="SELL",
        ml_conf=0.31,
        ml_probs={"BUY": 0.18, "SELL": 0.68, "HOLD": 0.14},
        ml_raw_signal="SELL",
        corrected=False,
        correction_reason=None,
        conviction_sell=3.75,
        conviction_buy=0.50,
        llm_signal="SELL",
        llm_conf=0.65,
        reasoning="Price broke below the 50-bar SMA with expanding volume. "
                   "In this risk-off regime, trend signals carry more weight.",
        key_drivers=["roc1=-0.0025", "bb_pos=0.22", "sma50_slope=-0.0003"],
        risk_flags=["rsi_approaching_30", "atr_spiking"],
        regime_label="bearish",
        regime_conf=0.65,
        macro_weight=0.7,
        headline="EURUSD SELL · trend breakdown · regime confirms",
        confidence_bar=0.65,
        agent_color="teal",
        key_levels={"support": "1.0820", "resistance": "1.0865"},
    )

    # Test serialization
    macro_dict = macro.to_dict()
    tech_dict = tech.to_dict()

    print(f"\n1. Macro packet serialized: {len(str(macro_dict))} chars")
    print(f"   Headline: {macro_dict['headline']}")
    print(f"   Key drivers: {macro_dict['key_drivers']}")

    print(f"\n2. Technical packet serialized: {len(str(tech_dict))} chars")
    print(f"   Conviction: SELL={tech_dict['conviction_sell']}, BUY={tech_dict['conviction_buy']}")
    print(f"   Corrected: {tech_dict['corrected']}")

    # Test round-trip
    macro_restored = AnalystPacket.from_dict(macro_dict)
    print(f"\n3. Round-trip: {macro_restored.agent} → {macro_restored.headline}")
    assert macro_restored.ml_signal == "SELL"
    assert macro_restored.llm_conf == 0.70

    print(f"\n{'='*60}")
    print("✅ All AnalystPacket tests passed!")
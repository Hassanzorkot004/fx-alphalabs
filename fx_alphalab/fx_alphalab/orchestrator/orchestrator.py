"""
orchestrator/orchestrator.py
────────────────────────────────────────────────────────────────────────────
Stage 5 of 5 — LLM Orchestrator

ARCHITECTURE v4 (5-stage hybrid pipeline):

  Stage 1: MacroAgent    (KMeans)    → regime + mac_features
  Stage 2: TechnicalAgent (TCN+LSTM) → direction + probabilities
  Stage 3: SentimentAgent (XGBoost)  → sentiment + probabilities
  Stage 4: ConvictionGate (Python)   → final direction + confidence
  Stage 5: Orchestrator  (LLM)       → per-agent analyst text + reasoning

  The LLM is used ONLY for explanation — never for decisions.
  All decisions are made deterministically in Stages 1-4.

PER-AGENT LLM ANALYST CALLS:
  Each agent gets a focused LLM call that produces a short analyst report
  explaining that agent's output in plain English. These reports are:
    - Shown in the UI "Analyst Breakdown" section per agent
    - Injected into the final orchestrator prompt for richer reasoning

RAG INTEGRATION:
  The orchestrator receives pre-retrieved headlines from NewsRAG
  (semantically relevant to the current signal context) rather than
  the 5 most recent RSS articles.

LLM PRIORITY:
  1. Groq API (llama-3.3-70b-versatile — fast, expert)
  2. Ollama local (llama3.1:latest — fallback)
  3. Rule-based text (if both unavailable)
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from fx_alphalab.agents.conviction_gate import effective_macro_dir

try:
    import ollama as ollama_client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    logger.warning("groq not installed — run: pip install groq")


# ── JSON parsing helper ───────────────────────────────────────────────────────

def _parse_json(text: str) -> Optional[Dict]:
    if not text:
        return None
    try:
        return json.loads(text.strip())
    except Exception:
        pass
    for pattern in [r'\{[^{}]+\}', r'\{.*?\}']:
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except Exception:
                pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# PER-AGENT ANALYST PROMPTS
# Each agent gets a short, focused prompt that produces a 2-3 sentence
# analyst report explaining that agent's output.
# ══════════════════════════════════════════════════════════════════════════════

# ── Macro analyst ─────────────────────────────────────────────────────────────

MACRO_ANALYST_SYSTEM = """You are a macro economist specialising in G10 FX.
Explain the current macro regime reading in 2 sentences for a trader.
Be specific — reference the actual yield_z, vix_z, and macro_strength values.
Output ONLY this JSON:
{"analyst_text": "<2 sentences>", "key_feature": "<most important macro feature name>", "override": false}
Set override=true if the regime label seems inconsistent with the raw data."""


def _macro_analyst_prompt(macro: Dict, pair: str) -> str:
    feats   = macro.get("mac_features", {})
    regime  = macro.get("regime_label", "neutral")
    eff, _  = effective_macro_dir(macro)
    probs   = macro.get("regime_probs", {})

    note = ""
    if eff != regime:
        note = f" [OVERRIDDEN to {eff.upper()} by yield_z threshold]"

    return f"""Pair: {pair.replace('=X','')} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

MACRO REGIME: {regime.upper()}{note}
Effective regime: {eff.upper()}
Regime probs: bullish={probs.get('bullish',0):.2f} neutral={probs.get('neutral',0):.2f} bearish={probs.get('bearish',0):.2f}

Key features:
  mac_yield_z={feats.get('mac_yield_z',0):+.3f}  (yield curve z-score; >0=steeper=USD bullish)
  mac_macro_strength={feats.get('mac_macro_strength',0):+.3f}
  mac_vix_z={feats.get('mac_vix_z',0):+.3f}  (VIX z-score; >0=elevated risk-off)
  mac_cb_tone_z={feats.get('mac_cb_tone_z',0):+.3f}  (CB tone; >0=hawkish)
  mac_cb_guidance_z={feats.get('mac_cb_guidance_z',0):+.3f}  (forward guidance)
  pair_carry_signal={feats.get('pair_carry_signal',0):+.3f}

Explain what this macro regime means for {pair.replace('=X','')} in 2 sentences."""


# ── Technical analyst ─────────────────────────────────────────────────────────

TECH_ANALYST_SYSTEM = """You are a technical analyst specialising in FX.
Explain the technical signal in 2 sentences for a trader.
Reference the actual RSI, MACD, Bollinger Band position, and model probabilities.
Output ONLY this JSON:
{"analyst_text": "<2 sentences>", "key_feature": "<most important technical feature>", "override": false}
Set override=true if the signal seems unreliable (high uncertainty, low confidence)."""


def _tech_analyst_prompt(tech: Dict, pair: str, last_bar: Dict) -> str:
    rsi14   = last_bar.get("rsi14", 0.5) * 100
    bb_pos  = last_bar.get("bb_pos", 0.5)
    macd_h  = last_bar.get("macd_hist", 0.0)

    return f"""Pair: {pair.replace('=X','')} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

TECHNICAL SIGNAL: {tech.get('signal','HOLD')}
P(BUY)={tech.get('p_buy',0):.3f}  P(HOLD)={tech.get('p_hold',0):.3f}  P(SELL)={tech.get('p_sell',0):.3f}
model_confidence={tech.get('confidence',0):.3f}  uncertainty={tech.get('uncertainty',1):.3f}

Key indicators (last bar):
  RSI(14)={rsi14:.1f}  (>70=overbought, <30=oversold)
  BB_position={bb_pos:.2f}  (0=lower band, 1=upper band)
  MACD_hist={macd_h:.6f}  (>0=bullish momentum, <0=bearish)

Explain what the technical model is seeing in 2 sentences."""


# ── Sentiment analyst ─────────────────────────────────────────────────────────

SENT_ANALYST_SYSTEM = """You are a news sentiment analyst specialising in FX.
Explain the current news sentiment reading in 2 sentences for a trader.
Reference the actual sentiment score and article count.
Output ONLY this JSON:
{"analyst_text": "<2 sentences>", "key_feature": "<most important sentiment feature>", "override": false}
Set override=true if sentiment is LOW-NEWS (insufficient coverage)."""


def _sent_analyst_prompt(sent: Dict, headlines: List[str], pair: str) -> str:
    low_news = "LOW-NEWS" in sent.get("signal", "")
    hl_str   = "\n".join(f"  - {h}" for h in headlines[:4]) if headlines else "  - No headlines"

    return f"""Pair: {pair.replace('=X','')} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

SENTIMENT SIGNAL: {sent.get('signal','HOLD')}
P(bullish)={sent.get('p_buy',0):.3f}  P(neutral)={sent.get('p_hold',0):.3f}  P(bearish)={sent.get('p_sell',0):.3f}
confidence={sent.get('confidence',0):.3f}
{"⚠ LOW-NEWS: fewer than 2 relevant articles — sentiment unreliable" if low_news else ""}

Retrieved headlines (RAG-selected, most relevant):
{hl_str}

Explain what the news sentiment is signalling in 2 sentences."""


# ── Final orchestrator prompt ─────────────────────────────────────────────────

ORCHESTRATOR_SYSTEM = """You are a senior FX trader with 15 years of experience on EUR/USD, GBP/USD and USD/JPY.

The trading DIRECTION has already been decided by a quantitative pipeline.
You have received analyst reports from three specialist agents (Macro, Technical, Sentiment).
Your job is to synthesise these into a final expert reasoning statement.

Rules:
- Base reasoning ONLY on the data provided — do not invent facts
- Be specific: reference actual values (yield_z, P values, RSI, etc.)
- 2 sentences maximum for reasoning
- Identify the single most important driver
- Note the main risk to this trade

Output ONLY this JSON:
{
  "reasoning": "<2 sentences synthesising the three agent reports>",
  "key_driver": "<TECHNICAL or MACRO or SENTIMENT or NEWS>",
  "risk_note": "<specific risk based on the data>"
}"""


def _orchestrator_prompt(
    pair: str,
    direction: str,
    confidence: float,
    agreement: str,
    macro_report: str,
    tech_report: str,
    sent_report: str,
    headlines: List[str],
) -> str:
    hl_str = "\n".join(f"  - {h}" for h in headlines[:5]) if headlines else "  - No headlines"

    return f"""Pair: {pair.replace('=X','')} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

DECIDED DIRECTION: {direction}  (confidence={confidence:.2f}, agreement={agreement})

━━━ MACRO ANALYST REPORT ━━━
{macro_report or "No macro report available."}

━━━ TECHNICAL ANALYST REPORT ━━━
{tech_report or "No technical report available."}

━━━ SENTIMENT ANALYST REPORT ━━━
{sent_report or "No sentiment report available."}

━━━ RETRIEVED HEADLINES (RAG) ━━━
{hl_str}

Synthesise the above into a final 2-sentence reasoning for {direction} on {pair.replace('=X','')}.
Output only the JSON."""


# ══════════════════════════════════════════════════════════════════════════════
# Orchestrator class
# ══════════════════════════════════════════════════════════════════════════════

class Orchestrator:

    def __init__(self, cfg: dict):
        llm          = cfg["llm"]
        self.model   = llm.get("model", "llama-3.3-70b-versatile")
        self.host    = llm.get("host", "http://localhost:11434")
        self.temp    = llm.get("temperature", 0.1)
        self.max_tok = llm.get("max_tokens", 512)

        # Init Groq
        self.groq_client = None
        groq_key = llm.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")
        if GROQ_AVAILABLE and groq_key and groq_key not in ("", "YOUR_GROQ_KEY_HERE"):
            try:
                self.groq_client = Groq(api_key=groq_key)
                logger.info(f"  Groq client initialized ✓ model={self.model}")
            except Exception as e:
                logger.warning(f"  Groq init failed: {e}")
        else:
            logger.info("  Groq unavailable — will use Ollama or rule-based fallback")

    # ── LLM call ─────────────────────────────────────────────────────────────

    def _call_llm(self, system: str, prompt: str,
                  max_tokens: Optional[int] = None) -> Optional[str]:
        """Groq → Ollama → None."""
        tok = max_tokens or self.max_tok

        if self.groq_client is not None:
            try:
                resp = self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=self.temp,
                    max_tokens=tok,
                )
                return resp.choices[0].message.content
            except Exception as e:
                logger.warning(f"Groq error: {e} — trying Ollama")

        if OLLAMA_AVAILABLE:
            try:
                client = ollama_client.Client(host=self.host)
                resp   = client.chat(
                    model="llama3.1:latest",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt},
                    ],
                    options={"temperature": self.temp, "num_predict": tok},
                )
                return resp["message"]["content"]
            except Exception as e:
                logger.warning(f"Ollama error: {e}")

        return None

    # ── Per-agent analyst calls ───────────────────────────────────────────────

    def _macro_analyst(self, macro: Dict, pair: str) -> Tuple[str, str, bool]:
        """Returns (analyst_text, key_feature, override_flag)."""
        prompt = _macro_analyst_prompt(macro, pair)
        raw    = self._call_llm(MACRO_ANALYST_SYSTEM, prompt, max_tokens=256)
        if raw:
            parsed = _parse_json(raw)
            if parsed:
                return (
                    parsed.get("analyst_text", ""),
                    parsed.get("key_feature", "mac_yield_z"),
                    bool(parsed.get("override", False)),
                )

        # Fallback
        feats   = macro.get("mac_features", {})
        eff, _  = effective_macro_dir(macro)
        yield_z = feats.get("mac_yield_z", 0.0)
        vix_z   = feats.get("mac_vix_z", 0.0)
        text = (
            f"Macro regime is {eff} with yield_z={yield_z:+.3f} "
            f"({'steepening' if yield_z > 0 else 'flattening'} yield curve) "
            f"and vix_z={vix_z:+.3f} "
            f"({'elevated risk-off' if vix_z > 0.5 else 'contained volatility'})."
        )
        return text, "mac_yield_z", False

    def _tech_analyst(self, tech: Dict, pair: str, last_bar: Dict) -> Tuple[str, str, bool]:
        """Returns (analyst_text, key_feature, override_flag)."""
        prompt = _tech_analyst_prompt(tech, pair, last_bar)
        raw    = self._call_llm(TECH_ANALYST_SYSTEM, prompt, max_tokens=256)
        if raw:
            parsed = _parse_json(raw)
            if parsed:
                return (
                    parsed.get("analyst_text", ""),
                    parsed.get("key_feature", "rsi14"),
                    bool(parsed.get("override", False)),
                )

        # Fallback
        rsi14 = last_bar.get("rsi14", 0.5) * 100
        text = (
            f"Technical model signals {tech.get('signal','HOLD')} with "
            f"P(BUY)={tech.get('p_buy',0):.2f}/P(SELL)={tech.get('p_sell',0):.2f} "
            f"and RSI(14)={rsi14:.0f}."
        )
        return text, "rsi14", tech.get("confidence", 0) < 0.1

    def _sent_analyst(self, sent: Dict, headlines: List[str],
                      pair: str) -> Tuple[str, str, bool]:
        """Returns (analyst_text, key_feature, override_flag)."""
        prompt = _sent_analyst_prompt(sent, headlines, pair)
        raw    = self._call_llm(SENT_ANALYST_SYSTEM, prompt, max_tokens=256)
        if raw:
            parsed = _parse_json(raw)
            if parsed:
                return (
                    parsed.get("analyst_text", ""),
                    parsed.get("key_feature", "nws_sent_signal"),
                    bool(parsed.get("override", False)),
                )

        # Fallback
        low_news = "LOW-NEWS" in sent.get("signal", "")
        if low_news:
            text = "Insufficient news coverage — sentiment signal unreliable."
        else:
            text = (
                f"News sentiment is {sent.get('signal','HOLD')} with "
                f"P(bullish)={sent.get('p_buy',0):.2f}."
            )
        return text, "nws_sent_signal", low_news

    # ── Main run ──────────────────────────────────────────────────────────────

    def run(
        self,
        pair: str,
        macro_out: Dict,
        tech_out: Dict,
        sent_out: Dict,
        headlines: List[str],
        conviction: Dict,
        last_bar: Optional[Dict] = None,
    ) -> Dict:
        """
        Stage 5: Generate per-agent analyst reports + final reasoning.

        conviction: output from ConvictionGate.evaluate()
        last_bar:   last row of price_df as dict (for technical indicators)
        """
        direction     = conviction["direction"]
        confidence    = conviction["confidence"]
        position_size = conviction["position_size"]
        agreement     = conviction["agreement"]
        eff_macro     = conviction["eff_macro"]

        last_bar = last_bar or {}

        logger.info(f"  Orchestrator: {direction} conf={confidence:.3f} agree={agreement}")

        # ── Per-agent analyst calls (parallel-ish via sequential Groq calls) ──
        logger.debug("  → Macro analyst …")
        macro_text, macro_feat, macro_override = self._macro_analyst(macro_out, pair)

        logger.debug("  → Technical analyst …")
        tech_text, tech_feat, tech_override = self._tech_analyst(tech_out, pair, last_bar)

        logger.debug("  → Sentiment analyst …")
        sent_text, sent_feat, sent_override = self._sent_analyst(sent_out, headlines, pair)

        # ── Final orchestrator reasoning ──────────────────────────────────────
        logger.debug("  → Final orchestrator reasoning …")
        orch_prompt = _orchestrator_prompt(
            pair, direction, confidence, agreement,
            macro_text, tech_text, sent_text, headlines,
        )
        raw = self._call_llm(ORCHESTRATOR_SYSTEM, orch_prompt, max_tokens=512)

        reasoning  = ""
        key_driver = ""
        risk_note  = ""
        source     = "fallback"

        if raw:
            parsed = _parse_json(raw)
            if parsed:
                reasoning  = parsed.get("reasoning",  "")
                key_driver = parsed.get("key_driver", "")
                risk_note  = parsed.get("risk_note",  "")
                source     = "groq" if self.groq_client else "ollama"

        if not reasoning:
            reasoning  = (
                f"Macro: {eff_macro}. "
                f"Tech: {tech_out.get('signal','HOLD')} "
                f"(conf={tech_out.get('confidence',0):.2f}). "
                f"Sentiment: {sent_out.get('signal','HOLD')}."
            )
            key_driver = "TECHNICAL"
            risk_note  = "Rule-based reasoning — LLM unavailable."

        logger.info(
            f"  {source.upper()} → {direction} "
            f"conf={confidence:.3f} size={position_size:.2f} agree={agreement}"
        )

        # ── Assemble final signal ─────────────────────────────────────────────
        return {
            "timestamp":        datetime.now(timezone.utc).isoformat(),
            "pair":             pair,
            "direction":        direction,
            "confidence":       confidence,
            "position_size":    position_size,
            "reasoning":        reasoning,
            "key_driver":       key_driver,
            "risk_note":        risk_note,
            "agent_agreement":  agreement,
            "source":           source,
            "macro_regime":     eff_macro,
            "macro_regime_raw": macro_out.get("regime_label", "unknown"),
            "tech_signal":      tech_out.get("signal", "HOLD"),
            "sent_signal":      sent_out.get("signal", "HOLD"),
            "macro_conf":       macro_out.get("regime_conf", 0.0),
            "tech_conf":        tech_out.get("confidence", 0.0),
            "sent_conf":        sent_out.get("confidence", 0.0),
            # Per-agent analyst reports (shown in UI Analyst Breakdown)
            "macro_analyst":    macro_text,
            "macro_key_feat":   macro_feat,
            "macro_override":   macro_override,
            "tech_analyst":     tech_text,
            "tech_key_feat":    tech_feat,
            "tech_override":    tech_override,
            "sent_analyst":     sent_text,
            "sent_key_feat":    sent_feat,
            "sent_override":    sent_override,
        }

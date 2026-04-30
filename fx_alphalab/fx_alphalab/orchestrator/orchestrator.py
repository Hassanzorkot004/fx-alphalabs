# """
# orchestrator/orchestrator.py
# ────────────────────────────────────────────────────────────────────────────
# LLM Orchestrator — Llama 3.1 8B via Ollama.

# FIX: Confidence is now computed in Python from agent agreement metrics,
# not by the LLM. Llama 3.1 8B anchors to ~0.55-0.57 regardless of prompt
# instructions — this is a known limitation of small RLHF-tuned models.

# The LLM is now used ONLY for:
#   - direction (BUY/SELL/HOLD)
#   - reasoning text
#   - risk_note
#   - key_driver

# Confidence, position_size, and agent_agreement are computed deterministically
# in Python based on how many agents agree, their individual confidence scores,
# and the effective macro regime.
# """
# from __future__ import annotations

# import json
# import re
# from datetime import datetime, timezone
# from typing import Dict, List, Optional, Tuple

# import numpy as np
# from loguru import logger

# try:
#     import ollama as ollama_client
#     OLLAMA_AVAILABLE = True
# except ImportError:
#     OLLAMA_AVAILABLE = False
#     logger.warning("ollama not installed — run: pip install ollama")


# # ── Python confidence computation ─────────────────────────────────────────────

# def _effective_macro_dir(macro: Dict) -> Tuple[str, int]:
#     """Return (effective_label, direction_int) correcting for mislabelled clusters."""
#     label   = macro.get("regime_label", "neutral")
#     feats   = macro.get("mac_features", {})
#     yield_z = feats.get("mac_yield_z", 0.0)
#     if label == "bearish" and yield_z > 0.10:
#         label = "neutral"
#     elif label == "bullish" and yield_z < -0.10:
#         label = "neutral"
#     direction = 1 if label == "bullish" else (-1 if label == "bearish" else 0)
#     return label, direction


# def compute_signal_confidence(
#     direction: str,
#     macro: Dict,
#     tech: Dict,
#     sent: Dict,
# ) -> Tuple[float, float, str]:
#     """
#     Compute (confidence, position_size, agreement) from agent outputs.

#     Agreement tiers:
#       FULL    (3/3 agree)  → base 0.78
#       PARTIAL (2/3 agree)  → base 0.65
#       PARTIAL (2 agree, 1 opposes) → base 0.54
#       CONFLICT (direct tech↔macro conflict) → base 0.46 → HOLD
#     """
#     if direction == "HOLD":
#         return 0.55, 0.0, "CONFLICT"

#     primary    = 1 if direction == "BUY" else -1
#     tech_dir   = tech.get("direction", 0)
#     tech_conf  = float(tech.get("confidence", 0.40))
#     sent_dir   = sent.get("direction", 0)
#     sent_conf  = float(sent.get("confidence", 0.0))
#     sent_real  = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

#     macro_eff_label, macro_dir = _effective_macro_dir(macro)
#     macro_conf = float(macro.get("regime_conf", 0.50))

#     # Count each agent's vote
#     votes_agree  = 0
#     votes_oppose = 0
#     conf_sum     = 0.0

#     # Technical (primary signal, highest weight)
#     if tech_dir == primary:
#         votes_agree += 1
#         conf_sum += tech_conf * 1.2
#     elif tech_dir == -primary:
#         votes_oppose += 1
#         conf_sum -= tech_conf * 0.5

#     # Sentiment (only if real news available)
#     if sent_real:
#         if sent_dir == primary:
#             votes_agree += 1
#             conf_sum += sent_conf * 1.0
#         elif sent_dir == -primary:
#             votes_oppose += 1
#             conf_sum -= sent_conf * 0.5

#     # Macro (lower weight — lags price action)
#     if macro_dir == primary:
#         votes_agree += 1
#         conf_sum += macro_conf * 0.6
#     elif macro_dir == -primary:
#         votes_oppose += 1
#         conf_sum -= macro_conf * 0.4

#     total_votes = votes_agree + votes_oppose

#     # Base confidence by agreement pattern
#     if votes_agree == 3 and votes_oppose == 0:
#         base   = 0.78
#         agree  = "FULL"
#     elif votes_agree == 2 and votes_oppose == 0:
#         base   = 0.65
#         agree  = "PARTIAL"
#     elif votes_agree == 2 and votes_oppose == 1:
#         base   = 0.58   # tech+sent agree vs macro alone — price action wins
#         agree  = "PARTIAL"
#     elif votes_agree == 1 and votes_oppose == 0:
#         base   = 0.52
#         agree  = "PARTIAL"
#     elif votes_agree == 1 and votes_oppose == 1:
#         # Direct conflict — reduce confidence significantly
#         base   = 0.46
#         agree  = "CONFLICT"
#     else:
#         base   = 0.50
#         agree  = "PARTIAL"

#     # Fine-tune by normalised confidence sum (±0.08 range)
#     norm_adj = np.clip(conf_sum / max(total_votes, 1) - 0.4, -0.08, 0.08)
#     final    = round(float(np.clip(base + norm_adj, 0.35, 0.88)), 3)

#     # Position size
#     if agree == "CONFLICT" or final < 0.44:
#         pos_size = 0.0
#     elif agree == "FULL":
#         pos_size = round(min(final * 0.95, 0.88), 2)
#     else:
#         pos_size = round(min(final * 0.78, 0.65), 2)

#     return final, pos_size, agree


# # ── LLM prompt (direction + reasoning only) ───────────────────────────────────

# SYSTEM_PROMPT = """You are an expert FX trading signal analyst.

# You will receive outputs from three specialist agents. Your job is ONLY to:
# 1. Choose direction: BUY, SELL, or HOLD
# 2. Write a 2-sentence reasoning
# 3. Identify the key_driver
# 4. Note the main risk

# Do NOT output a confidence value or position_size — these are computed separately.

# MACRO GUIDE:
#   mac_yield_z > 0 = yield curve steeper than avg (bullish USD backdrop)
#   mac_yield_z < 0 = yield curve flat/inverted (bearish/risk-off)
#   If regime='bearish' but yield_z>0: treat macro as NEUTRAL
#   "HOLD [LOW-NEWS]" from sentiment = no news, treat as NEUTRAL

# DIRECTION RULES:
#   BUY  — when tech+sent agree on upside, even if macro is neutral/weak bearish
#   SELL — when tech+sent agree on downside, even if macro is neutral/weak bullish
#   HOLD — ONLY when tech and macro directly and strongly conflict with no tiebreaker

# OUTPUT — respond ONLY with this JSON:
# {
#   "direction": "BUY" or "SELL" or "HOLD",
#   "reasoning": "<2 sentences explaining the most important factors>",
#   "key_driver": "<single most important factor>",
#   "risk_note": "<main risk to this signal>"
# }"""


# def _build_prompt(pair: str, macro: Dict, tech: Dict, sent: Dict,
#                   headlines: List[str]) -> str:
#     feats   = macro.get("mac_features", {})
#     yield_z = feats.get("mac_yield_z", 0.0)
#     mac_str = feats.get("mac_macro_strength", 0.0)
#     regime  = macro.get("regime_label", "unknown")

#     note = ""
#     if regime == "bearish" and yield_z > 0.1:
#         note = f" ⚠ yield_z={yield_z:+.2f}>0 → treat as NEUTRAL"
#     elif regime == "bullish" and yield_z < -0.1:
#         note = f" ⚠ yield_z={yield_z:+.2f}<0 → treat as NEUTRAL"

#     sent_note = ""
#     if "LOW-NEWS" in sent.get("signal", ""):
#         sent_note = " [NO news — treat as NEUTRAL]"

#     return f"""Pair: {pair.replace('=X','')} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

# MACRO: regime={regime.upper()}{note}
#   yield_z={yield_z:+.3f}  macro_strength={mac_str:+.3f}
#   probs: bullish={macro.get('regime_probs',{}).get('bullish',0):.2f} neutral={macro.get('regime_probs',{}).get('neutral',0):.2f} bearish={macro.get('regime_probs',{}).get('bearish',0):.2f}

# TECHNICAL: {tech.get('signal','HOLD')}
#   P(BUY)={tech.get('p_buy',0):.3f}  P(HOLD)={tech.get('p_hold',0):.3f}  P(SELL)={tech.get('p_sell',0):.3f}
#   model_conf={tech.get('confidence',0):.3f}  uncertainty={tech.get('uncertainty',1):.3f}

# SENTIMENT: {sent.get('signal','HOLD')}{sent_note}
#   P(BUY)={sent.get('p_buy',0):.3f}  P(HOLD)={sent.get('p_hold',0):.3f}  P(SELL)={sent.get('p_sell',0):.3f}

# HEADLINES:
# {chr(10).join(headlines[:4])}

# Choose direction and explain. Output only the JSON."""


# def _parse_json(text: str) -> Optional[Dict]:
#     try:
#         return json.loads(text.strip())
#     except Exception:
#         pass
#     for pattern in [r'\{[^{}]+\}', r'\{.*?\}']:
#         m = re.search(pattern, text, re.DOTALL)
#         if m:
#             try:
#                 return json.loads(m.group())
#             except Exception:
#                 pass
#     return None


# def _rule_based_direction(macro: Dict, tech: Dict, sent: Dict) -> str:
#     """Determine direction without LLM."""
#     _, macro_dir = _effective_macro_dir(macro)
#     tech_dir     = tech.get("direction", 0)
#     sent_dir     = sent.get("direction", 0)
#     sent_real    = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

#     if tech_dir == 0:
#         return "HOLD"

#     if sent_real and sent_dir == tech_dir:
#         # Tech + sentiment agree → follow them regardless of macro
#         return "BUY" if tech_dir == 1 else "SELL"
#     elif macro_dir == tech_dir:
#         # Tech + macro agree
#         return "BUY" if tech_dir == 1 else "SELL"
#     elif macro_dir == -tech_dir and macro_dir != 0:
#         # Direct conflict between macro and tech with no sentiment tiebreaker
#         return "HOLD"
#     else:
#         # Tech alone, macro neutral
#         return "BUY" if tech_dir == 1 else "SELL"


# # ── Orchestrator ──────────────────────────────────────────────────────────────

# class Orchestrator:

#     def __init__(self, cfg: dict):
#         llm           = cfg["llm"]
#         self.model    = llm["model"]
#         self.host     = llm["host"]
#         self.temp     = llm["temperature"]
#         self.max_tok  = llm["max_tokens"]
#         self.min_conf = cfg["signal"]["min_confidence"]

#     def run(self, pair: str, macro_out: Dict, tech_out: Dict,
#             sent_out: Dict, headlines: List[str]) -> Dict:

#         # ── Step 1: Get direction from LLM (or fallback) ──────────────────────
#         direction = None
#         reasoning = ""
#         key_driver = ""
#         risk_note  = ""
#         source     = "llm"

#         if OLLAMA_AVAILABLE:
#             try:
#                 client   = ollama_client.Client(host=self.host)
#                 prompt   = _build_prompt(pair, macro_out, tech_out, sent_out, headlines)
#                 response = client.chat(
#                     model=self.model,
#                     messages=[
#                         {"role": "system", "content": SYSTEM_PROMPT},
#                         {"role": "user",   "content": prompt},
#                     ],
#                     options={"temperature": self.temp, "num_predict": 512},
#                 )
#                 raw    = response["message"]["content"]
#                 logger.debug(f"LLM raw:\n{raw[:600]}")
#                 parsed = _parse_json(raw)
#                 if parsed and "direction" in parsed:
#                     direction  = parsed.get("direction", "HOLD").upper()
#                     reasoning  = parsed.get("reasoning", "")
#                     key_driver = parsed.get("key_driver", "")
#                     risk_note  = parsed.get("risk_note", "")
#                 else:
#                     logger.warning("LLM response unparseable — rule-based direction")
#             except Exception as e:
#                 logger.warning(f"Ollama error: {e} — rule-based direction")

#         if direction is None:
#             direction  = _rule_based_direction(macro_out, tech_out, sent_out)
#             eff_label, _ = _effective_macro_dir(macro_out)
#             reasoning  = (
#                 f"Effective macro: {eff_label}. "
#                 f"Tech: {tech_out.get('signal','HOLD')} (conf={tech_out.get('confidence',0):.2f}). "
#                 f"Sentiment: {sent_out.get('signal','HOLD')}."
#             )
#             key_driver = "Technical"
#             risk_note  = "Rule-based signal — LLM unavailable."
#             source     = "fallback"

#         # Normalise direction
#         if direction not in ("BUY", "SELL", "HOLD"):
#             direction = "HOLD"

#         # ── Step 2: Compute confidence in Python ───────────────────────────────
#         confidence, position_size, agreement = compute_signal_confidence(
#             direction, macro_out, tech_out, sent_out
#         )

#         logger.info(
#             f"  {source.upper()} → {direction} "
#             f"conf={confidence:.3f} size={position_size:.2f} agree={agreement}"
#         )

#         # ── Step 3: Confidence gate ────────────────────────────────────────────
#         if confidence < self.min_conf:
#             orig = direction
#             direction    = "HOLD"
#             position_size = 0.0
#             reasoning    = (
#                 f"Conf {confidence:.3f} < threshold {self.min_conf}. "
#                 f"Original: {orig}. " + reasoning
#             )

#         # ── Step 4: Assemble signal ────────────────────────────────────────────
#         eff_label, _ = _effective_macro_dir(macro_out)
#         return {
#             "timestamp":        datetime.now(timezone.utc).isoformat(),
#             "pair":             pair,
#             "direction":        direction,
#             "confidence":       confidence,
#             "position_size":    position_size,
#             "reasoning":        reasoning,
#             "key_driver":       key_driver,
#             "risk_note":        risk_note,
#             "agent_agreement":  agreement,
#             "source":           source,
#             "macro_regime":     eff_label,
#             "macro_regime_raw": macro_out.get("regime_label", "unknown"),
#             "tech_signal":      tech_out.get("signal", "HOLD"),
#             "sent_signal":      sent_out.get("signal", "HOLD"),
#             "macro_conf":       macro_out.get("regime_conf", 0.0),
#             "tech_conf":        tech_out.get("confidence", 0.0),
#             "sent_conf":        sent_out.get("confidence", 0.0),
#         }









"""
orchestrator/orchestrator.py
────────────────────────────────────────────────────────────────────────────
LLM Orchestrator — Groq (llama3.1:70b) + Ollama fallback + rule-based fallback

ARCHITECTURE v3:
  1. Direction   → _rule_based_direction() déterministe (fiable, cohérent)
  2. Reasoning   → LLM Groq (llama3.1:70b) — expert forex, raisonnement riche
  3. Confidence  → Python déterministe (pas le LLM)

  Pourquoi cette séparation :
    - La DIRECTION doit être cohérente et reproductible → Python
    - Le RAISONNEMENT doit être intelligent et contextuel → LLM
    - La CONFIANCE doit être calibrée sur les agents → Python

  Priorité LLM :
    1. Groq API (llama3.1:70b — gratuit, rapide, expert)
    2. Ollama local (llama3.1:8b — fallback)
    3. Rule-based (si tout est indisponible)
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

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


# ── Python confidence computation ─────────────────────────────────────────────

def _effective_macro_dir(macro: Dict) -> Tuple[str, int]:
    label   = macro.get("regime_label", "neutral")
    feats   = macro.get("mac_features", {})
    yield_z = feats.get("mac_yield_z", 0.0)
    if label == "bearish" and yield_z > 0.10:
        label = "neutral"
    elif label == "bullish" and yield_z < -0.10:
        label = "neutral"
    direction = 1 if label == "bullish" else (-1 if label == "bearish" else 0)
    return label, direction


def compute_signal_confidence(
    direction: str,
    macro: Dict,
    tech: Dict,
    sent: Dict,
) -> Tuple[float, float, str]:
    if direction == "HOLD":
        return 0.55, 0.0, "CONFLICT"

    primary   = 1 if direction == "BUY" else -1
    tech_dir  = tech.get("direction", 0)
    tech_conf = float(tech.get("confidence", 0.40))
    sent_dir  = sent.get("direction", 0)
    sent_conf = float(sent.get("confidence", 0.0))
    sent_real = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

    macro_eff_label, macro_dir = _effective_macro_dir(macro)
    macro_conf = float(macro.get("regime_conf", 0.50))

    votes_agree  = 0
    votes_oppose = 0
    conf_sum     = 0.0

    if tech_dir == primary:
        votes_agree += 1
        conf_sum += tech_conf * 1.5       # poids tech augmenté
    elif tech_dir == -primary:
        votes_oppose += 1
        conf_sum -= tech_conf * 0.5

    if sent_real:
        if sent_dir == primary:
            votes_agree += 1
            conf_sum += sent_conf * 1.0
        elif sent_dir == -primary:
            votes_oppose += 1
            conf_sum -= sent_conf * 0.5

    if macro_dir == primary:
        votes_agree += 1
        conf_sum += macro_conf * 0.4      # poids macro réduit
    elif macro_dir == -primary:
        votes_oppose += 1
        conf_sum -= macro_conf * 0.4

    total_votes = votes_agree + votes_oppose

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
        agree = "PARTIAL"
    elif votes_agree == 1 and votes_oppose == 1:
        base  = 0.46
        agree = "CONFLICT"
    else:
        base  = 0.50
        agree = "PARTIAL"

    norm_adj = np.clip(conf_sum / max(total_votes, 1) - 0.4, -0.08, 0.08)
    final    = round(float(np.clip(base + norm_adj, 0.35, 0.88)), 3)

    if agree == "CONFLICT" or final < 0.44:
        pos_size = 0.0
    elif agree == "FULL":
        pos_size = round(min(final * 0.95, 0.88), 2)
    else:
        pos_size = round(min(final * 0.78, 0.65), 2)

    return final, pos_size, agree


# ── Direction déterministe (Python) ───────────────────────────────────────────

def _rule_based_direction(macro: Dict, tech: Dict, sent: Dict) -> str:
    """
    Détermine la direction de façon déterministe.
    Le LLM ne décide plus la direction — il explique seulement.
    """
    _, macro_dir = _effective_macro_dir(macro)
    tech_dir     = tech.get("direction", 0)
    sent_dir     = sent.get("direction", 0)
    sent_real    = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

    if tech_dir == 0:
        return "HOLD"

    # Tech + sent alignés → suivre peu importe macro
    if sent_real and sent_dir == tech_dir:
        return "BUY" if tech_dir == 1 else "SELL"

    # Tech + macro alignés
    if macro_dir == tech_dir:
        return "BUY" if tech_dir == 1 else "SELL"

    # Conflit direct tech vs macro → HOLD
    if macro_dir == -tech_dir and macro_dir != 0:
        return "HOLD"

    # Tech seul, macro neutral → suivre tech
    return "BUY" if tech_dir == 1 else "SELL"


# ── System prompt LLM (reasoning uniquement) ──────────────────────────────────

SYSTEM_PROMPT = """You are a senior FX trader with 15 years of experience on EUR/USD, GBP/USD and USD/JPY.

The trading DIRECTION has already been decided by a quantitative system.
Your job is to provide expert reasoning that explains WHY this direction makes sense
given the current market context.

You will receive:
- The decided direction (BUY/SELL/HOLD)
- Quantitative agent outputs (macro regime, technical signals, sentiment)
- Live market headlines

Your task:
1. Write 2 sentences of expert reasoning explaining the direction
2. Identify the single most important driver
3. Note the main risk to this trade

FOREX KNOWLEDGE TO APPLY:
- yield_z > 0 = yield curve steepening = USD bullish backdrop
- yield_z < 0 = yield curve flattening/inverting = risk-off, USD safe haven bid
- VIX rising = risk-off = JPY and USD bid, EUR/GBP offered
- Fed hawkish = USD bullish across all pairs
- ECB hawkish = EUR bullish vs USD
- BOJ dovish = JPY bearish = USDJPY higher
- Oil spike = JPY bearish (Japan imports 90% of oil)
- Gold rising = risk-off or USD weakness
- P(SELL) > 0.60 = strong technical sell signal
- P(BUY) > 0.60 = strong technical buy signal

IMPORTANT:
- Base reasoning ONLY on data provided in this prompt
- Do not invent data not present in headlines or agent outputs
- Be specific — mention actual values from the data (yield_z, P values, etc.)

OUTPUT — respond ONLY with this JSON, nothing else:
{
  "reasoning": "<2 sentences of expert FX reasoning referencing actual data values>",
  "key_driver": "<TECHNICAL or MACRO or SENTIMENT or NEWS>",
  "risk_note": "<specific risk to this trade based on provided context>"
}"""


def _build_prompt(pair: str, macro: Dict, tech: Dict, sent: Dict,
                  headlines: List[str], direction: str) -> str:
    feats   = macro.get("mac_features", {})
    yield_z = feats.get("mac_yield_z", 0.0)
    mac_str = feats.get("mac_macro_strength", 0.0)
    vix_z   = feats.get("mac_vix_z", 0.0)
    regime  = macro.get("regime_label", "unknown")

    eff_label, _ = _effective_macro_dir(macro)
    macro_note = ""
    if eff_label != regime:
        macro_note = f" (effective: NEUTRAL due to yield_z={yield_z:+.2f})"

    sent_note = " [LOW-NEWS — no significant headlines]" \
        if "LOW-NEWS" in sent.get("signal", "") else ""

    headlines_str = "\n".join(
        f"  - {h}" for h in headlines[:5]
    ) if headlines else "  - No headlines available"

    return f"""Pair: {pair.replace('=X', '')} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

DECIDED DIRECTION: {direction}
(Explain why this direction is correct given the data below)

━━━ MACRO AGENT ━━━
Regime: {regime.upper()}{macro_note}
yield_z={yield_z:+.3f}  macro_strength={mac_str:+.3f}  vix_z={vix_z:+.3f}
Regime probs: bullish={macro.get('regime_probs', {}).get('bullish', 0):.2f}  neutral={macro.get('regime_probs', {}).get('neutral', 0):.2f}  bearish={macro.get('regime_probs', {}).get('bearish', 0):.2f}

━━━ TECHNICAL AGENT ━━━
Signal: {tech.get('signal', 'HOLD')}
P(BUY)={tech.get('p_buy', 0):.3f}  P(HOLD)={tech.get('p_hold', 0):.3f}  P(SELL)={tech.get('p_sell', 0):.3f}
model_confidence={tech.get('confidence', 0):.3f}  uncertainty={tech.get('uncertainty', 1):.3f}

━━━ SENTIMENT AGENT ━━━
Signal: {sent.get('signal', 'HOLD')}{sent_note}
P(bullish)={sent.get('p_buy', 0):.3f}

━━━ LIVE HEADLINES ━━━
{headlines_str}

Now explain in 2 sentences why {direction} is the right call. Output only the JSON."""


def _parse_json(text: str) -> Optional[Dict]:
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


# ── Orchestrator ──────────────────────────────────────────────────────────────

class Orchestrator:

    def __init__(self, cfg: dict):
        llm           = cfg["llm"]
        self.model    = llm.get("model", "llama-3.1-70b-versatile")
        self.host     = llm.get("host", "http://localhost:11434")
        self.temp     = llm.get("temperature", 0.1)
        self.max_tok  = llm.get("max_tokens", 512)
        self.min_conf = cfg["signal"]["min_confidence"]

        # ── Init Groq client ──────────────────────────────────────────────────
        self.groq_client = None
        groq_key = llm.get("groq_api_key", "") or os.getenv("GROQ_API_KEY", "")
        if GROQ_AVAILABLE and groq_key and groq_key != "YOUR_GROQ_KEY_HERE":
            try:
                self.groq_client = Groq(api_key=groq_key)
                logger.info(
                    f"  Groq client initialized ✓ "
                    f"model={self.model}"
                )
            except Exception as e:
                logger.warning(f"  Groq init failed: {e}")
        else:
            if not groq_key:
                logger.warning(
                    "  No Groq API key found — "
                    "add groq_api_key in agent_config.yaml or set GROQ_API_KEY env var"
                )
            logger.info("  Will use Ollama or rule-based fallback")

    def _call_llm(self, system: str, prompt: str) -> Optional[str]:
        """
        Appelle le LLM dans l'ordre :
          1. Groq API (llama3.1:70b — priorité)
          2. Ollama local (fallback)
        """
        # ── 1. Groq ──────────────────────────────────────────────────────────
        if self.groq_client is not None:
            try:
                response = self.groq_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt},
                    ],
                    temperature=self.temp,
                    max_tokens=self.max_tok,
                )
                raw = response.choices[0].message.content
                logger.debug(f"Groq raw:\n{raw[:600]}")
                return raw
            except Exception as e:
                logger.warning(f"Groq error: {e} — trying Ollama fallback")

        # ── 2. Ollama fallback ────────────────────────────────────────────────
        if OLLAMA_AVAILABLE:
            try:
                client   = ollama_client.Client(host=self.host)
                response = client.chat(
                    model="llama3.1:latest",
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt},
                    ],
                    options={"temperature": self.temp, "num_predict": 512},
                )
                raw = response["message"]["content"]
                logger.debug(f"Ollama raw:\n{raw[:600]}")
                return raw
            except Exception as e:
                logger.warning(f"Ollama error: {e}")

        return None

    def run(self, pair: str, macro_out: Dict, tech_out: Dict,
            sent_out: Dict, headlines: List[str]) -> Dict:

        # ── Step 1: Direction déterministe (Python) ───────────────────────────
        direction = _rule_based_direction(macro_out, tech_out, sent_out)
        source    = "rule_based"

        # ── Step 2: Confidence en Python ─────────────────────────────────────
        confidence, position_size, agreement = compute_signal_confidence(
            direction, macro_out, tech_out, sent_out
        )

        # ── Step 3: Reasoning via LLM (expert forex) ─────────────────────────
        reasoning  = ""
        key_driver = ""
        risk_note  = ""

        prompt = _build_prompt(
            pair, macro_out, tech_out, sent_out, headlines, direction
        )
        raw = self._call_llm(SYSTEM_PROMPT, prompt)

        if raw:
            parsed = _parse_json(raw)
            if parsed:
                reasoning  = parsed.get("reasoning",  "")
                key_driver = parsed.get("key_driver", "")
                risk_note  = parsed.get("risk_note",  "")
                source     = "groq" if self.groq_client else "ollama"
            else:
                logger.warning("LLM response unparseable — using rule-based reasoning")

        # Fallback reasoning si LLM indisponible
        if not reasoning:
            eff_label, _ = _effective_macro_dir(macro_out)
            reasoning = (
                f"Effective macro: {eff_label}. "
                f"Tech: {tech_out.get('signal','HOLD')} "
                f"(conf={tech_out.get('confidence',0):.2f}). "
                f"Sentiment: {sent_out.get('signal','HOLD')}."
            )
            key_driver = "TECHNICAL"
            risk_note  = "Rule-based signal — LLM unavailable."
            source     = "fallback"

        logger.info(
            f"  {source.upper()} → {direction} "
            f"conf={confidence:.3f} size={position_size:.2f} agree={agreement}"
        )

        # ── Step 4: Confidence gate ────────────────────────────────────────────
        if confidence < self.min_conf:
            orig          = direction
            direction     = "HOLD"
            position_size = 0.0
            reasoning     = (
                f"Conf {confidence:.3f} < threshold {self.min_conf}. "
                f"Original: {orig}. " + reasoning
            )

        # ── Step 5: Assembler le signal ───────────────────────────────────────
        eff_label, _ = _effective_macro_dir(macro_out)
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
            "macro_regime":     eff_label,
            "macro_regime_raw": macro_out.get("regime_label", "unknown"),
            "tech_signal":      tech_out.get("signal", "HOLD"),
            "sent_signal":      sent_out.get("signal", "HOLD"),
            "macro_conf":       macro_out.get("regime_conf", 0.0),
            "tech_conf":        tech_out.get("confidence", 0.0),
            "sent_conf":        sent_out.get("confidence", 0.0),
        }
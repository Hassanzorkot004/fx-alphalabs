"""
orchestrator/orchestrator.py
────────────────────────────────────────────────────────────────────────────
LLM Orchestrator — Agentic loop using hosted Llama 3.1 70B with tool calling.

ARCHITECTURE:
  1. Pre-fetch: Run all 3 ML models BEFORE the LLM loop (cached results)
  2. Agentic loop: LLM calls tools → tools return cached results instantly
  3. Final answer: LLM synthesizes all 3 outputs → direction + reasoning
  4. Confidence: Computed deterministically in Python (not by LLM)
  5. Fallback: Rule-based direction if LLM fails or times out
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from fx_alphalab.llm.client import get_llm_client, MODEL


# ── Python confidence computation (unchanged) ─────────────────────────────────

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
        conf_sum += tech_conf * 1.5
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
        conf_sum += macro_conf * 0.4
    elif macro_dir == -primary:
        votes_oppose += 1
        conf_sum -= macro_conf * 0.4

    total_votes = votes_agree + votes_oppose

    if votes_agree == 3 and votes_oppose == 0:
        base  = 0.78; agree = "FULL"
    elif votes_agree == 2 and votes_oppose == 0:
        base  = 0.65; agree = "PARTIAL"
    elif votes_agree == 2 and votes_oppose == 1:
        base  = 0.58; agree = "PARTIAL"
    elif votes_agree == 1 and votes_oppose == 0:
        base  = 0.52; agree = "PARTIAL"
    elif votes_agree == 1 and votes_oppose == 1:
        base  = 0.46; agree = "CONFLICT"
    else:
        base  = 0.50; agree = "PARTIAL"

    norm_adj = np.clip(conf_sum / max(total_votes, 1) - 0.4, -0.08, 0.08)
    final    = round(float(np.clip(base + norm_adj, 0.35, 0.88)), 3)

    if agree == "CONFLICT" or final < 0.44:
        pos_size = 0.0
    elif agree == "FULL":
        pos_size = round(min(final * 0.95, 0.88), 2)
    else:
        pos_size = round(min(final * 0.78, 0.65), 2)

    return final, pos_size, agree


# ── Rule-based fallback direction ─────────────────────────────────────────────

def _rule_based_direction(macro: Dict, tech: Dict, sent: Dict) -> str:
    _, macro_dir = _effective_macro_dir(macro)
    tech_dir     = tech.get("direction", 0)
    sent_dir     = sent.get("direction", 0)
    sent_real    = "LOW-NEWS" not in sent.get("signal", "") and sent_dir != 0

    if tech_dir == 0:
        return "HOLD"
    if sent_real and sent_dir == tech_dir:
        return "BUY" if tech_dir == 1 else "SELL"
    if macro_dir == tech_dir:
        return "BUY" if tech_dir == 1 else "SELL"
    if macro_dir == -tech_dir and macro_dir != 0:
        return "HOLD"
    return "BUY" if tech_dir == 1 else "SELL"


# ── System prompt for agentic loop ────────────────────────────────────────────

SYSTEM_PROMPT = """You are a senior FX trader with 15 years of experience on EUR/USD, GBP/USD and USD/JPY.

You have access to three quantitative models as tools:
- run_macro_model: Returns macro regime (bullish/neutral/bearish) with probs
- run_technical_model: Returns BUY/SELL/HOLD with probabilities and confidence
- run_sentiment_model: Returns sentiment signal with confidence

Your job:
1. Call ALL THREE tools to get the latest model outputs
2. Synthesize their outputs into a final BUY/SELL/HOLD decision
3. Provide 2 sentences of expert reasoning
4. Identify the key driver
5. Note the main risk

DIRECTION RULES:
- Tech+sent agree → follow them regardless of macro
- Tech+macro agree, sent neutral → follow them
- Tech↔macro direct conflict, no sent tiebreaker → HOLD
- Tech weak (uncertainty > 0.6) → weight macro and sent more

FOREX KNOWLEDGE:
- yield_z > 0 → yield curve steepening → USD bullish
- yield_z < 0 → yield curve flattening → risk-off
- VIX rising → JPY/USD bid, EUR/GBP offered
- "HOLD [LOW-NEWS]" from sentiment → no news, treat as NEUTRAL
- Technical signal is primary; macro provides backdrop; sentiment provides confirmation

OUTPUT — after calling all tools, respond with ONLY this JSON:
{
  "direction": "BUY" or "SELL" or "HOLD",
  "reasoning": "<2 sentences referencing actual values from tool outputs>",
  "key_driver": "TECHNICAL" or "MACRO" or "SENTIMENT",
  "risk_note": "<specific risk based on the data>"
}"""


def _parse_json(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response."""
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
        self.min_conf = cfg["signal"]["min_confidence"]
        self.timeout  = 3.0  # seconds — max time for LLM loop

        # Init LLM client
        self.llm = get_llm_client()
        logger.info(f"  LLM client initialized — model={MODEL}")

        # Tool registry — populated in _init_tools()
        self.tools: List[dict] = []
        self.tool_registry: Dict[str, callable] = {}

    def _init_tools(self, macro_agent, tech_agent, sent_agent,
                    macro_features, tech_df, sent_features):
        """
        Build the combined tools list and registry.
        Pre-fetches all ML model results so tool calls return instantly.
        """
        # Pre-fetch all results
        macro_result = macro_agent.run_macro_tool(macro_features)
        tech_agent.pre_cache_result(tech_df)
        sent_result = sent_agent.run_sentiment_tool(sent_features)

        # Store for fallback
        self._cached_macro = macro_result
        self._cached_tech = tech_agent._cached_result
        self._cached_sent = sent_result

        # Tool definitions the LLM sees
        self.tools = [
            macro_agent.MACRO_TOOL_SCHEMA,
            tech_agent.TECHNICAL_TOOL_SCHEMA,
            sent_agent.SENTIMENT_TOOL_SCHEMA,
        ]

        # Tool name → function that returns cached result
        self.tool_registry = {
            "run_macro_model": lambda **kwargs: self._cached_macro,
            "run_technical_model": lambda **kwargs: tech_agent.run_technical_tool(
                kwargs.get("pair", "")
            ),
            "run_sentiment_model": lambda **kwargs: self._cached_sent,
        }

    def run(self, pair: str, macro_agent, tech_agent, sent_agent,
            macro_features, tech_df, sent_features,
            headlines: List[str]) -> Dict:
        """
        Main entry point. Runs the full agentic LLM loop with pre-fetched tools.
        Falls back to rule-based if LLM fails or times out.
        """
        # ── Pre-fetch all ML results ──────────────────────────────────────
        self._init_tools(macro_agent, tech_agent, sent_agent,
                         macro_features, tech_df, sent_features)

        # ── Build messages ────────────────────────────────────────────────
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Generate the trading signal for {pair} at "
                    f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}.\n\n"
                    f"Headlines:\n" +
                    "\n".join(f"  - {h}" for h in headlines[:5]) if headlines else
                    "  - No headlines available"
                )
            }
        ]

        direction   = None
        reasoning   = ""
        key_driver  = ""
        risk_note   = ""
        source      = "llm"

        t_start = time.time()

        try:
            # ── Agentic loop ──────────────────────────────────────────────
            while True:
                # Timeout check
                if time.time() - t_start > self.timeout:
                    raise TimeoutError("LLM loop timeout")

                response = self.llm.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    max_tokens=400,
                    temperature=0.1,
                )

                msg = response.choices[0].message

                # No tool calls → LLM has final answer
                if not msg.tool_calls:
                    parsed = _parse_json(msg.content or "")
                    if parsed and "direction" in parsed:
                        direction  = parsed.get("direction", "HOLD").upper()
                        reasoning  = parsed.get("reasoning", "")
                        key_driver = parsed.get("key_driver", "")
                        risk_note  = parsed.get("risk_note", "")
                    break

                # Execute tool calls
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments) if tc.function.arguments else {}
                    fn      = self.tool_registry.get(fn_name)

                    if fn:
                        result = fn(**fn_args)
                        print(f"🔁 LLM tool call: {fn_name}")
                    else:
                        result = {"error": f"Unknown tool: {fn_name}"}

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    })

        except Exception as e:
            logger.warning(f"LLM error: {e} — using fallback")
            source = "fallback"

        # ── Fallback if LLM didn't produce direction ──────────────────────
        if direction is None:
            direction  = _rule_based_direction(self._cached_macro, self._cached_tech, self._cached_sent)
            eff_label, _ = _effective_macro_dir(self._cached_macro)
            reasoning  = (
                f"Effective macro: {eff_label}. "
                f"Tech: {self._cached_tech.get('signal','HOLD')} "
                f"(conf={self._cached_tech.get('confidence',0):.2f}). "
                f"Sentiment: {self._cached_sent.get('signal','HOLD')}."
            )
            key_driver = "TECHNICAL"
            risk_note  = "Fallback signal — LLM unavailable."
            source     = "fallback"

        # Normalize
        if direction not in ("BUY", "SELL", "HOLD"):
            direction = "HOLD"

        # ── Compute confidence in Python ──────────────────────────────────
        confidence, position_size, agreement = compute_signal_confidence(
            direction, self._cached_macro, self._cached_tech, self._cached_sent
        )

        # ── Confidence gate ───────────────────────────────────────────────
        if confidence < self.min_conf:
            orig = direction
            direction     = "HOLD"
            position_size = 0.0
            reasoning     = (
                f"Conf {confidence:.3f} < threshold {self.min_conf}. "
                f"Original: {orig}. " + reasoning
            )

        elapsed = time.time() - t_start
        llm_used = "yes" if source == "llm" else "no"
        print(f"✅ Orchestrator final: {direction}, conf={confidence:.3f}")
        print(f"⏱  Full cycle: {elapsed:.2f}s | LLM: {llm_used} | Fallback: {source == 'fallback'}")

        # ── Assemble signal ────────────────────────────────────────────────
        eff_label, _ = _effective_macro_dir(self._cached_macro)
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
            "macro_regime_raw": self._cached_macro.get("regime_label", "unknown"),
            "tech_signal":      self._cached_tech.get("signal", "HOLD"),
            "sent_signal":      self._cached_sent.get("signal", "HOLD"),
            "macro_conf":       self._cached_macro.get("confidence", 0.0),
            "tech_conf":        self._cached_tech.get("confidence", 0.0),
            "sent_conf":        self._cached_sent.get("confidence", 0.0),
        }
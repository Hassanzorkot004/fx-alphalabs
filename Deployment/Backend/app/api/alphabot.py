"""AlphaBot chat endpoint — Groq-powered conversational signal explainer."""
import json
from typing import List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from groq import Groq
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.services.calendar_service import calendar_service
from app.services.signal_store import signal_store

router = APIRouter()

# Initialize Groq client
groq_client = None
logger.info(f"Checking GROQ_API_KEY: {'SET' if settings.GROQ_API_KEY else 'NOT SET'}")
if settings.GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("✓ Groq client initialized for AlphaBot")
    except Exception as e:
        logger.error(f"Groq client init failed: {e}")
        import traceback
        traceback.print_exc()
else:
    logger.warning("No GROQ_API_KEY found - AlphaBot will return fallback responses")


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    pair: str                          # e.g. "EURUSD"
    message: str
    mode: str = "simple"               # "simple" | "pro"
    history: List[ChatMessage] = []


SIMPLE_SYSTEM = """You are AlphaBot, the AI trading analyst for FX AlphaLab.

Your job: Explain forex signals to traders who may not have deep technical knowledge.

TONE & STYLE:
- Talk straight. No corporate speak, no hedging with "perhaps" and "possibly"
- If the signal is weak, say it's weak. If confidence is low, lead with that
- Use analogies when they clarify (e.g., "money flows to where it's paid more")
- Define technical terms on first use: "RSI (momentum indicator) shows..."

RESPONSE STRUCTURE:
- Lead with the bottom line: what the signal says and how confident we are
- Then explain why (macro, technical, sentiment)
- End with the caveat if there is one (low confidence, conflicting agents, etc.)
- Be complete but not verbose - say what matters, skip what doesn't

CHART CAPABILITIES:
You can show charts to visualize your explanations. When a chart would help, include a chart command:
- [CHART:price:24h] - Price action with entry/stop/target levels
- [CHART:rsi:24h] - RSI indicator over time
- [CHART:macd:24h] - MACD indicator
- [CHART:risk] - Risk/reward visualization
- [CHART:agents] - Agent confidence breakdown
- [CHART:correlation:24h] - Correlation heatmap showing how pairs move together
- [CHART:volatility:24h] - ATR volatility chart for position sizing

Use charts when:
- User asks to "show me" or "visualize" something
- Explaining technical indicators (show the RSI chart when discussing RSI)
- Discussing trade levels (show price chart with entry/stop/target)
- Explaining risk (show risk visualization)
- Discussing diversification or multiple positions (show correlation heatmap)
- Discussing position sizing or market conditions (show volatility chart)

FORBIDDEN:
- Never mention model internals (TCN, LSTM, HMM, logistic regression, etc.)
- Never invent numbers that aren't in the context
- Never say "the model thinks" - say "the analysis shows" or "the data suggests"
- Don't use trader jargon without defining it (pips, ATR, carry, etc.)

WHEN DATA IS MISSING:
- Say so directly: "We don't have sentiment data for this signal"
- Don't speculate or fill in gaps

The signal context is provided below. Answer based on it.
"""

PRO_SYSTEM = """You are AlphaBot, the quantitative analyst for FX AlphaLab.

Your job: Explain signals to experienced traders and quants who want precision.

TONE & STYLE:
- Technical and exact. Cite specific values from the context
- Skip definitions (they know what RSI is), explain implications (what THIS RSI means HERE)
- Identify the key driver: which agent/feature is driving the signal?
- When agents conflict, explain the resolution logic explicitly
- Be direct. No hand-holding, no softening language

RESPONSE STRUCTURE:
- State the signal and confidence
- Identify the primary driver (e.g., "Macro regime is the key factor here")
- Walk through each agent's contribution with exact values
- Explain how the orchestrator weighted them
- Include risk metrics when discussing trade setup

CHART CAPABILITIES:
You can show charts to support your analysis. Include chart commands when relevant:
- [CHART:price:24h] - OHLC with signal levels (periods: 1h, 4h, 24h, 7d)
- [CHART:rsi:24h] - RSI indicator
- [CHART:macd:24h] - MACD indicator
- [CHART:bb:24h] - Bollinger Bands
- [CHART:risk] - Risk/reward breakdown
- [CHART:agents] - Agent confidence data
- [CHART:correlation:24h] - Correlation matrix (risk management)
- [CHART:volatility:24h] - ATR volatility (position sizing)

Use charts to:
- Visualize technical setups
- Show indicator divergences
- Illustrate risk/reward scenarios
- Display agent agreement/conflict
- Analyze correlation risk when discussing multiple positions
- Show volatility for position sizing recommendations

TIMEFRAME CONTEXT:
Always reference agent horizons when relevant:
- Macro: 24h view
- Technical: 12h view  
- Sentiment: 8h view

FORBIDDEN:
- Never invent or interpolate values
- Don't round aggressively (use 2-3 decimal places for probabilities)
- Don't skip over conflicts - address them directly

WHEN DATA IS MISSING:
- State it: "No sentiment data available for this signal"
- Explain impact: "This reduces our confidence in the 8h outlook"

The signal context is provided below. Be precise.
"""


def build_signal_context(pair: str, mode: str) -> str:
    """Build the signal context block to inject into the system prompt."""
    signal = signal_store.get_latest_for_pair(pair)
    if not signal:
        return f"No active signal found for {pair}."

    headlines = signal_store.get_recent_headlines(pair)
    events = calendar_service.get_upcoming(hours_ahead=12)
    pair_events = [e for e in events if pair.replace("=X", "") in e.get("pairs_affected", [])]
    
    # Calculate risk metrics
    from app.services.live_context_service import calculate_risk_metrics
    current_price = signal.get("price_at_signal", 0)
    risk_metrics = calculate_risk_metrics(signal, current_price)

    if mode == "simple":
        # Build risk summary for simple mode
        risk_summary = ""
        if risk_metrics["risk_level"] != "UNKNOWN":
            risk_summary = f"""
RISK: {risk_metrics['risk_level']}
• You're risking {risk_metrics['stop_distance_pips']:.0f} pips to potentially gain {risk_metrics['target_distance_pips']:.0f} pips
• Risk/Reward: 1:{risk_metrics['risk_reward_ratio']:.1f}
• Position size: {risk_metrics['position_risk_pct']:.1f}% of account
"""
        
        ctx = f"""
═══════════════════════════════════════════
SIGNAL: {pair.replace('=X', '')} — {signal.get('direction')}
═══════════════════════════════════════════

CONFIDENCE: {signal.get('confidence', 0)*100:.0f}% | AGREEMENT: {signal.get('agent_agreement')}

WHY {signal.get('direction')}?
• Macro (24h): {signal.get('macro_regime', '?').upper()} — {_yield_direction(signal.get('yield_z', 0))}
• Technical (12h): {signal.get('tech_signal', '?')} — RSI at {signal.get('rsi14', 50):.1f} ({_rsi_label(signal.get('rsi14', 50))})
• Sentiment (8h): {signal.get('sent_signal', '?')} — {signal.get('n_articles', 0)} relevant articles

TRADE SETUP:
• Entry: {signal.get('entry_low', '?')}–{signal.get('entry_high', '?')}
• Stop: {signal.get('stop_estimate', '?')} ({risk_metrics.get('stop_distance_pips', 0):.0f} pips)
• Target: {signal.get('target_estimate', '?')} ({risk_metrics.get('target_distance_pips', 0):.0f} pips)
• Current price: {signal.get('price_at_signal', '?')}
{risk_summary}"""
    else:
        # Build risk summary for pro mode
        risk_summary = ""
        if risk_metrics["risk_level"] != "UNKNOWN":
            risk_summary = f"""
───────────────────────────────────────────
RISK METRICS
───────────────────────────────────────────
risk_level: {risk_metrics['risk_level']}
rr_ratio: {risk_metrics['risk_reward_ratio']:.2f}
position_size: {risk_metrics['position_risk_pct']:.2f}%
stop_distance: {risk_metrics['stop_distance_pips']:.1f} pips
target_distance: {risk_metrics['target_distance_pips']:.1f} pips
max_loss_estimate: {risk_metrics['max_loss_estimate']:.2f} pips (position-weighted)
"""
        
        ctx = f"""
═══════════════════════════════════════════
SIGNAL CONTEXT: {pair.replace('=X', '')}
═══════════════════════════════════════════
timestamp: {signal.get('timestamp', '')}
direction: {signal.get('direction')}
confidence: {signal.get('confidence', 0):.3f}
agreement: {signal.get('agent_agreement')}
source: {signal.get('source', 'orchestrator')}

───────────────────────────────────────────
MACRO AGENT (24h horizon)
───────────────────────────────────────────
regime: {signal.get('macro_regime')}
regime_probs: [bull={signal.get('regime_prob_bull',0):.2f}, neut={signal.get('regime_prob_neut',0):.2f}, bear={signal.get('regime_prob_bear',0):.2f}]
yield_z: {signal.get('yield_z', 0):.4f}
carry_signal: {signal.get('carry_signal', 0):.4f}
vix_z: {signal.get('vix_z', 0):.4f}

───────────────────────────────────────────
TECHNICAL AGENT (12h horizon)
───────────────────────────────────────────
signal: {signal.get('tech_signal')}
probs: [buy={signal.get('p_buy',0):.3f}, sell={signal.get('p_sell',0):.3f}, hold={signal.get('p_hold',0):.3f}]
model_confidence: {signal.get('model_conf',0):.3f}
rsi_14: {signal.get('rsi14',0):.2f}
macd_hist: {signal.get('macd_hist',0):.6f}
bb_position: {signal.get('bb_pos',0):.3f}

───────────────────────────────────────────
SENTIMENT AGENT (8h horizon)
───────────────────────────────────────────
signal: {signal.get('sent_signal')}
p_bullish: {signal.get('p_bullish',0):.3f}
n_articles: {signal.get('n_articles',0)}
sentiment_raw: {signal.get('sent_raw',0):.3f}

───────────────────────────────────────────
TRADE LEVELS
───────────────────────────────────────────
current_price: {signal.get('price_at_signal')}
atr_14: {signal.get('atr')}
entry_range: [{signal.get('entry_low')}, {signal.get('entry_high')}]
stop_loss: {signal.get('stop_estimate')}
take_profit: {signal.get('target_estimate')}
{risk_summary}
───────────────────────────────────────────
ORCHESTRATOR LOGIC
───────────────────────────────────────────
{signal.get('reasoning', 'No reasoning provided')}
"""

    # Add headlines if available
    if headlines:
        if mode == "simple":
            ctx += f"\n\nRECENT NEWS:\n" + "\n".join(f"• {h}" for h in headlines[:4])
        else:
            ctx += f"\n───────────────────────────────────────────\n"
            ctx += f"RECENT HEADLINES\n"
            ctx += f"───────────────────────────────────────────\n"
            ctx += "\n".join(f"• {h}" for h in headlines[:4])

    # Add upcoming events if available
    if pair_events:
        if mode == "simple":
            ctx += f"\n\nUPCOMING EVENTS:\n" + "\n".join(
                f"• [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
                for e in pair_events[:3]
            )
        else:
            ctx += f"\n\n───────────────────────────────────────────\n"
            ctx += f"UPCOMING CATALYSTS\n"
            ctx += f"───────────────────────────────────────────\n"
            ctx += "\n".join(
                f"[{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
                for e in pair_events[:3]
            )

    return ctx.strip()


def _pair_foreign(pair: str) -> str:
    mapping = {"EURUSD": "German", "GBPUSD": "UK", "USDJPY": "Japanese"}
    for k, v in mapping.items():
        if k in pair:
            return v
    return "foreign"


def _yield_direction(z: float) -> str:
    if z < -0.5:
        return "widening (USD more attractive)"
    if z > 0.5:
        return "narrowing (foreign currency supported)"
    return "roughly neutral"


def _rsi_label(rsi: float) -> str:
    if rsi < 30:
        return "oversold — may bounce"
    if rsi > 70:
        return "overbought — may pull back"
    return "neutral zone"


@router.post("/alphabot/chat")
async def alphabot_chat(req: ChatRequest):
    """AlphaBot chat endpoint - Groq-powered signal explainer (non-streaming)"""
    
    # Build context
    system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
    signal_ctx = build_signal_context(req.pair, req.mode)
    system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    # Try Groq API
    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_with_ctx}] + messages,
                max_tokens=400,
                temperature=0.3,
            )
            reply = response.choices[0].message.content
            return {"reply": reply, "mode": req.mode, "source": "groq"}
        except Exception as e:
            logger.error(f"AlphaBot Groq call failed: {e}")
    
    # Fallback response
    signal = signal_store.get_latest_for_pair(req.pair)
    if signal:
        fallback = (
            f"Signal for {req.pair.replace('=X', '')}: {signal.get('direction')} "
            f"(confidence {signal.get('confidence', 0)*100:.0f}%). "
            f"Macro: {signal.get('macro_regime')}, Tech: {signal.get('tech_signal')}, "
            f"Sentiment: {signal.get('sent_signal')}. "
            f"AlphaBot is temporarily unavailable (Groq API issue)."
        )
    else:
        fallback = f"No signal available for {req.pair}. AlphaBot is temporarily unavailable."
    
    return {"reply": fallback, "mode": req.mode, "source": "fallback", "error": "Groq API unavailable"}


@router.post("/alphabot/chat/stream")
async def alphabot_chat_stream(req: ChatRequest):
    """AlphaBot streaming chat endpoint - Server-Sent Events"""
    from fastapi.responses import StreamingResponse
    
    async def generate():
        # Build context
        system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
        signal_ctx = build_signal_context(req.pair, req.mode)
        system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

        messages = [{"role": m.role, "content": m.content} for m in req.history]
        messages.append({"role": "user", "content": req.message})

        # Try Groq streaming API
        if groq_client:
            try:
                stream = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": system_with_ctx}] + messages,
                    max_tokens=400,
                    temperature=0.3,
                    stream=True,
                )
                
                for chunk in stream:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
                yield f"data: {json.dumps({'content': '', 'done': True, 'source': 'groq'})}\n\n"
                return
                
            except Exception as e:
                logger.error(f"AlphaBot streaming failed: {e}")
                yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
                return
        
        # Fallback non-streaming response
        signal = signal_store.get_latest_for_pair(req.pair)
        if signal:
            fallback = (
                f"Signal for {req.pair.replace('=X', '')}: {signal.get('direction')} "
                f"(confidence {signal.get('confidence', 0)*100:.0f}%). "
                f"Macro: {signal.get('macro_regime')}, Tech: {signal.get('tech_signal')}, "
                f"Sentiment: {signal.get('sent_signal')}. "
                f"AlphaBot is temporarily unavailable (Groq API issue)."
            )
        else:
            fallback = f"No signal available for {req.pair}. AlphaBot is temporarily unavailable."
        
        yield f"data: {json.dumps({'content': fallback, 'done': True, 'source': 'fallback'})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

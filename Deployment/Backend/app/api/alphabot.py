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


SIMPLE_SYSTEM = """You are AlphaBot, the AI analyst for FX AlphaLab.

You explain forex trading signals in plain English to traders of all levels.
When in SIMPLE mode:
- Use plain language, avoid jargon
- Explain technical terms when you must use them
- Use analogies (e.g. "US bonds are paying more than German bonds — so money flows to the dollar")
- Keep responses concise — 2-4 sentences unless a detailed breakdown is requested
- Never mention model internals (HMM, TCN, LSTM, LogisticRegression)
- Talk about what it means for the trader, not what the model computed

Current signal context is provided. Answer questions about it honestly.
If confidence is low or the signal is a HOLD, say so clearly.
Never invent numbers that aren't in the context.
"""

PRO_SYSTEM = """You are AlphaBot, the quantitative analyst for FX AlphaLab.

You explain signals to experienced traders and analysts.
When in PRO mode:
- Use proper trading/macro terminology
- Reference exact values from the signal context (yield_z, p_buy, RSI, etc.)
- Explain the model's reasoning chain precisely
- Include timeframe context (macro=24h, technical=12h, sentiment=8h)
- Identify the key driver feature explicitly
- Discuss conflict resolution logic when agents disagree
- Be direct and dense — no hand-holding

Current signal context is provided. Be precise. Never fabricate values.
"""


def build_signal_context(pair: str, mode: str) -> str:
    """Build the signal context block to inject into the system prompt."""
    signal = signal_store.get_latest_for_pair(pair)
    if not signal:
        return f"No active signal found for {pair}."

    headlines = signal_store.get_recent_headlines(pair)
    events = calendar_service.get_upcoming(hours_ahead=12)
    pair_events = [e for e in events if pair.replace("=X", "") in e.get("pairs_affected", [])]

    if mode == "simple":
        ctx = f"""
CURRENT SIGNAL — {pair.replace('=X', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0)*100:.0f}%

What each analyst sees:
- Macro (24h view): {signal.get('macro_regime', '?').upper()} — yield spread between US and {_pair_foreign(pair)} bonds is {_yield_direction(signal.get('yield_z', 0))}
- Technical (12h view): {signal.get('tech_signal', '?')} — RSI is {signal.get('rsi14', 50):.1f} ({_rsi_label(signal.get('rsi14', 50))})
- Sentiment (8h view): {signal.get('sent_signal', '?')} — {signal.get('n_articles', 0)} relevant news articles

Current price: {signal.get('price_at_signal', '?')}
"""
    else:
        ctx = f"""
SIGNAL CONTEXT — {pair.replace('=X', '')} — {signal.get('timestamp', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0):.3f} | Source: {signal.get('source')}

MACRO AGENT (24h horizon):
  regime: {signal.get('macro_regime')} | probs: bull={signal.get('regime_prob_bull',0):.2f} neut={signal.get('regime_prob_neut',0):.2f} bear={signal.get('regime_prob_bear',0):.2f}
  yield_z: {signal.get('yield_z', 0):.4f} | carry_signal: {signal.get('carry_signal', 0):.4f} | vix_z: {signal.get('vix_z', 0):.4f}

TECHNICAL AGENT (12h horizon):
  signal: {signal.get('tech_signal')} | P(BUY)={signal.get('p_buy',0):.3f} P(SELL)={signal.get('p_sell',0):.3f} P(HOLD)={signal.get('p_hold',0):.3f}
  model_conf: {signal.get('model_conf',0):.3f} | RSI14: {signal.get('rsi14',0):.2f} | MACD_hist: {signal.get('macd_hist',0):.6f} | BB_pos: {signal.get('bb_pos',0):.3f}

SENTIMENT AGENT (8h horizon):
  signal: {signal.get('sent_signal')} | P(bullish): {signal.get('p_bullish',0):.3f} | n_articles: {signal.get('n_articles',0)} | sent_raw: {signal.get('sent_raw',0):.3f}

TRADE LEVELS:
  price: {signal.get('price_at_signal')} | ATR: {signal.get('atr')}
  entry: {signal.get('entry_low')}–{signal.get('entry_high')} | stop: {signal.get('stop_estimate')} | target: {signal.get('target_estimate')}

ORCHESTRATOR REASONING: {signal.get('reasoning', '')}
"""

    if headlines:
        ctx += f"\nRECENT HEADLINES:\n" + "\n".join(f"  - {h}" for h in headlines[:4])

    if pair_events:
        ctx += f"\nUPCOMING EVENTS:\n" + "\n".join(
            f"  - [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
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

"""AlphaBot chat endpoint — Groq-powered conversational signal explainer."""

import json
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from groq import Groq
from loguru import logger
from pydantic import BaseModel

from app.auth.security import get_current_user
from app.config import settings
from app.services.calendar_service import calendar_service
from app.services.signal_store import signal_store

router = APIRouter()

groq_client = None
logger.info(f"Checking GROQ_API_KEY: {'SET' if settings.GROQ_API_KEY else 'NOT SET'}")
if settings.GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=settings.GROQ_API_KEY)
        logger.info("✓ Groq client initialized for AlphaBot")
    except Exception as e:
        logger.error(f"Groq client init failed: {e}")
else:
    logger.warning("No GROQ_API_KEY found - AlphaBot will return fallback responses")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    pair: str
    message: str
    mode: str = "simple"
    history: List[ChatMessage] = []


SIMPLE_SYSTEM = """You are AlphaBot, the AI analyst for FX AlphaLab.

You explain forex trading signals in plain English to traders of all levels.
When in SIMPLE mode:
- Use plain language, avoid jargon
- Explain technical terms when you must use them
- Keep responses concise — 2-4 sentences unless a detailed breakdown is requested
- Never mention model internals
- Talk about what it means for the trader

Current signal context is provided. Answer questions honestly.
Never invent numbers that aren't in the context.
"""

PRO_SYSTEM = """You are AlphaBot, the quantitative analyst for FX AlphaLab.

You explain signals to experienced traders and analysts.
When in PRO mode:
- Use proper trading/macro terminology
- Reference exact values from the signal context
- Explain the model's reasoning chain precisely
- Include timeframe context
- Identify the key driver feature explicitly
- Be direct and dense

Current signal context is provided. Be precise. Never fabricate values.
"""


def build_signal_context(pair: str, mode: str) -> str:
    signal = signal_store.get_latest_for_pair(pair)
    if not signal:
        return f"No active signal found for {pair}."

    headlines = signal_store.get_recent_headlines(pair)
    events = calendar_service.get_upcoming(hours_ahead=12)
    pair_events = [
        e for e in events
        if pair.replace("=X", "") in e.get("pairs_affected", [])
    ]

    if mode == "simple":
        ctx = f"""
CURRENT SIGNAL — {pair.replace('=X', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0)*100:.0f}%

What each analyst sees:
- Macro: {signal.get('macro_regime', '?').upper()}
- Technical: {signal.get('tech_signal', '?')}
- Sentiment: {signal.get('sent_signal', '?')}
- Current price: {signal.get('price_at_signal', '?')}
"""
    else:
        ctx = f"""
SIGNAL CONTEXT — {pair.replace('=X', '')} — {signal.get('timestamp', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0):.3f}

MACRO:
  regime: {signal.get('macro_regime')}
  yield_z: {signal.get('yield_z', 0):.4f}
  vix_z: {signal.get('vix_z', 0):.4f}

TECHNICAL:
  signal: {signal.get('tech_signal')}
  P(BUY): {signal.get('p_buy',0):.3f}
  P(SELL): {signal.get('p_sell',0):.3f}
  P(HOLD): {signal.get('p_hold',0):.3f}
  RSI14: {signal.get('rsi14',0):.2f}
  MACD_hist: {signal.get('macd_hist',0):.6f}

SENTIMENT:
  signal: {signal.get('sent_signal')}
  n_articles: {signal.get('n_articles',0)}
  sent_raw: {signal.get('sent_raw',0):.3f}

TRADE LEVELS:
  price: {signal.get('price_at_signal')}
  entry: {signal.get('entry_low')}–{signal.get('entry_high')}
  stop: {signal.get('stop_estimate')}
  target: {signal.get('target_estimate')}

ORCHESTRATOR REASONING:
{signal.get('reasoning', '')}
"""

    if headlines:
        ctx += "\nRECENT HEADLINES:\n" + "\n".join(
            f"  - {h}" for h in headlines[:4]
        )

    if pair_events:
        ctx += "\nUPCOMING EVENTS:\n" + "\n".join(
            f"  - [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
            for e in pair_events[:3]
        )

    return ctx.strip()


@router.post("/alphabot/chat")
async def alphabot_chat(
    req: ChatRequest,
    current_user=Depends(get_current_user),
):
    system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
    signal_ctx = build_signal_context(req.pair, req.mode)
    system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_with_ctx}] + messages,
                max_tokens=400,
                temperature=0.3,
            )

            reply = response.choices[0].message.content

            return {
                "reply": reply,
                "mode": req.mode,
                "source": "groq",
                "user": current_user,
            }

        except Exception as e:
            logger.error(f"AlphaBot Groq call failed: {e}")

    signal = signal_store.get_latest_for_pair(req.pair)

    if signal:
        fallback = (
            f"Signal for {req.pair.replace('=X', '')}: {signal.get('direction')} "
            f"(confidence {signal.get('confidence', 0)*100:.0f}%). "
            f"Macro: {signal.get('macro_regime')}, Tech: {signal.get('tech_signal')}, "
            f"Sentiment: {signal.get('sent_signal')}."
        )
    else:
        fallback = f"No signal available for {req.pair}."

    return {
        "reply": fallback,
        "mode": req.mode,
        "source": "fallback",
        "error": "Groq API unavailable",
    }


@router.post("/alphabot/chat/stream")
async def alphabot_chat_stream(
    req: ChatRequest,
    current_user=Depends(get_current_user),
):
    async def generate():
        system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
        signal_ctx = build_signal_context(req.pair, req.mode)
        system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

        messages = [{"role": m.role, "content": m.content} for m in req.history]
        messages.append({"role": "user", "content": req.message})

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

        signal = signal_store.get_latest_for_pair(req.pair)

        if signal:
            fallback = (
                f"Signal for {req.pair.replace('=X', '')}: {signal.get('direction')} "
                f"(confidence {signal.get('confidence', 0)*100:.0f}%). "
                f"Macro: {signal.get('macro_regime')}, Tech: {signal.get('tech_signal')}, "
                f"Sentiment: {signal.get('sent_signal')}."
            )
        else:
            fallback = f"No signal available for {req.pair}."

        yield f"data: {json.dumps({'content': fallback, 'done': True, 'source': 'fallback'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
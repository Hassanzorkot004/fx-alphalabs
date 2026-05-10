"""AlphaBot chat endpoint — RAG-powered with hosted Llama 3.1 70B."""
import json
from typing import List

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from app.config import settings
from app.services.calendar_service import calendar_service
from app.services.signal_store import signal_store

router = APIRouter()

# Using hosted Llama 3.1 70B via RAG
logger.info("AlphaBot using hosted Llama 3.1 70B via RAG")


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
- Identify the key driver feature explicitly
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
Macro: {signal.get('macro_regime', '?').upper()} | Technical: {signal.get('tech_signal', '?')} | Sentiment: {signal.get('sent_signal', '?')}
Current price: {signal.get('price_at_signal', '?')}
"""
    else:
        ctx = f"""
SIGNAL CONTEXT — {pair.replace('=X', '')} — {signal.get('timestamp', '')}
Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0):.3f} | Source: {signal.get('source')}
MACRO: regime={signal.get('macro_regime')} yield_z={signal.get('yield_z', 0):.4f} vix_z={signal.get('vix_z', 0):.4f}
TECHNICAL: signal={signal.get('tech_signal')} P(BUY)={signal.get('p_buy',0):.3f} P(SELL)={signal.get('p_sell',0):.3f}
SENTIMENT: signal={signal.get('sent_signal')} P(bullish)={signal.get('p_bullish',0):.3f} n_articles={signal.get('n_articles',0)}
REASONING: {signal.get('reasoning', '')}
"""

    if headlines:
        ctx += f"\nRECENT HEADLINES:\n" + "\n".join(f"  - {h}" for h in headlines[:4])

    if pair_events:
        ctx += f"\nUPCOMING EVENTS:\n" + "\n".join(
            f"  - [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
            for e in pair_events[:3]
        )

    return ctx.strip()


@router.post("/alphabot/chat")
async def alphabot_chat(req: ChatRequest):
    """AlphaBot chat endpoint - RAG-powered with hosted Llama 3.1 70B"""
    from fx_alphalab.llm.rag import AlphaBotRAG

    signal_ctx = build_signal_context(req.pair, req.mode)

    try:
        from main import rag_store
    except Exception:
        rag_store = AlphaBotRAG()

    full_query = (
        f"Pair: {req.pair}\n"
        f"Signal context:\n{signal_ctx}\n\n"
        f"User question: {req.message}"
    )

    try:
        reply = rag_store.chat(full_query)
        return {"reply": reply, "mode": req.mode, "source": "llm_rag"}
    except Exception as e:
        logger.error(f"AlphaBot RAG call failed: {e}")

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
    return {"reply": fallback, "mode": req.mode, "source": "fallback"}


@router.post("/alphabot/chat/stream")
async def alphabot_chat_stream(req: ChatRequest):
    """AlphaBot streaming chat endpoint"""
    from fx_alphalab.llm.rag import AlphaBotRAG
    from fx_alphalab.llm.client import get_llm_client, MODEL

    async def generate():
        signal_ctx = build_signal_context(req.pair, req.mode)

        try:
            from main import rag_store
        except Exception:
            rag_store = AlphaBotRAG()

        full_query = (
            f"Pair: {req.pair}\n"
            f"Signal context:\n{signal_ctx}\n\n"
            f"User question: {req.message}"
        )

        try:
            context_docs = rag_store._smart_retrieve(full_query) if rag_store else []
            context = "\n\n".join(f"[{i+1}] {d}" for i, d in enumerate(context_docs)) if context_docs else "No data available."
            system_prompt = rag_store.CHAT_PROMPT.format(context=context) if rag_store else "You are AlphaBot."

            llm = get_llm_client()
            stream = llm.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_query},
                ],
                max_tokens=500, temperature=0.3, stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content, 'done': False})}\n\n"
            yield f"data: {json.dumps({'content': '', 'done': True, 'source': 'llm_rag'})}\n\n"
            return
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
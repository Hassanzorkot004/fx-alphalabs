# """AlphaBot chat endpoint — Groq-powered conversational signal explainer."""
# import json
# from typing import List

# from fastapi import APIRouter
# from fastapi.responses import StreamingResponse
# from groq import Groq
# from loguru import logger
# from pydantic import BaseModel

# from app.config import settings
# from app.services.calendar_service import calendar_service
# from app.services.signal_store import signal_store

# router = APIRouter()

# # Initialize Groq client
# groq_client = None
# logger.info(f"Checking GROQ_API_KEY: {'SET' if settings.GROQ_API_KEY else 'NOT SET'}")
# if settings.GROQ_API_KEY:
#     try:
#         groq_client = Groq(api_key=settings.GROQ_API_KEY)
#         logger.info("✓ Groq client initialized for AlphaBot")
#     except Exception as e:
#         logger.error(f"Groq client init failed: {e}")
#         import traceback
#         traceback.print_exc()
# else:
#     logger.warning("No GROQ_API_KEY found - AlphaBot will return fallback responses")


# class ChatMessage(BaseModel):
#     role: str   # "user" | "assistant"
#     content: str


# class ChatRequest(BaseModel):
#     pair: str                          # e.g. "EURUSD"
#     message: str
#     mode: str = "simple"               # "simple" | "pro"
#     history: List[ChatMessage] = []


# SIMPLE_SYSTEM = """You are AlphaBot, the AI analyst for FX AlphaLab.

# You explain forex trading signals in plain English to traders of all levels.
# When in SIMPLE mode:
# - Use plain language, avoid jargon
# - Explain technical terms when you must use them
# - Use analogies (e.g. "US bonds are paying more than German bonds — so money flows to the dollar")
# - Keep responses concise — 2-4 sentences unless a detailed breakdown is requested
# - Never mention model internals (HMM, TCN, LSTM, LogisticRegression)
# - Talk about what it means for the trader, not what the model computed

# Current signal context is provided. Answer questions about it honestly.
# If confidence is low or the signal is a HOLD, say so clearly.
# Never invent numbers that aren't in the context.
# """

# PRO_SYSTEM = """You are AlphaBot, the quantitative analyst for FX AlphaLab.

# You explain signals to experienced traders and analysts.
# When in PRO mode:
# - Use proper trading/macro terminology
# - Reference exact values from the signal context (yield_z, p_buy, RSI, etc.)
# - Explain the model's reasoning chain precisely
# - Include timeframe context (macro=24h, technical=12h, sentiment=8h)
# - Identify the key driver feature explicitly
# - Discuss conflict resolution logic when agents disagree
# - Be direct and dense — no hand-holding

# Current signal context is provided. Be precise. Never fabricate values.
# """


# def build_signal_context(pair: str, mode: str) -> str:
#     """Build the signal context block to inject into the system prompt."""
#     signal = signal_store.get_latest_for_pair(pair)
#     if not signal:
#         return f"No active signal found for {pair}."

#     headlines = signal_store.get_recent_headlines(pair)
#     events = calendar_service.get_upcoming(hours_ahead=12)
#     pair_events = [e for e in events if pair.replace("=X", "") in e.get("pairs_affected", [])]

#     if mode == "simple":
#         ctx = f"""
# CURRENT SIGNAL — {pair.replace('=X', '')}
# Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0)*100:.0f}%

# What each analyst sees:
# - Macro (24h view): {signal.get('macro_regime', '?').upper()} — yield spread between US and {_pair_foreign(pair)} bonds is {_yield_direction(signal.get('yield_z', 0))}
# - Technical (12h view): {signal.get('tech_signal', '?')} — RSI is {signal.get('rsi14', 50):.1f} ({_rsi_label(signal.get('rsi14', 50))})
# - Sentiment (8h view): {signal.get('sent_signal', '?')} — {signal.get('n_articles', 0)} relevant news articles

# Current price: {signal.get('price_at_signal', '?')}
# """
#     else:
#         ctx = f"""
# SIGNAL CONTEXT — {pair.replace('=X', '')} — {signal.get('timestamp', '')}
# Direction: {signal.get('direction')} | Agreement: {signal.get('agent_agreement')} | Confidence: {signal.get('confidence', 0):.3f} | Source: {signal.get('source')}

# MACRO AGENT (24h horizon):
#   regime: {signal.get('macro_regime')} | probs: bull={signal.get('regime_prob_bull',0):.2f} neut={signal.get('regime_prob_neut',0):.2f} bear={signal.get('regime_prob_bear',0):.2f}
#   yield_z: {signal.get('yield_z', 0):.4f} | carry_signal: {signal.get('carry_signal', 0):.4f} | vix_z: {signal.get('vix_z', 0):.4f}

# TECHNICAL AGENT (12h horizon):
#   signal: {signal.get('tech_signal')} | P(BUY)={signal.get('p_buy',0):.3f} P(SELL)={signal.get('p_sell',0):.3f} P(HOLD)={signal.get('p_hold',0):.3f}
#   model_conf: {signal.get('model_conf',0):.3f} | RSI14: {signal.get('rsi14',0):.2f} | MACD_hist: {signal.get('macd_hist',0):.6f} | BB_pos: {signal.get('bb_pos',0):.3f}

# SENTIMENT AGENT (8h horizon):
#   signal: {signal.get('sent_signal')} | P(bullish): {signal.get('p_bullish',0):.3f} | n_articles: {signal.get('n_articles',0)} | sent_raw: {signal.get('sent_raw',0):.3f}

# TRADE LEVELS:
#   price: {signal.get('price_at_signal')} | ATR: {signal.get('atr')}
#   entry: {signal.get('entry_low')}–{signal.get('entry_high')} | stop: {signal.get('stop_estimate')} | target: {signal.get('target_estimate')}

# ORCHESTRATOR REASONING: {signal.get('reasoning', '')}
# """

#     if headlines:
#         ctx += f"\nRECENT HEADLINES:\n" + "\n".join(f"  - {h}" for h in headlines[:4])

#     if pair_events:
#         ctx += f"\nUPCOMING EVENTS:\n" + "\n".join(
#             f"  - [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
#             for e in pair_events[:3]
#         )

#     return ctx.strip()


# def _pair_foreign(pair: str) -> str:
#     mapping = {"EURUSD": "German", "GBPUSD": "UK", "USDJPY": "Japanese"}
#     for k, v in mapping.items():
#         if k in pair:
#             return v
#     return "foreign"


# def _yield_direction(z: float) -> str:
#     if z < -0.5:
#         return "widening (USD more attractive)"
#     if z > 0.5:
#         return "narrowing (foreign currency supported)"
#     return "roughly neutral"


# def _rsi_label(rsi: float) -> str:
#     if rsi < 30:
#         return "oversold — may bounce"
#     if rsi > 70:
#         return "overbought — may pull back"
#     return "neutral zone"


# @router.post("/alphabot/chat")
# async def alphabot_chat(req: ChatRequest):
#     """AlphaBot chat endpoint - Groq-powered signal explainer (non-streaming)"""
    
#     # Build context
#     system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
#     signal_ctx = build_signal_context(req.pair, req.mode)
#     system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

#     messages = [{"role": m.role, "content": m.content} for m in req.history]
#     messages.append({"role": "user", "content": req.message})

#     # Try Groq API
#     if groq_client:
#         try:
#             response = groq_client.chat.completions.create(
#                 model="llama-3.3-70b-versatile",
#                 messages=[{"role": "system", "content": system_with_ctx}] + messages,
#                 max_tokens=400,
#                 temperature=0.3,
#             )
#             reply = response.choices[0].message.content
#             return {"reply": reply, "mode": req.mode, "source": "groq"}
#         except Exception as e:
#             logger.error(f"AlphaBot Groq call failed: {e}")
    
#     # Fallback response
#     signal = signal_store.get_latest_for_pair(req.pair)
#     if signal:
#         fallback = (
#             f"Signal for {req.pair.replace('=X', '')}: {signal.get('direction')} "
#             f"(confidence {signal.get('confidence', 0)*100:.0f}%). "
#             f"Macro: {signal.get('macro_regime')}, Tech: {signal.get('tech_signal')}, "
#             f"Sentiment: {signal.get('sent_signal')}. "
#             f"AlphaBot is temporarily unavailable (Groq API issue)."
#         )
#     else:
#         fallback = f"No signal available for {req.pair}. AlphaBot is temporarily unavailable."
    
#     return {"reply": fallback, "mode": req.mode, "source": "fallback", "error": "Groq API unavailable"}


# @router.post("/alphabot/chat/stream")
# async def alphabot_chat_stream(req: ChatRequest):
#     """AlphaBot streaming chat endpoint - Server-Sent Events"""
#     from fastapi.responses import StreamingResponse
    
#     async def generate():
#         # Build context
#         system = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
#         signal_ctx = build_signal_context(req.pair, req.mode)
#         system_with_ctx = system + f"\n\n---\n{signal_ctx}\n---"

#         messages = [{"role": m.role, "content": m.content} for m in req.history]
#         messages.append({"role": "user", "content": req.message})

#         # Try Groq streaming API
#         if groq_client:
#             try:
#                 stream = groq_client.chat.completions.create(
#                     model="llama-3.3-70b-versatile",
#                     messages=[{"role": "system", "content": system_with_ctx}] + messages,
#                     max_tokens=400,
#                     temperature=0.3,
#                     stream=True,
#                 )
                
#                 for chunk in stream:
#                     if chunk.choices[0].delta.content:
#                         content = chunk.choices[0].delta.content
#                         yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"
                
#                 yield f"data: {json.dumps({'content': '', 'done': True, 'source': 'groq'})}\n\n"
#                 return
                
#             except Exception as e:
#                 logger.error(f"AlphaBot streaming failed: {e}")
#                 yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"
#                 return
        
#         # Fallback non-streaming response
#         signal = signal_store.get_latest_for_pair(req.pair)
#         if signal:
#             fallback = (
#                 f"Signal for {req.pair.replace('=X', '')}: {signal.get('direction')} "
#                 f"(confidence {signal.get('confidence', 0)*100:.0f}%). "
#                 f"Macro: {signal.get('macro_regime')}, Tech: {signal.get('tech_signal')}, "
#                 f"Sentiment: {signal.get('sent_signal')}. "
#                 f"AlphaBot is temporarily unavailable (Groq API issue)."
#             )
#         else:
#             fallback = f"No signal available for {req.pair}. AlphaBot is temporarily unavailable."
        
#         yield f"data: {json.dumps({'content': fallback, 'done': True, 'source': 'fallback'})}\n\n"
    
#     return StreamingResponse(generate(), media_type="text/event-stream")



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
else:
    logger.warning("No GROQ_API_KEY — AlphaBot will return fallback responses")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    pair: str
    message: str
    mode: str = "simple"
    history: List[ChatMessage] = []


# ── System Prompts ────────────────────────────────────────────────────────────

SIMPLE_SYSTEM = """You are AlphaBot, the AI trading assistant for FX AlphaLab.

You explain forex signals to traders in plain, conversational language.

RULES:
- NEVER mention model internals: no HMM, TCN, LSTM, yield_z, p_buy, p_sell,
  mac_str, model_conf, LogisticRegression, or any variable names
- Translate everything into plain market language:
    macro bearish     → "the macro backdrop is weak, fundamentals favor selling"
    macro bullish     → "macro is supportive, fundamentals favor buying"
    macro neutral     → "macro gives no strong edge here"
    tech SELL         → "price action is turning bearish, momentum is down"
    tech BUY          → "price action is bullish, momentum is building"
    low confidence    → "the signal is not very strong — size down or wait"
    HIGH conflict     → "our models disagree — better to stay flat"
    LOW-NEWS          → "it's quiet in the news, no major catalyst right now"
- Keep it SHORT: 2-4 sentences max unless trader asks for detail
- Be honest about weak signals — never oversell
- If asked for trade levels, give them clearly: entry / stop / target / R:R
- Sound like a helpful senior trader briefing a junior, not a robot report
- If upcoming events are in context, mention the risk naturally
- If headlines are relevant, reference them naturally

Never invent prices or values not in the context provided.
"""

PRO_SYSTEM = """You are AlphaBot, the senior quantitative analyst for FX AlphaLab.

You brief experienced traders and PMs on signal quality and market structure.

RULES:
- Use proper FX trading desk terminology
- Translate model outputs into market language — never cite raw variable names:
    yield curve flattening → "risk-off pressure building, safe havens bid"
    yield curve steepening → "reflation trade, USD broadly supported"
    bearish momentum confirmed → "technicals aligned, sell-side in control"
    macro/tech divergence → "CONFLICT — agents disagree, reduce sizing to 50%"
    overbought RSI → "overbought on short-term oscillators, watch for fades"
    oversold RSI → "oversold, mean-reversion risk — tighten stop"
- Always reference agent timeframes: macro view=24h, tech signal=12h, sent=8h
- Mention R:R explicitly if trade levels are available
- Flag upcoming calendar risk clearly if events are within 12h
- Be dense, precise, no hand-holding — max 6 sentences unless breakdown asked
- If multiple agents conflict, explain WHY and what it means for position sizing

Never fabricate values not explicitly provided in the signal context.
"""


# ── Context Builder ───────────────────────────────────────────────────────────

def build_signal_context(pair: str, mode: str) -> str:
    signal = signal_store.get_latest_for_pair(pair)
    if not signal:
        return f"No active signal found for {pair}."

    headlines  = signal_store.get_recent_headlines(pair)
    events     = calendar_service.get_upcoming(hours_ahead=12)
    pair_clean = pair.replace("=X", "")
    pair_events = [
        e for e in events
        if pair_clean in e.get("pairs_affected", [])
    ]

    # ── Compute trade levels ──────────────────────────────────────────────────
    price      = signal.get("price_at_signal")
    atr        = signal.get("atr")
    direction  = signal.get("direction", "HOLD")
    stop_pips  = _compute_stop_pips(signal)
    target_pips = _compute_target_pips(signal)
    rr         = _compute_rr(signal)

    if mode == "simple":
        # ── Macro language ────────────────────────────────────────────────────
        regime   = signal.get("macro_regime", "neutral")
        yield_z  = signal.get("yield_z", 0.0)
        vix_z    = signal.get("vix_z", 0.0)
        rsi      = signal.get("rsi14", 50.0)

        macro_desc = _macro_description_simple(regime, yield_z, vix_z, pair_clean)
        tech_desc  = _tech_description_simple(signal)
        sent_desc  = _sent_description_simple(signal)
        conf_pct   = signal.get("confidence", 0) * 100
        agreement  = signal.get("agent_agreement", "PARTIAL")
        conf_desc  = _confidence_description(conf_pct, agreement)

        ctx = f"""
CURRENT SIGNAL — {pair_clean}
Direction: {direction} | Confidence: {conf_pct:.0f}% ({conf_desc})

What's happening in the market:
- Big picture (24h): {macro_desc}
- Price action (12h): {tech_desc}
- News sentiment (8h): {sent_desc}
"""
        if price:
            ctx += f"\nCurrent price: {price}"
        if stop_pips and target_pips and rr and direction != "HOLD":
            ctx += f"""
Trade setup:
  Entry: ~{price}
  Stop loss: {signal.get('stop_estimate', '?')} ({stop_pips} pips risk)
  Target: {signal.get('target_estimate', '?')} ({target_pips} pips)
  Risk/Reward: {rr}
"""

    else:
        # PRO mode — full technical context in market language
        regime    = signal.get("macro_regime", "neutral")
        yield_z   = signal.get("yield_z", 0.0)
        vix_z     = signal.get("vix_z", 0.0)
        carry     = signal.get("carry_signal", 0.0)
        rsi       = signal.get("rsi14", 50.0)
        macd      = signal.get("macd_hist", 0.0)
        bb_pos    = signal.get("bb_pos", 0.5)
        p_buy     = signal.get("p_buy", 0.0)
        p_sell    = signal.get("p_sell", 0.0)
        p_hold    = signal.get("p_hold", 0.0)
        p_bullish = signal.get("p_bullish", 0.0)
        n_articles = signal.get("n_articles", 0)
        agreement  = signal.get("agent_agreement", "PARTIAL")
        conf       = signal.get("confidence", 0.0)

        ctx = f"""
SIGNAL BRIEF — {pair_clean} | {signal.get('timestamp', '')}
Direction: {direction} | Agreement: {agreement} | Confidence: {conf:.0f}%

MACRO VIEW (24h):
  Regime: {regime.upper()} — {_macro_description_pro(regime, yield_z, vix_z, pair_clean)}
  Carry: {_carry_description(carry, pair_clean)}

TECHNICAL VIEW (12h):
  Signal: {signal.get('tech_signal')} — {_tech_description_pro(signal, p_buy, p_sell, p_hold)}
  RSI: {rsi:.1f} ({_rsi_label(rsi)}) | MACD hist: {"positive" if macd > 0 else "negative"} | BB pos: {bb_pos:.2f}

SENTIMENT VIEW (8h):
  Signal: {signal.get('sent_signal')} — {_sent_description_pro(p_bullish, n_articles)}

TRADE LEVELS:
  Entry: ~{price} | Stop: {signal.get('stop_estimate', 'n/a')} | Target: {signal.get('target_estimate', 'n/a')}
  Stop risk: {stop_pips} pips | Target: {target_pips} pips | R:R = {rr}

ORCHESTRATOR REASONING: {signal.get('reasoning', 'n/a')}
"""

    if headlines:
        ctx += "\nRECENT HEADLINES:\n"
        ctx += "\n".join(f"  - {h}" for h in headlines[:4])

    if pair_events:
        ctx += "\nUPCOMING CALENDAR RISK:\n"
        ctx += "\n".join(
            f"  - [{e.get('impact','').upper()}] {e.get('event')} in {e.get('hours_until', 0):.1f}h"
            for e in pair_events[:3]
        )

    return ctx.strip()


# ── Market Language Translators ───────────────────────────────────────────────

def _macro_description_simple(regime: str, yield_z: float, vix_z: float, pair: str) -> str:
    foreign = {"EURUSD": "European", "GBPUSD": "British", "USDJPY": "Japanese"}.get(pair, "foreign")
    if regime == "bearish":
        if yield_z < -0.3:
            return f"macro backdrop is weak — yield curve flattening suggests risk-off, {foreign} assets under pressure"
        return f"macro regime is bearish — fundamentals favor selling {pair[:3]}"
    elif regime == "bullish":
        if yield_z > 0.3:
            return f"macro is supportive — steepening yield curve and USD demand in play"
        return f"macro regime is bullish — fundamentals support buying"
    else:
        return "macro is neutral — no strong directional bias from fundamentals"


def _macro_description_pro(regime: str, yield_z: float, vix_z: float, pair: str) -> str:
    if yield_z < -0.5:
        return "yield curve flattening, risk-off environment, safe haven bid"
    elif yield_z > 0.5:
        return "curve steepening, reflation bias, USD broadly supported"
    elif regime == "bearish":
        return "bearish regime, macro headwinds intact"
    elif regime == "bullish":
        return "bullish regime, macro tailwinds supportive"
    return "neutral regime, no macro edge"


def _carry_description(carry: float, pair: str) -> str:
    if carry > 0.3:
        return f"carry favors USD side — rate differential is attractive"
    elif carry < -0.3:
        return f"carry unfavorable for USD — rate differential supports foreign currency"
    return "carry roughly neutral"


def _tech_description_simple(signal: dict) -> str:
    tech = signal.get("tech_signal", "HOLD")
    rsi  = signal.get("rsi14", 50.0)
    if tech == "SELL":
        base = "price action is turning bearish, momentum is to the downside"
        if rsi > 65:
            base += " — market was overbought and is now fading"
        return base
    elif tech == "BUY":
        base = "price action is bullish, momentum is building to the upside"
        if rsi < 35:
            base += " — market was oversold and is now recovering"
        return base
    return "technical signals are mixed — no clear directional conviction"


def _tech_description_pro(signal: dict, p_buy: float, p_sell: float, p_hold: float) -> str:
    tech = signal.get("tech_signal", "HOLD")
    dominant = max(p_buy, p_sell, p_hold)
    if tech == "SELL":
        strength = "strong" if p_sell > 0.55 else "moderate"
        return f"{strength} bearish momentum, sell-side in control"
    elif tech == "BUY":
        strength = "strong" if p_buy > 0.55 else "moderate"
        return f"{strength} bullish momentum, buy-side accumulating"
    return "technical conviction weak — model uncertain on direction"


def _sent_description_simple(signal: dict) -> str:
    sent = signal.get("sent_signal", "HOLD")
    n    = signal.get("n_articles", 0)
    if "LOW" in str(sent):
        return f"quiet session — only {n} relevant headlines, no major catalyst"
    elif "BUY" in str(sent):
        return f"news flow is positive — {n} articles tilting bullish"
    elif "SELL" in str(sent):
        return f"negative news flow — {n} articles adding downside pressure"
    return f"sentiment is neutral across {n} articles"


def _sent_description_pro(p_bullish: float, n_articles: int) -> str:
    if n_articles < 3:
        return f"low news flow ({n_articles} articles) — sentiment unreliable"
    if p_bullish > 0.6:
        return f"bullish sentiment bias ({p_bullish:.0%} bullish across {n_articles} articles)"
    elif p_bullish < 0.4:
        return f"bearish sentiment ({p_bullish:.0%} bullish across {n_articles} articles)"
    return f"neutral sentiment ({p_bullish:.0%} bullish, {n_articles} articles)"


def _confidence_description(conf_pct: float, agreement: str) -> str:
    if agreement == "CONFLICT":
        return "agents disagree — stay flat or reduce size"
    if conf_pct >= 70:
        return "high conviction"
    if conf_pct >= 55:
        return "moderate conviction"
    return "low conviction — size down"


def _rsi_label(rsi: float) -> str:
    if rsi < 30:
        return "oversold, mean-reversion risk"
    if rsi > 70:
        return "overbought, watch for fades"
    return "neutral"


def _compute_stop_pips(signal: dict) -> str:
    try:
        price  = float(signal.get("price_at_signal", 0))
        stop   = float(signal.get("stop_estimate", 0))
        pair   = signal.get("pair", "EURUSD")
        mult   = 100 if "JPY" in pair else 10000
        pips   = abs(price - stop) * mult
        return f"{pips:.1f}"
    except Exception:
        return "n/a"


def _compute_target_pips(signal: dict) -> str:
    try:
        price  = float(signal.get("price_at_signal", 0))
        target = float(signal.get("target_estimate", 0))
        pair   = signal.get("pair", "EURUSD")
        mult   = 100 if "JPY" in pair else 10000
        pips   = abs(target - price) * mult
        return f"{pips:.1f}"
    except Exception:
        return "n/a"


def _compute_rr(signal: dict) -> str:
    try:
        price  = float(signal.get("price_at_signal", 0))
        stop   = float(signal.get("stop_estimate", 0))
        target = float(signal.get("target_estimate", 0))
        risk   = abs(price - stop)
        reward = abs(target - price)
        if risk == 0:
            return "n/a"
        return f"{reward/risk:.1f}:1"
    except Exception:
        return "n/a"


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/alphabot/chat")
async def alphabot_chat(req: ChatRequest):
    """AlphaBot chat — non-streaming"""
    system      = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
    signal_ctx  = build_signal_context(req.pair, req.mode)
    full_system = system + f"\n\n---\nSIGNAL CONTEXT:\n{signal_ctx}\n---"

    messages = [{"role": m.role, "content": m.content} for m in req.history]
    messages.append({"role": "user", "content": req.message})

    if groq_client:
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": full_system}] + messages,
                max_tokens=800,
                temperature=0.2,
            )
            reply = response.choices[0].message.content
            return {"reply": reply, "mode": req.mode, "source": "groq"}
        except Exception as e:
            logger.error(f"AlphaBot Groq call failed: {e}")

    # Fallback
    signal   = signal_store.get_latest_for_pair(req.pair)
    fallback = _fallback_response(req.pair, signal)
    return {"reply": fallback, "mode": req.mode, "source": "fallback"}


@router.post("/alphabot/chat/stream")
async def alphabot_chat_stream(req: ChatRequest):
    """AlphaBot streaming chat — Server-Sent Events"""

    async def generate():
        system      = SIMPLE_SYSTEM if req.mode == "simple" else PRO_SYSTEM
        signal_ctx  = build_signal_context(req.pair, req.mode)
        full_system = system + f"\n\n---\nSIGNAL CONTEXT:\n{signal_ctx}\n---"

        messages = [{"role": m.role, "content": m.content} for m in req.history]
        messages.append({"role": "user", "content": req.message})

        if groq_client:
            try:
                stream = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "system", "content": full_system}] + messages,
                    max_tokens=800,
                    temperature=0.2,
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

        # Fallback
        signal   = signal_store.get_latest_for_pair(req.pair)
        fallback = _fallback_response(req.pair, signal)
        yield f"data: {json.dumps({'content': fallback, 'done': True, 'source': 'fallback'})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


def _fallback_response(pair: str, signal: dict | None) -> str:
    pair_clean = pair.replace("=X", "")
    if signal:
        return (
            f"{pair_clean}: {signal.get('direction')} signal "
            f"({signal.get('confidence', 0)*100:.0f}% confidence). "
            f"Macro {signal.get('macro_regime')}, "
            f"tech {signal.get('tech_signal')}, "
            f"sentiment {signal.get('sent_signal')}. "
            f"AlphaBot is temporarily unavailable."
        )
    return f"No active signal for {pair_clean}. AlphaBot is temporarily unavailable."
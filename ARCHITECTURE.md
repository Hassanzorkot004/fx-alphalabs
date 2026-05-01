# FX AlphaLab Architecture

## Core Principle

**Run cheap models frequently to detect changes. Only call expensive LLM when those changes matter.**

This architecture saves 30-50% on API costs while maintaining sub-2-minute reaction time to market events.

---

## The 4-Layer System

### Layer 1: Real-Time Updates (Every 30 Seconds)
**What:** Price fetching + validity checks  
**Why:** Users need live feedback, but don't need new AI predictions every 30 seconds  
**Cost:** Negligible (Yahoo Finance API + simple math)

```
fetch_prices() → check_validity() → broadcast_to_frontend()
```

**Validity checks are deterministic rules, not AI:**
- Is signal expired? (age > horizon)
- Is stop loss hit? (price <= stop)
- Is target hit? (price >= target)

**Why rules, not AI?** These are known facts, not predictions. You don't need a neural network to check if `1.0815 < 1.0820`.

---

### Layer 2: Technical Monitoring (Every 15 Minutes)
**What:** Run Technical Agent (TCN+LSTM), trigger LLM only if output changed  
**Why:** Technical patterns evolve faster than macro conditions  
**Cost:** Cheap model (0.5s) + occasional LLM (~10s)

```
run_technical_agent() → detect_change() → run_full_cycle() [if changed]
```

**Change detection triggers on:**
- Signal flip (BUY → SELL)
- Confidence change ≥15%
- Leading probability change ≥12%

**Result:** LLM runs ~8-12 times/day instead of 24 times/day (50% reduction)

---

### Layer 3: News Spike Detection (Every 2 Minutes)
**What:** Run Sentiment Agent on recent news, trigger full cycle if spike detected  
**Why:** Breaking news can move markets instantly, can't wait for hourly cycle  
**Cost:** Sentiment Agent (0.5s) + occasional full cycle (~15s)

```
fetch_news() → run_sentiment_agent() → detect_spike() → run_full_cycle() [if spike]
```

**Spike detection:**
- Baseline: Slow-moving average of sentiment (95% old + 5% new)
- Spike: When current sentiment deviates >0.25 from baseline
- Cooldown: 15 minutes to prevent spam

**Why real model, not keywords?** Keyword matching ("rise", "fall") misses context and synonyms. The trained Sentiment Agent captures nuance.

**Trade-off:** Runs model 2,160 times/day (18 min compute), but catches breaking news within 2 minutes.

---

### Layer 4: Full Cycle (Every 60 Minutes)
**What:** Run all 3 agents + LLM orchestrator  
**Why:** Macro conditions change slowly, hourly updates sufficient  
**Cost:** Full stack (~15s)

```
run_macro_agent() → run_technical_agent() → run_sentiment_agent() → llm_orchestrator() → generate_signal()
```

**The 3 agents:**
1. **Macro Agent** (KMeans) - Analyzes yield curves, VIX, central bank tone
2. **Technical Agent** (TCN+LSTM) - Analyzes price patterns, momentum, volatility
3. **Sentiment Agent** (LogisticRegression + lexical) - Analyzes news sentiment

**LLM Orchestrator** (Llama 3.3 70B) - Synthesizes all 3 signals into final trading decision with entry/stop/target levels.

---

## The Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Every 30s: Price Updates                                   │
│  • Fetch current prices                                     │
│  • Check validity (expired, stopped out, target hit)        │
│  • Broadcast to frontend                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Every 2min: News Monitoring                                │
│  • Fetch recent news (last 2 hours)                         │
│  • Run Sentiment Agent model                                │
│  • Compare to baseline                                      │
│  • If spike detected → Trigger full cycle for that pair    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Every 15min: Technical Monitoring                          │
│  • Run Technical Agent (TCN+LSTM)                           │
│  • Compare output to previous run                           │
│  • If changed significantly → Trigger full cycle           │
│  • Else → Skip LLM, save money                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Every 60min: Full Cycle                                    │
│  • Run Macro Agent (KMeans)                                 │
│  • Run Technical Agent (TCN+LSTM)                           │
│  • Run Sentiment Agent (LogisticRegression)                 │
│  • LLM Orchestrator synthesizes → New signal                │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Why Smart Triggering?

**Problem:** Running LLM every 15 minutes wastes money when nothing changed.

**Solution:** Run cheap Technical Agent, only call LLM if output changed.

**Analogy:** You check your phone every 5 minutes (cheap), but only call your broker when you see something important (expensive).

---

### 2. Why Real Model for Spike Detection?

**Problem:** Keyword matching ("rise", "fall") is brittle and misses context.

**Solution:** Use trained Sentiment Agent model for spike detection.

**Trade-off:** 2,160 model runs/day (18 min compute) vs. keyword matching (0 compute).

**Verdict:** Worth it. Compute is cheap, missing breaking news is expensive.

---

### 3. Why Rules for Validity Checks?

**Problem:** Do we need AI to check if a signal expired?

**Solution:** No. Use deterministic rules (timestamp math, price comparisons).

**Reasoning:** 
- Validity is a **known fact**, not a **prediction**
- Rules are fast (0.001ms vs 100ms for AI)
- Rules are explainable ("Price 1.0815 hit stop 1.0820")
- Rules can't be wrong (math is math)

**Principle:** Use AI for predictions, use rules for verification.

---

### 4. Why Per-Pair Technical Models?

**Problem:** EURUSD, GBPUSD, USDJPY have different volatility and session patterns.

**Solution:** Train separate TCN+LSTM model for each pair.

**Result:** F1 score improved from 0.37 (pooled) to 0.42-0.48 (per-pair).

---

## Cost Analysis

### Old System (Naive)
```
LLM runs: 24/day (every hour)
Cost: 24 × $X = $24X/day
```

### New System (Smart)
```
Full cycles: 24/day (hourly)
Technical triggers: ~8/day (only when changed)
News spike triggers: ~2/day (only on breaking news)

Total LLM runs: ~34/day
But: Prevented ~48 unnecessary runs (15-min naive approach)
Net savings: 30-50% vs naive 15-min approach
```

**The win:** React faster (15 min vs 60 min) while spending less (smart triggering).

---

## Data Flow

### Signal Generation
```
Agents → LLM → Signal Store → WebSocket → Frontend
```

### Live Updates
```
Price Service → Live Context Service → WebSocket → Frontend
                     ↓
              Signal Validator
              (validity checks)
```

### News Spikes
```
RSS Feeds → News Service → News Monitor → Sentiment Agent → Change Detector → Full Cycle
```

---

## The Models

### Technical Agent
- **Architecture:** TCN (Temporal Convolutional Network) + LSTM
- **Training:** One model per pair (EURUSD, GBPUSD, USDJPY)
- **Features:** RSI, MACD, Bollinger Bands, ATR, momentum indicators
- **Output:** P(BUY), P(SELL), P(HOLD) + confidence

### Sentiment Agent
- **Architecture:** LogisticRegression calibrator + direct lexical scoring
- **Training:** Historical news → price movement correlations
- **Features:** Sentiment signal, momentum, pressure, flow indicators
- **Output:** Bullish/Bearish/Neutral + confidence

### Macro Agent
- **Architecture:** KMeans clustering with absolute labeling
- **Training:** Yield curves, VIX, central bank data
- **Features:** Yield spreads, VIX z-scores, carry signals
- **Output:** Regime (Bullish/Neutral/Bearish) + probabilities

### LLM Orchestrator
- **Model:** Llama 3.3 70B (via Groq)
- **Role:** Synthesize all 3 agent signals into final trading decision
- **Output:** Direction, entry zone, stop loss, take profit, reasoning

---

## Error Handling Philosophy

**Fail gracefully, never silently.**

- Agent cycle fails → Log error, keep last known signals, retry next cycle
- WebSocket disconnects → Frontend reconnects with exponential backoff
- Price fetch fails → Use last known price, mark as stale
- Model inference fails → Return neutral signal, log for investigation

**No silent failures.** Every error is logged and visible.

---

## What Makes This Architecture Good

1. **Cost-efficient** - Smart triggering saves 30-50% on LLM costs
2. **Responsive** - Reacts to breaking news within 2 minutes
3. **Consistent** - ML-first approach throughout (no keyword hacks)
4. **Explainable** - Can trace every decision back to model outputs
5. **Resilient** - Graceful degradation on failures
6. **Scalable** - Add more pairs without redesigning

---

## What Could Be Better

See `KNOWN_ISSUES.md` for optimization opportunities:
- Duplicate Sentiment runs on spike detection
- No retry logic on agent failures
- Stats computation uses subprocess

None are blockers. Ship it.

---

## File Map

```
Deployment/Backend/
├── main.py                          # Scheduler, cycles, callbacks
├── app/
│   ├── api/
│   │   ├── websocket.py            # WebSocket broadcasts
│   │   ├── signals.py              # Signal enrichment
│   │   └── prices.py               # Price fetching
│   └── services/
│       ├── agent_service.py        # Wraps fx_alphalab agents
│       ├── change_detector.py      # Smart LLM triggering
│       ├── news_monitor.py         # Spike detection
│       ├── live_context_service.py # Real-time context
│       └── signal_validator.py     # Validity checks

fx_alphalab/fx_alphalab/
├── agents/
│   ├── technical_agent.py          # TCN+LSTM per pair
│   ├── sentiment_agent.py          # LogReg + lexical
│   └── macro_agent.py              # KMeans clustering
└── orchestrator/
    └── orchestrator.py             # LLM synthesis
```

---

## The Bottom Line

**This architecture treats AI models as what they are: expensive prediction engines.**

Run them when you need predictions. Use cheap operations (rules, caching, change detection) everywhere else.

The result: A system that's both smarter (reacts faster) and cheaper (wastes less) than naive approaches.

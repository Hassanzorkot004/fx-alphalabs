# Known Issues & Optimization Opportunities

## Overview
This document tracks known inefficiencies and potential improvements in the FX AlphaLab system. These are **not bugs** - the system works correctly. These are optimization opportunities for future iterations.

---

## 1. Duplicate Sentiment Agent Runs on Spike Detection

**Status:** 🟡 Minor Inefficiency  
**Impact:** Low - wastes ~0.5s and one model inference per spike  
**Priority:** Low

### Description
When a news spike is detected, the Sentiment Agent runs twice:
1. First run: Check if sentiment changed significantly
2. Second run: As part of the full cycle (Macro + Tech + Sent + LLM)

### Location
`Deployment/Backend/main.py` - `on_sentiment_spike()` function

```python
# Run 1
sentiment_output = await agent_service.run_sentiment_only(pair)

if change_detector.sentiment_changed(pair, sentiment_output):
    # Run 2 (includes Sentiment Agent again)
    signals_list = await agent_service.run_cycle(pairs=[pair])
```

### Proposed Fix
Cache the first Sentiment Agent result and pass it to the full cycle to avoid re-running:

```python
sentiment_output = await agent_service.run_sentiment_only(pair)

if change_detector.sentiment_changed(pair, sentiment_output):
    # Pass cached sentiment output to avoid re-running
    signals_list = await agent_service.run_cycle(
        pairs=[pair], 
        cached_sentiment={pair: sentiment_output}
    )
```

### Cost-Benefit
- **Savings:** ~0.5s per spike, ~10-20 model inferences/day
- **Effort:** Medium (requires modifying agent_service.run_cycle signature)
- **Recommendation:** Implement if spike frequency increases

---

## 2. Increased Compute from Real Model Spike Detection

**Status:** 🟡 Monitoring Required  
**Impact:** Medium - 2,160 additional model inferences/day  
**Priority:** Monitor

### Description
After replacing keyword matching with real Sentiment Agent model for spike detection, compute increased:

- **Before:** Keyword matching (~0 compute)
- **After:** Sentiment Agent every 2 min × 3 pairs = 2,160 runs/day

### Location
`Deployment/Backend/app/services/news_monitor.py` - `_check_pair_spike()` function

### Current Cost
- 2,160 runs/day × 0.5s = **18 minutes of compute/day**
- Still negligible compared to LLM costs

### Monitoring Plan
Track in production:
- Average inference time per run
- Total daily compute cost
- Spike detection accuracy vs old keyword approach

### Optimization Path (if needed)
If costs become significant, implement lightweight spike detector:
1. Train fast binary classifier (LogisticRegression)
2. Use as first-stage filter (10ms inference)
3. Run full Sentiment Agent only when fast detector triggers
4. See: `improvements/spike-detector/` for implementation plan

### Recommendation
- **Now:** Ship as-is, monitor costs
- **Later:** Optimize only if costs exceed $X/month threshold

---

## 3. No Error Recovery for Agent Cycle Failures

**Status:** 🟡 Resilience Gap  
**Impact:** Medium - stale signals for up to 60 minutes on failure  
**Priority:** Medium

### Description
If the agent cycle fails (network error, model crash, API timeout), no new signals are generated until the next scheduled cycle.

### Location
`Deployment/Backend/main.py` - `run_full_cycle()`, `run_technical_cycle()`, `on_sentiment_spike()`

```python
async def run_full_cycle():
    try:
        signals_list = await agent_service.run_cycle()
        signal_store.update(signals_list)
    except Exception as e:
        logger.error(f"Full cycle failed: {e}")
        # No retry, no fallback - just logs and waits for next cycle
```

### Impact Scenarios
- **Full cycle fails:** No new signals for 60 minutes
- **Technical cycle fails:** No updates for 15 minutes
- **Spike handler fails:** Missed opportunity to react to breaking news

### Proposed Fix
Add exponential backoff retry logic:

```python
async def run_full_cycle():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            signals_list = await agent_service.run_cycle()
            signal_store.update(signals_list)
            return
        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s
                logger.warning(f"Cycle failed (attempt {attempt+1}/{max_retries}), retrying in {wait}s: {e}")
                await asyncio.sleep(wait)
            else:
                logger.error(f"Cycle failed after {max_retries} attempts: {e}")
                # Could broadcast error to frontend here
```

### Additional Considerations
- Keep last known good signals in memory
- Broadcast "degraded mode" status to frontend
- Alert monitoring system on repeated failures

### Recommendation
Implement retry logic before production deployment

---

## 4. Stats Computation Uses Subprocess

**Status:** 🟡 Fragile Implementation  
**Impact:** Low - stats might fail silently  
**Priority:** Low

### Description
Stats computation spawns a subprocess instead of importing directly:

```python
result = subprocess.run(
    [sys.executable, str(stats_script)],
    cwd=str(settings.FX_ALPHALAB_ROOT),
    timeout=300,
)
```

### Issues
- **Path dependencies:** Requires correct working directory
- **Environment issues:** Subprocess might not have same Python environment
- **Silent failures:** If script fails, stats just don't update
- **Harder to debug:** Errors happen in separate process

### Location
`Deployment/Backend/main.py` - `compute_stats_cache()` function

### Proposed Fix
Import and call directly:

```python
async def compute_stats_cache():
    try:
        from fx_alphalab.scripts import compute_backtest_stats
        
        logger.info("Running backtest stats computation...")
        await asyncio.to_thread(compute_backtest_stats.main)
        
        logger.success("✓ Stats cache updated")
        signal_store.load_from_csv()
    except Exception as e:
        logger.error(f"Stats computation error: {e}")
```

### Benefits
- Same Python environment
- Better error messages
- Easier to debug
- No path issues

### Recommendation
Refactor when touching stats code next

---

## 5. WebSocket Reconnection Could Be Smarter

**Status:** 🟢 Working, Could Be Better  
**Impact:** Low - minor UX improvement  
**Priority:** Low

### Description
Frontend WebSocket uses exponential backoff (1s, 2s, 4s, 8s, max 30s) but doesn't distinguish between:
- Network issues (should retry aggressively)
- Server shutdown (should back off)
- Invalid auth (should not retry)

### Location
`Deployment/Frontend/my-app/src/hooks/useSignals.ts`

### Current Behavior
```typescript
const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
```

### Proposed Enhancement
```typescript
ws.onclose = (event) => {
    if (event.code === 1000) {
        // Normal closure - don't reconnect
        return;
    }
    if (event.code === 1008) {
        // Policy violation - don't reconnect
        return;
    }
    // Otherwise use exponential backoff
};
```

### Recommendation
Nice-to-have, not urgent

---

## Summary

| Issue | Priority | Impact | Effort | Recommendation |
|-------|----------|--------|--------|----------------|
| Duplicate Sentiment runs | Low | Low | Medium | Optimize if spike frequency increases |
| Increased compute | Monitor | Medium | N/A | Monitor costs, optimize if needed |
| No error recovery | Medium | Medium | Low | Implement before production |
| Stats subprocess | Low | Low | Low | Refactor when convenient |
| WebSocket reconnection | Low | Low | Low | Nice-to-have |

---

## Monitoring Checklist

Track these metrics in production:

- [ ] Sentiment Agent inference time (should be <1s)
- [ ] Daily Sentiment Agent run count (expect ~2,160)
- [ ] Agent cycle failure rate (should be <1%)
- [ ] Spike detection accuracy (compare to manual review)
- [ ] WebSocket disconnection frequency
- [ ] Stats computation success rate

---

## Version History

- **2026-05-01:** Initial document created after architecture review
- **2026-05-01:** Added spike detection compute increase after replacing keyword matching

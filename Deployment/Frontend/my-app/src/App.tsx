import { useState, useRef, useCallback } from 'react';
import { useSignals } from './hooks/useSignals';
import { useNotifications } from './hooks/useNotifications';
import type { NewsArticle, CalendarEvent } from './Types';
import SignalCard from './components/SignalCard';
import AlphaBotPanel from './components/AlphaBotPanel';
import EventCalendarPanel from './components/EventCalendarPanel';
import NewsFeedPanel from './components/NewsFeedPanel';
import NextUpdateCountdown from './components/NextUpdateCountdown';
import { API_BASE_URL } from './config/constants';

export default function App() {
  const { signals, history, calendar, news, prices, liveContexts, connected, lastUpdate, nextCycle } = useSignals();
  const [selectedPair, setSelectedPair] = useState<string | null>(null);
  const [alphaBotOpen, setAlphaBotOpen] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const alphaBotSendRef = useRef<((msg: string) => Promise<void>) | null>(null);

  const handleRefresh = useCallback(async () => {
    if (isRefreshing) return;
    setIsRefreshing(true);
    try {
      await fetch(`${API_BASE_URL}/api/run-now`, { method: 'POST' });
    } catch (e) {
      console.error('run-now failed', e);
    }
    // Safety timeout — stop spinner after 60s regardless
    setTimeout(() => setIsRefreshing(false), 60000);
  }, [isRefreshing]);

  // Stop spinner when new signals arrive
  const prevSignalCount = useRef(signals.length);
  if (isRefreshing && signals.length > 0 && signals.length !== prevSignalCount.current) {
    setIsRefreshing(false);
  }
  prevSignalCount.current = signals.length;  useNotifications(signals);

  const getWatchlist = (): string[] => {
    try {
      const stored = localStorage.getItem('fx-alphalab-settings');
      if (stored) {
        const settings = JSON.parse(stored);
        return settings.watchlist || ['EURUSD', 'GBPUSD', 'USDJPY'];
      }
    } catch { /* ignore */ }
    return ['EURUSD', 'GBPUSD', 'USDJPY'];
  };

  const watchlist = getWatchlist();
  const filteredSignals = signals.filter(s => watchlist.includes(s.pair.replace('=X', '')));

  const activePair = selectedPair || filteredSignals[0]?.pair || 'EURUSD=X';
  const activeSignal = filteredSignals.find(s => s.pair === activePair) || null;

  const handleNewsClick = (article: NewsArticle) => {
    const pairName = activePair.replace('=X', '');
    setAlphaBotOpen(true);
    // Small delay so panel mounts and subscribes to state before message fires
    setTimeout(() => {
      if (alphaBotSendRef.current) {
        alphaBotSendRef.current(`How does this news affect ${pairName}? "${article.title}"`);
      }
    }, 50);
  };

  const handleEventClick = (event: CalendarEvent) => {
    const pairName = activePair.replace('=X', '');
    setAlphaBotOpen(true);
    setTimeout(() => {
      if (alphaBotSendRef.current) {
        alphaBotSendRef.current(`How will "${event.event}" (${event.currency}) impact ${pairName}?`);
      }
    }, 50);
  };

  const sortedSignals = [...filteredSignals].sort((a, b) => {
    const order = ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'];
    return order.indexOf(a.pair) - order.indexOf(b.pair);
  });

  // Current time display
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });

  return (
    <div style={{
      minHeight: 'calc(100vh - 49px)',
      background: 'var(--bg)',
      color: 'var(--text)',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Dashboard Header Bar */}
      <div style={{
        background: 'var(--bg1)',
        borderBottom: '1px solid var(--border)',
        padding: '0 20px',
        height: 44,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        {/* Left: live indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '3px 10px',
            background: connected ? 'rgba(0,200,150,0.1)' : 'rgba(255,71,87,0.1)',
            border: `1px solid ${connected ? 'rgba(0,200,150,0.3)' : 'rgba(255,71,87,0.3)'}`,
            borderRadius: 4,
          }}>
            <div style={{
              width: 5,
              height: 5,
              borderRadius: '50%',
              background: connected ? 'var(--green)' : 'var(--red)',
            }} className={connected ? 'animate-pulse-dot' : ''} />
            <span className="mono" style={{ fontSize: 10, fontWeight: 600, color: connected ? 'var(--green)' : 'var(--red)', letterSpacing: '0.06em' }}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>

        {/* Right: controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Refresh / Run Now button */}
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            title="Run all agents now"
            style={{
              background: isRefreshing ? 'rgba(0,212,255,0.08)' : 'var(--bg3)',
              border: `1px solid ${isRefreshing ? 'rgba(0,212,255,0.4)' : 'var(--border2)'}`,
              color: isRefreshing ? 'var(--cyan)' : 'var(--text2)',
              padding: '4px 10px',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              cursor: isRefreshing ? 'not-allowed' : 'pointer',
              letterSpacing: '0.04em',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s ease',
            }}
          >
            <svg
              width="11" height="11" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"
              style={{
                animation: isRefreshing ? 'spin 1s linear infinite' : 'none',
              }}
            >
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            {isRefreshing ? 'RUNNING…' : 'RUN NOW'}
          </button>

          {/* Intel button */}
          <button
            onClick={() => setAlphaBotOpen(true)}
            style={{
              background: 'var(--bg3)',
              border: '1px solid var(--border2)',
              color: 'var(--text2)',
              padding: '4px 12px',
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              letterSpacing: '0.04em',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <span style={{ color: 'var(--cyan)', fontSize: 10 }}>+</span> INTEL
          </button>

          {/* Countdown */}
          <NextUpdateCountdown nextCycleSeconds={nextCycle} />

          {/* Clock */}
          <div className="mono" style={{ fontSize: 11, color: 'var(--text3)', minWidth: 70, textAlign: 'right' }}>
            {lastUpdate ? new Date(lastUpdate).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false }) : timeStr}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 16 }}>

        {/* Signal Cards — 3 columns */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {filteredSignals.length === 0
            ? [0, 1, 2].map(i => <SkeletonCard key={i} />)
            : sortedSignals.map(signal => (
                <SignalCard
                  key={signal.pair}
                  signal={signal}
                  price={prices[signal.pair]}
                  liveContext={liveContexts[signal.pair]}
                  isSelected={signal.pair === activePair}
                  onClick={() => setSelectedPair(signal.pair)}
                />
              ))
          }
        </div>

        {/* News Wire + Calendar */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 420px', gap: 12 }}>
          <NewsFeedPanel
            articles={news}
            selectedPair={activePair}
            onArticleClick={handleNewsClick}
          />
          <EventCalendarPanel
            events={calendar}
            selectedPair={activePair}
            onEventClick={handleEventClick}
          />
        </div>

        {/* Signal Ledger Strip */}
        {history.length > 0 && (
          <SignalLedgerStrip history={history} />
        )}
      </div>

      {/* Status Bar */}
      <div style={{
        background: 'var(--bg1)',
        borderTop: '1px solid var(--border)',
        padding: '6px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexShrink: 0,
      }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
          FX AlphaLab v4.0 · Llama 3.3 70B · 5-Stage Hybrid Pipeline
        </span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
          {filteredSignals.length} active · {history.length} in ledger
        </span>
      </div>

      {/* AlphaBot Floating Overlay */}
      {alphaBotOpen && (
        <AlphaBotPanel
          pair={activePair.replace('=X', '')}
          signal={activeSignal}
          onSendMessage={fn => { alphaBotSendRef.current = fn; }}
          onClose={() => setAlphaBotOpen(false)}
        />
      )}

      {/* AlphaBot FAB */}
      {!alphaBotOpen && (
        <button
          onClick={() => setAlphaBotOpen(true)}
          title="Open AlphaBot"
          style={{
            position: 'fixed',
            bottom: 28,
            right: 28,
            width: 48,
            height: 48,
            borderRadius: '50%',
            background: 'var(--cyan)',
            border: 'none',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 20px rgba(0,212,255,0.35)',
            zIndex: 100,
            transition: 'transform 0.15s ease, box-shadow 0.15s ease',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.transform = 'scale(1.08)';
            (e.currentTarget as HTMLElement).style.boxShadow = '0 6px 28px rgba(0,212,255,0.5)';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.transform = 'scale(1)';
            (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 20px rgba(0,212,255,0.35)';
          }}
        >
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#0d1117" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        </button>
      )}
    </div>
  );
}

/* ── Signal Ledger Strip ─────────────────────────────────────── */
function SignalLedgerStrip({ history }: { history: import('./Types').Signal[] }) {
  const recent = history.slice(0, 8);
  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: '10px 16px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Signal Ledger
        </span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
          · {history.length} entries
        </span>
      </div>
      <div style={{ display: 'flex', gap: 8, overflowX: 'auto', paddingBottom: 2 }}>
        {recent.map((signal, idx) => {
          const pair = signal.pair.replace('=X', '');
          const dirColor = signal.direction === 'BUY' ? 'var(--green)' : signal.direction === 'SELL' ? 'var(--red)' : 'var(--text3)';
          const ts = signal.timestamp ? new Date(signal.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) : '—';
          return (
            <div key={idx} style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '6px 12px',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              flexShrink: 0,
              fontSize: 11,
            }}>
              <span className="mono" style={{ fontWeight: 600, color: 'var(--text)' }}>{pair}</span>
              <span style={{ fontWeight: 700, color: dirColor, fontSize: 10 }}>{signal.direction}</span>
              <span className="mono" style={{ color: 'var(--text3)', fontSize: 10 }}>
                {(signal.confidence * 100).toFixed(0)}%
              </span>
              <span className="mono" style={{ color: 'var(--text3)', fontSize: 10 }}>{ts}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ── Skeleton ────────────────────────────────────────────────── */
function SkeletonCard() {
  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      height: 220,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
        <div>
          <div style={{ height: 16, background: 'var(--border)', borderRadius: 4, width: 80, marginBottom: 6 }} />
          <div style={{ height: 11, background: 'var(--border)', borderRadius: 3, width: 50 }} />
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ height: 22, background: 'var(--border)', borderRadius: 4, width: 90, marginBottom: 6 }} />
          <div style={{ height: 11, background: 'var(--border)', borderRadius: 3, width: 70 }} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        <div style={{ height: 26, background: 'var(--border)', borderRadius: 4, width: 60 }} />
        <div style={{ height: 26, background: 'var(--border)', borderRadius: 4, width: 70 }} />
      </div>
      <div style={{ height: 4, background: 'var(--border)', borderRadius: 2, marginBottom: 14 }} />
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ height: 22, background: 'var(--border)', borderRadius: 12, width: 80 }} />
        <div style={{ height: 22, background: 'var(--border)', borderRadius: 12, width: 80 }} />
        <div style={{ height: 22, background: 'var(--border)', borderRadius: 12, width: 80 }} />
      </div>
    </div>
  );
}

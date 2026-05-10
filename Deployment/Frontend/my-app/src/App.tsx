import { useRef, useState } from 'react';
import { useSignals } from './hooks/useSignals';
import TickerStrip from './components/TickerStrip';
import SignalCard from './components/SignalCard';
import AlphaBotPanel from './components/AlphaBotPanel';
import EventCalendarPanel from './components/EventCalendarPanel';
import NewsFeedPanel from './components/NewsFeedPanel';
import NextUpdateCountdown from './components/NextUpdateCountdown';
import type { CalendarEvent, NewsArticle } from './Types';

export default function App() {
  const { signals, history, calendar, news, prices, liveContexts, connected, lastUpdate, nextCycle } = useSignals();
  const [selectedPair, setSelectedPair] = useState<string | null>(null);
  const [autoOpenChat, setAutoOpenChat] = useState(false);
  const [showIntel, setShowIntel] = useState(true);
  const alphaBotSendRef = useRef<((msg: string) => void) | null>(null);

  const activePair = selectedPair || signals[0]?.pair || 'EURUSD=X';
  const activeSignal = signals.find(s => s.pair === activePair) || null;
  const validSignals = signals.filter(s => s && s.pair);
  const validHistory = history.filter(s => s && s.pair && s.timestamp);

  const handleNewsClick = (article: NewsArticle) => {
    setAutoOpenChat(true);
    setTimeout(() => {
      alphaBotSendRef.current?.(`How does this news affect ${activePair.replace('=X', '')}? "${article.title}"`);
      setAutoOpenChat(false);
    }, 150);
  };

  const handleEventClick = (event: CalendarEvent) => {
    setAutoOpenChat(true);
    setTimeout(() => {
      alphaBotSendRef.current?.(`How will "${event.event}" (${event.currency}) impact ${activePair.replace('=X', '')}?`);
      setAutoOpenChat(false);
    }, 150);
  };

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)', display: 'flex', flexDirection: 'column' }}>
      {/* ── Skyline Header ── */}
      <header style={{
        background: 'var(--bg1)',
        borderBottom: '1px solid var(--border)',
        padding: '10px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        position: 'sticky',
        top: 0,
        zIndex: 100,
        backdropFilter: 'blur(20px)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: 'linear-gradient(135deg, var(--cyan), var(--violet))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 800, color: '#000',
              boxShadow: '0 0 16px rgba(0,229,255,0.2)',
            }}>FX</div>
            <div>
              <div className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.2px' }}>AlphaLab</div>
              <div className="mono" style={{ fontSize: 8, color: 'var(--text3)', letterSpacing: '1px', textTransform: 'uppercase' }}>Signal Engine</div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, paddingLeft: 20, borderLeft: '1px solid var(--border)' }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', background: connected ? 'var(--emerald)' : 'var(--magenta)', boxShadow: connected ? '0 0 8px var(--emerald)' : 'none' }} className={connected ? 'animate-pulse' : ''} />
            <span className="mono" style={{ fontSize: 9, color: connected ? 'var(--emerald)' : 'var(--magenta)', fontWeight: 600, letterSpacing: '1.5px' }}>
              {connected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <button onClick={() => setShowIntel(!showIntel)} className="badge badge-outline" style={{ color: 'var(--text3)', cursor: 'pointer', fontSize: 9, padding: '5px 10px' }}>
            {showIntel ? '▾ Intel' : '▸ Intel'}
          </button>
          <NextUpdateCountdown nextCycleSeconds={nextCycle} />
          <span className="mono" style={{ fontSize: 9, color: 'var(--text3)' }}>
            {lastUpdate ? new Date(lastUpdate).toLocaleTimeString() : '--:--:--'}
          </span>
        </div>
      </header>

      {/* ── Ticker ── */}
      {prices && Object.keys(prices).length > 0 && <TickerStrip prices={prices} />}

      {/* ── Main Grid ── */}
      <main style={{ flex: 1, padding: '14px 20px', display: 'flex', flexDirection: 'column', gap: 14, maxWidth: 1600, margin: '0 auto', width: '100%' }}>
        {/* Signal Cards — Full width, equal columns */}
        <section>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
            {validSignals.length === 0
              ? [0, 1, 2].map(i => <SkeletonCard key={i} />)
              : [...validSignals].sort((a, b) => ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'].indexOf(a.pair) - ['EURUSD=X', 'GBPUSD=X', 'USDJPY=X'].indexOf(b.pair)).map(signal => (
                  <SignalCard
                    key={signal.pair}
                    signal={signal}
                    price={prices?.[signal.pair]}
                    liveContext={liveContexts?.[signal.pair]}
                    isSelected={signal.pair === activePair}
                    onClick={() => setSelectedPair(signal.pair)}
                  />
                ))
            }
          </div>
        </section>

        {/* Market Intelligence — Collapsible */}
        {showIntel && (
          <section className="animate-slide-up">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <NewsFeedPanel articles={news || []} selectedPair={activePair} onArticleClick={handleNewsClick} />
              <EventCalendarPanel events={calendar || []} selectedPair={activePair} onEventClick={handleEventClick} />
            </div>
          </section>
        )}

        {/* History Strip — Compact scrollable */}
        {validHistory.length > 0 && (
          <section>
            <div className="mono" style={{ fontSize: 8, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 8, fontWeight: 600 }}>
              Signal Ledger · {validHistory.length} entries
            </div>
            <div style={{
              background: 'var(--bg1)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '8px 12px',
              overflowX: 'auto',
              display: 'flex',
              gap: 8,
            }}>
              {validHistory.slice(0, 12).map((signal, idx) => (
                <div key={signal.timestamp + '-' + idx} style={{
                  background: 'var(--bg2)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  padding: '6px 10px',
                  fontSize: 10,
                  whiteSpace: 'nowrap',
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}>
                  <span className="mono" style={{ fontWeight: 600, color: 'var(--text)' }}>{signal.pair.replace('=X', '')}</span>
                  <span style={{ color: signal.direction === 'BUY' ? 'var(--buy)' : signal.direction === 'SELL' ? 'var(--sell)' : 'var(--hold)', fontWeight: 700 }}>{signal.direction}</span>
                  <span className="mono" style={{ color: 'var(--text3)' }}>{((signal.confidence || 0) * 100).toFixed(0)}%</span>
                  <span className="mono" style={{ color: 'var(--text3)', fontSize: 9 }}>{(() => {
  try {
    const d = new Date(signal.timestamp);
    if (isNaN(d.getTime())) return '--:--';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch { return '--:--'; }
})()}</span>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>

      {/* ── Status Bar ── */}
      <footer style={{
        background: 'var(--bg1)',
        borderTop: '1px solid var(--border)',
        padding: '6px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 9,
        color: 'var(--text3)',
      }}>
        <span className="mono">FX AlphaLab v2.0 · Llama 3.1 70B · 5-Stage Hybrid Pipeline · ~1.8s latency</span>
        <span className="mono">{validSignals.length} active · {validHistory.length} total</span>
      </footer>

      <AlphaBotPanel pair={activePair} signal={activeSignal} onSendRef={fn => { alphaBotSendRef.current = fn; }} autoOpen={autoOpenChat} />
    </div>
  );
}

function SkeletonCard() {
  return (
    <div className="glass" style={{ padding: 20, height: 280 }}>
      <div style={{ height: 14, background: 'var(--border)', borderRadius: 4, width: 70, marginBottom: 16 }} />
      <div style={{ height: 20, background: 'var(--border)', borderRadius: 4, width: 110, marginBottom: 12 }} />
      <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, marginBottom: 14 }} />
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 10, width: 50 }} />
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 10, width: 50 }} />
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 10, width: 50 }} />
      </div>
    </div>
  );
}
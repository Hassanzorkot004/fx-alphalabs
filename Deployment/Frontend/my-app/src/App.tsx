import { useState } from 'react';
import { useSignals } from './hooks/useSignals';
import { useRef } from 'react';
import type { NewsArticle, CalendarEvent } from './Types';
import TickerStrip from './components/TickerStrip';
import SignalCard from './components/SignalCard';
import AlphaBotPanel from './components/AlphaBotPanel';
import EventCalendarPanel from './components/EventCalendarPanel';
import NewsFeedPanel from './components/NewsFeedPanel';

export default function App() {
  const { signals, history, stats, calendar, news, prices, connected, lastUpdate } = useSignals();
  const [selectedPair, setSelectedPair] = useState<string | null>(null);
  const alphaBotSendRef = useRef<((msg: string) => Promise<void>) | null>(null);

  // Auto-select first signal if none selected
  const activePair = selectedPair || signals[0]?.pair || 'EURUSD=X';
  const activeSignal = signals.find(s => s.pair === activePair) || null;

  // Handle news article click
  const handleNewsClick = (article: NewsArticle) => {
    if (alphaBotSendRef.current) {
      const pairName = activePair.replace('=X', '');
      alphaBotSendRef.current(`How does this news affect ${pairName}? "${article.title}"`);
    }
  };

  // Handle calendar event click
  const handleEventClick = (event: CalendarEvent) => {
    if (alphaBotSendRef.current) {
      const pairName = activePair.replace('=X', '');
      alphaBotSendRef.current(`How will "${event.event}" (${event.currency}) impact ${pairName}?`);
    }
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      background: 'var(--bg)', 
      color: 'var(--text)',
      display: 'flex',
      flexDirection: 'column',
    }}>
        {/* Top Bar */}
        <div style={{
          background: 'var(--bg1)',
          borderBottom: '1px solid var(--border)',
          padding: '10px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--amber)' }}>
              FX AlphaLab
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <div style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: connected ? 'var(--green)' : 'var(--red)',
              }}
              className={connected ? 'animate-pulse-dot' : ''}
              />
              <span className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
                {connected ? 'LIVE' : 'DISCONNECTED'}
              </span>
            </div>
          </div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
            {lastUpdate ? `Updated ${new Date(lastUpdate).toLocaleTimeString()}` : 'Waiting for data...'}
          </div>
        </div>

        {/* Ticker Strip */}
        {Object.keys(prices).length > 0 && <TickerStrip prices={prices} />}

        {/* Main Content */}
        <div style={{ flex: 1, padding: 20, display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Signal Cards */}
          <div>
            <div className="mono" style={{ 
              fontSize: 10, 
              color: 'var(--text3)', 
              textTransform: 'uppercase', 
              letterSpacing: '0.08em',
              marginBottom: 12,
            }}>
              Live Signals
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
              {signals.length === 0 ? (
                [0, 1, 2].map(i => <SkeletonCard key={i} />)
              ) : (
                signals.map(signal => (
                  <SignalCard
                    key={signal.pair}
                    signal={signal}
                    price={prices[signal.pair]}
                    isSelected={signal.pair === activePair}
                    onClick={() => setSelectedPair(signal.pair)}
                  />
                ))
              )}
            </div>
          </div>

          {/* Workspace: AlphaBot + Right Panel */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 400px', gap: 20 }}>
            {/* AlphaBot */}
            <AlphaBotPanel 
              pair={activePair.replace('=X', '')} 
              signal={activeSignal}
              onSendMessage={(fn) => { alphaBotSendRef.current = fn; }}
            />

            {/* Right Panel */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <EventCalendarPanel 
                events={calendar} 
                selectedPair={activePair}
                onEventClick={handleEventClick}
              />
              <NewsFeedPanel 
                articles={news}
                onArticleClick={handleNewsClick}
              />
            </div>
          </div>

          {/* History Preview */}
          {history.length > 0 && (
            <div>
              <div className="mono" style={{ 
                fontSize: 10, 
                color: 'var(--text3)', 
                textTransform: 'uppercase', 
                letterSpacing: '0.08em',
                marginBottom: 12,
              }}>
                Recent History ({history.length} signals)
              </div>
              <div style={{
                background: 'var(--bg2)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: 16,
                maxHeight: 200,
                overflowY: 'auto',
              }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {history.slice(0, 5).map((signal, idx) => (
                    <div key={idx} style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: 8,
                      background: 'var(--bg3)',
                      borderRadius: 4,
                      fontSize: 12,
                    }}>
                      <span className="mono" style={{ fontWeight: 600 }}>
                        {signal.pair.replace('=X', '')}
                      </span>
                      <span style={{ 
                        color: signal.direction === 'BUY' ? 'var(--green)' : 
                               signal.direction === 'SELL' ? 'var(--red)' : 'var(--text3)',
                        fontWeight: 600,
                      }}>
                        {signal.direction}
                      </span>
                      <span style={{ color: 'var(--text3)' }}>
                        {signal.agent_agreement}
                      </span>
                      <span className="mono" style={{ color: 'var(--text3)', fontSize: 11 }}>
                        {new Date(signal.timestamp).toLocaleString()}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Status Bar */}
        <div style={{
          background: 'var(--bg1)',
          borderTop: '1px solid var(--border)',
          padding: '8px 20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
            FX AlphaLab v2.0 · llama-3.3-70b-versatile · signals updated every 60 min
          </span>
          <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
            {signals.length} active · {history.length} total
          </span>
        </div>
      </div>
  );
}

function SkeletonCard() {
  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      height: 180,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ height: 14, background: 'var(--border)', borderRadius: 4, width: 70 }} />
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 4, width: 80 }} />
      </div>
      <div style={{ height: 4, background: 'var(--border)', borderRadius: 2, marginBottom: 12 }} />
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ height: 24, background: 'var(--border)', borderRadius: 4, width: 60 }} />
        <div style={{ height: 24, background: 'var(--border)', borderRadius: 4, width: 70 }} />
      </div>
    </div>
  );
}

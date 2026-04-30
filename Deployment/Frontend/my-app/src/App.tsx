import { useState } from 'react';
import { ErrorBoundary } from './components/ErrorBoundary';
import TopBar         from './components/TopBar';
import StatsRow       from './components/StatsRow';
import SignalCard     from './components/SignalCard';
import ReasoningPanel from './components/Reasoningpanel';
import HistoryTable   from './components/HistoryTable';
import { useWebSocket } from './hooks/useWebSocket';
import { useBackendInfo } from './hooks/useBackendInfo';
import { WS_URL } from './config/constants';
import type { Signal } from './Types';

function SkeletonCard() {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div style={{ height: 14, background: 'var(--border)', borderRadius: 4, width: 70 }} />
        <div style={{ height: 26, background: 'var(--border)', borderRadius: 8, width: 52 }} />
      </div>
      <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, marginBottom: 10 }} />
      <div style={{ display: 'flex', gap: 6 }}>
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 99, width: 72 }} />
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 99, width: 60 }} />
        <div style={{ height: 20, background: 'var(--border)', borderRadius: 99, width: 64 }} />
      </div>
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', padding: '14px 20px 8px' }}>
      {children}
    </div>
  );
}

export default function App() {
  const { signals, history, stats, connected, lastUpdate, nextCycle } = useWebSocket();
  const backendInfo = useBackendInfo();
  const [selectedPair, setSelectedPair] = useState<string | null>(null);

  const cycleNum = history.length > 0 ? Math.ceil(history.length / 3) : null;

  const selectedSignal: Signal | null =
    selectedPair
      ? (signals.find(s => s.pair === selectedPair) ?? history.find(s => s.pair === selectedPair) ?? null)
      : (signals[0] ?? null);

  return (
    <ErrorBoundary>
      <div style={{ minHeight: '100svh', background: 'var(--bg)', color: 'var(--text-primary)' }}>

        <TopBar connected={connected} lastUpdate={lastUpdate} nextCycle={nextCycle} cycleNumber={cycleNum} />
        <StatsRow stats={stats} />

      <SectionLabel>
        Live signals
        <span style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '50%', background: connected ? 'var(--buy)' : 'var(--hold)', marginLeft: 8, verticalAlign: 'middle' }}
          className={connected ? 'animate-pulse-dot' : ''} />
      </SectionLabel>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 14, padding: '0 20px 4px' }}>
        {signals.length === 0
          ? [0, 1, 2].map(i => <SkeletonCard key={i} />)
          : signals.map(signal => (
              <SignalCard
                key={signal.pair}
                signal={signal}
                isSelected={selectedPair === signal.pair || (!selectedPair && signals.indexOf(signal) === 0)}
                onClick={() => setSelectedPair(signal.pair)}
              />
            ))
        }
      </div>

      <SectionLabel>LLM Reasoning</SectionLabel>
      <ReasoningPanel signal={selectedSignal} />

      <SectionLabel>History</SectionLabel>
      <HistoryTable history={history} />

      <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between' }}>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          FX AlphaLab v{backendInfo?.version || '2.0'} · {backendInfo?.model || 'llama-3.1-70b'} · signals updated every {backendInfo?.interval || 60} min
        </span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {connected ? '🟢' : '🔴'} {WS_URL}
        </span>
      </div>
    </div>
    </ErrorBoundary>
  );
}
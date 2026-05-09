import { useState, useEffect } from 'react';
import type { Signal } from '../Types';
import { API_BASE_URL, PAIR_DECIMALS } from '../config/constants';

export default function HistoryPage() {
  const [history, setHistory] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPair, setSelectedPair] = useState<string>('all');
  const [selectedDirection, setSelectedDirection] = useState<string>('all');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => { fetchHistory(); }, []);

  const fetchHistory = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/history`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      setHistory(data.history || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const filteredHistory = history.filter(signal => {
    if (selectedPair !== 'all' && signal.pair.replace('=X', '') !== selectedPair) return false;
    if (selectedDirection !== 'all' && signal.direction !== selectedDirection) return false;
    return true;
  });

  const exportToCSV = () => {
    const headers = ['Timestamp', 'Pair', 'Direction', 'Confidence', 'Agreement', 'Regime', 'Price', 'Driver', 'Reasoning'];
    const rows = filteredHistory.map(s => [
      s.timestamp,
      s.pair.replace('=X', ''),
      s.direction,
      (s.confidence * 100).toFixed(0) + '%',
      s.agent_agreement,
      s.macro_regime,
      s.price_at_signal || '',
      s.source || '',
      `"${s.reasoning.replace(/"/g, '""')}"`,
    ]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fx-alphalab-ledger-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div style={{ minHeight: 'calc(100vh - 49px)', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text3)' }}>
        <span className="mono" style={{ fontSize: 12 }}>Loading ledger…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: 'calc(100vh - 49px)', background: 'var(--bg)', padding: 40, color: 'var(--red)' }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div style={{ minHeight: 'calc(100vh - 49px)', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Page Header */}
      <div style={{
        padding: '20px 24px 16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
        borderBottom: '1px solid var(--border)',
      }}>
        <div>
          <h1 className="mono" style={{ fontSize: 22, fontWeight: 700, color: 'var(--cyan)', marginBottom: 4 }}>
            Signal Ledger
          </h1>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
            {filteredHistory.length} record{filteredHistory.length !== 1 ? 's' : ''}
            {(selectedPair !== 'all' || selectedDirection !== 'all') && ' (filtered)'}
          </div>
        </div>
        <button
          onClick={exportToCSV}
          disabled={filteredHistory.length === 0}
          style={{
            background: filteredHistory.length > 0 ? 'transparent' : 'var(--bg3)',
            color: filteredHistory.length > 0 ? 'var(--cyan)' : 'var(--text3)',
            border: `1px solid ${filteredHistory.length > 0 ? 'var(--cyan)' : 'var(--border)'}`,
            padding: '8px 18px',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 600,
            cursor: filteredHistory.length > 0 ? 'pointer' : 'not-allowed',
            transition: 'all 0.15s ease',
            letterSpacing: '0.02em',
          }}
          onMouseEnter={e => { if (filteredHistory.length > 0) (e.currentTarget as HTMLElement).style.background = 'rgba(0,212,255,0.1)'; }}
          onMouseLeave={e => { if (filteredHistory.length > 0) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
        >
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div style={{
        padding: '10px 24px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        gap: 10,
        alignItems: 'center',
        background: 'var(--bg2)',
      }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          Filter
        </span>
        <select
          value={selectedPair}
          onChange={e => setSelectedPair(e.target.value)}
          style={selectStyle}
        >
          <option value="all">All Pairs</option>
          <option value="EURUSD">EURUSD</option>
          <option value="GBPUSD">GBPUSD</option>
          <option value="USDJPY">USDJPY</option>
        </select>
        <select
          value={selectedDirection}
          onChange={e => setSelectedDirection(e.target.value)}
          style={selectStyle}
        >
          <option value="all">All Directions</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="HOLD">HOLD</option>
        </select>
        {(selectedPair !== 'all' || selectedDirection !== 'all') && (
          <button
            onClick={() => { setSelectedPair('all'); setSelectedDirection('all'); }}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text3)',
              padding: '5px 10px',
              borderRadius: 4,
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Table */}
      <div style={{ padding: '20px 24px' }}>
        {filteredHistory.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)', fontSize: 13 }}>
            No signals found
          </div>
        ) : (
          <div style={{
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            overflow: 'hidden',
          }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: 'var(--bg3)', borderBottom: '1px solid var(--border)' }}>
                  {['Time', 'Pair', 'Direction', 'Conf', 'Agreement', 'Regime', 'Price', 'Driver', ''].map(h => (
                    <th key={h} style={thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((signal, idx) => (
                  <HistoryRow
                    key={idx}
                    signal={signal}
                    isExpanded={expandedRow === idx}
                    onToggle={() => setExpandedRow(expandedRow === idx ? null : idx)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

const selectStyle: React.CSSProperties = {
  background: 'var(--bg3)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  padding: '5px 28px 5px 10px',
  borderRadius: 4,
  fontSize: 12,
  cursor: 'pointer',
  outline: 'none',
};

const thStyle: React.CSSProperties = {
  padding: '10px 14px',
  textAlign: 'left',
  fontSize: 10,
  fontWeight: 700,
  color: 'var(--text3)',
  textTransform: 'uppercase',
  letterSpacing: '0.06em',
  fontFamily: 'var(--font-mono)',
};

const tdStyle: React.CSSProperties = {
  padding: '11px 14px',
  fontSize: 12,
  borderBottom: '1px solid var(--border)',
};

function HistoryRow({ signal, isExpanded, onToggle }: {
  signal: Signal;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const pair = signal.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;

  const dirColor =
    signal.direction === 'BUY'  ? 'var(--green)' :
    signal.direction === 'SELL' ? 'var(--red)'   : 'var(--text3)';

  const agreementColor =
    signal.agent_agreement === 'FULL'    ? 'var(--green)' :
    signal.agent_agreement === 'PARTIAL' ? '#f59e0b'      : 'var(--text3)';

  const driverColor = 'var(--cyan)';

  const ts = signal.timestamp
    ? new Date(signal.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })
    : '—';

  return (
    <>
      <tr
        onClick={onToggle}
        style={{ cursor: 'pointer', transition: 'background 0.1s ease' }}
        onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'var(--bg3)'}
        onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
      >
        <td style={tdStyle} className="mono" >{ts}</td>
        <td style={{ ...tdStyle, fontWeight: 700 }} className="mono">{pair}</td>
        <td style={{ ...tdStyle, color: dirColor, fontWeight: 700 }}>{signal.direction}</td>
        <td style={tdStyle} className="mono">{(signal.confidence * 100).toFixed(0)}%</td>
        <td style={{ ...tdStyle, color: agreementColor, fontSize: 11 }}>{signal.agent_agreement}</td>
        <td style={{ ...tdStyle, color: 'var(--text2)', fontSize: 11 }}>{signal.macro_regime || '?'}</td>
        <td style={tdStyle} className="mono">
          {signal.price_at_signal ? signal.price_at_signal.toFixed(decimals) : '—'}
        </td>
        <td style={{ ...tdStyle, color: driverColor, fontSize: 11, fontWeight: 600 }} className="mono">
          {signal.source?.toUpperCase() || 'MACRO'}
        </td>
        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text3)', fontSize: 11 }}>
          {isExpanded ? '▼' : '▶'}
        </td>
      </tr>

      {isExpanded && (
        <tr>
          <td colSpan={9} style={{
            padding: '16px 20px',
            background: 'var(--bg3)',
            borderBottom: '1px solid var(--border)',
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr 1fr 1fr', gap: 16 }}>
              {/* Agent Signals */}
              <div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 8, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Agent Signals
                </div>
                <AgentSignalRow label="Macro" value={signal.macro_regime} />
                <AgentSignalRow label="Technical" value={signal.tech_signal} />
                <AgentSignalRow label="Sentiment" value={signal.sent_signal} />

                {signal.entry_low && signal.entry_high && (
                  <>
                    <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginTop: 12, marginBottom: 8, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                      Trade Levels
                    </div>
                    <div className="mono" style={{ fontSize: 11, color: 'var(--text2)', marginBottom: 4 }}>
                      Entry: {signal.entry_low.toFixed(decimals)}–{signal.entry_high.toFixed(decimals)}
                    </div>
                    {signal.stop_estimate && (
                      <div className="mono" style={{ fontSize: 11, color: 'var(--red)', marginBottom: 4 }}>
                        Stop: {signal.stop_estimate.toFixed(decimals)}
                      </div>
                    )}
                    {signal.target_estimate && (
                      <div className="mono" style={{ fontSize: 11, color: 'var(--green)' }}>
                        Target: {signal.target_estimate.toFixed(decimals)}
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Reasoning */}
              <div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 8, letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  Reasoning
                </div>
                <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.6 }}>
                  {signal.reasoning || 'No reasoning available'}
                </div>
              </div>

              {/* Analyst Reports — Macro */}
              <AnalystReport
                label="Macro"
                signal={signal.macro_regime}
                narrative={signal.macro_analyst}
                keyFeature={signal.macro_key_feat}
                override={signal.macro_override}
                features={[
                  signal.yield_z != null ? `Yield curve: ${signal.yield_z > 0.3 ? 'steepening' : signal.yield_z < -0.3 ? 'inverted' : 'flat'}` : null,
                  signal.vix_z   != null ? `Volatility: ${signal.vix_z > 0.5 ? 'elevated' : signal.vix_z < -0.5 ? 'suppressed' : 'normal'}` : null,
                  signal.carry_signal != null && signal.carry_signal !== 0 ? `Carry: ${signal.carry_signal > 0 ? 'USD favoured' : 'USD unfavoured'}` : null,
                ].filter(Boolean) as string[]}
              />

              {/* Analyst Reports — Technical */}
              <AnalystReport
                label="Technical"
                signal={signal.tech_signal}
                narrative={signal.tech_analyst}
                keyFeature={signal.tech_key_feat}
                override={signal.tech_override}
                features={[
                  signal.rsi14     != null ? `RSI: ${signal.rsi14.toFixed(0)} (${signal.rsi14 > 70 ? 'overbought' : signal.rsi14 < 30 ? 'oversold' : 'neutral'})` : null,
                  signal.macd_hist != null ? `MACD: ${signal.macd_hist > 0 ? 'bullish momentum' : 'bearish momentum'}` : null,
                  signal.bb_pos    != null ? `Bollinger: ${signal.bb_pos > 0.8 ? 'upper band' : signal.bb_pos < 0.2 ? 'lower band' : 'mid-range'}` : null,
                ].filter(Boolean) as string[]}
              />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function AgentSignalRow({ label, value }: { label: string; value: string }) {
  const upper = value.toUpperCase();
  const color =
    upper.includes('BUY') || upper.includes('BULLISH') ? 'var(--green)' :
    upper.includes('SELL') || upper.includes('BEARISH') ? 'var(--red)'  : 'var(--text3)';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 5 }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }} />
      <span style={{ fontSize: 11, color: 'var(--text3)' }}>{label}:</span>
      <span style={{ fontSize: 11, color, fontWeight: 600 }}>{value}</span>
    </div>
  );
}

function AnalystReport({ label, signal, features, narrative, keyFeature, override }: {
  label: string;
  signal: string;
  features: string[];
  narrative?: string;
  keyFeature?: string;
  override?: boolean;
}) {
  const upper = signal.toUpperCase();
  const color =
    upper.includes('BUY') || upper.includes('BULLISH') ? 'var(--green)' :
    upper.includes('SELL') || upper.includes('BEARISH') ? 'var(--red)'  : 'var(--text3)';
  const isOverride = override || upper.includes('OVERRIDE');

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '10px 12px',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--cyan)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          {label}
        </span>
        <span style={{
          padding: '2px 6px',
          borderRadius: 3,
          fontSize: 9,
          fontWeight: 700,
          background: color + '18',
          color,
          border: `1px solid ${color}40`,
        }}>
          {signal.toUpperCase()}
        </span>
        {keyFeature && (
          <span className="mono" style={{
            fontSize: 9,
            color: 'var(--cyan)',
            background: 'rgba(0,212,255,0.08)',
            border: '1px solid rgba(0,212,255,0.2)',
            padding: '1px 5px',
            borderRadius: 3,
          }}>
            {keyFeature.toUpperCase()}
          </span>
        )}
        {isOverride && (
          <span style={{
            padding: '2px 5px',
            borderRadius: 3,
            fontSize: 9,
            fontWeight: 700,
            background: 'rgba(255,71,87,0.15)',
            color: 'var(--red)',
            border: '1px solid rgba(255,71,87,0.3)',
          }}>
            OVERRIDE
          </span>
        )}
      </div>
      {narrative && (
        <p style={{ fontSize: 11, color: 'var(--text2)', lineHeight: 1.55, marginBottom: features.length > 0 ? 8 : 0 }}>
          {narrative}
        </p>
      )}
      {features.length > 0 && (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {features.map(f => (
            <span key={f} className="mono" style={{
              fontSize: 9,
              color: 'var(--text3)',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              padding: '2px 5px',
              borderRadius: 3,
            }}>
              {f}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

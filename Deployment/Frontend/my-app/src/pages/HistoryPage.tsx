import { useState, useEffect } from 'react';
import type { Signal } from '../Types';
import { API_BASE_URL } from '../config/constants';

export default function HistoryPage() {
  const [history, setHistory] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [selectedPair, setSelectedPair] = useState<string>('all');
  const [selectedDirection, setSelectedDirection] = useState<string>('all');
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  useEffect(() => {
    fetchHistory();
  }, []);

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
    const headers = ['Timestamp', 'Pair', 'Direction', 'Confidence', 'Agreement', 'Regime', 'Price', 'Reasoning'];
    const rows = filteredHistory.map(s => [
      s.timestamp,
      s.pair.replace('=X', ''),
      s.direction,
      (s.confidence * 100).toFixed(0) + '%',
      s.agent_agreement,
      s.macro_regime,
      s.price_at_signal || '',
      `"${s.reasoning.replace(/"/g, '""')}"`,
    ]);

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fx-alphalab-history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: 'var(--bg)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        color: 'var(--text3)',
      }}>
        Loading history...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: 'var(--bg)', 
        padding: 40,
        color: 'var(--red)',
      }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Header */}
      <div style={{
        background: 'var(--bg1)',
        borderBottom: '1px solid var(--border)',
        padding: '16px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <h1 className="mono" style={{ fontSize: 20, fontWeight: 600, color: 'var(--amber)', marginBottom: 4 }}>
            Signal History
          </h1>
          <div style={{ fontSize: 13, color: 'var(--text3)' }}>
            {filteredHistory.length} signals {selectedPair !== 'all' || selectedDirection !== 'all' ? '(filtered)' : ''}
          </div>
        </div>
        <button
          onClick={exportToCSV}
          disabled={filteredHistory.length === 0}
          style={{
            background: filteredHistory.length > 0 ? 'var(--amber)' : 'var(--bg3)',
            color: filteredHistory.length > 0 ? 'var(--bg)' : 'var(--text3)',
            border: 'none',
            padding: '10px 20px',
            borderRadius: 6,
            fontSize: 13,
            fontWeight: 600,
            cursor: filteredHistory.length > 0 ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s ease',
          }}
        >
          Export CSV
        </button>
      </div>

      {/* Filters */}
      <div style={{
        background: 'var(--bg2)',
        borderBottom: '1px solid var(--border)',
        padding: '12px 24px',
        display: 'flex',
        gap: 16,
        alignItems: 'center',
      }}>
        <span style={{ fontSize: 12, color: 'var(--text3)', fontWeight: 600 }}>FILTERS:</span>
        
        <select
          value={selectedPair}
          onChange={(e) => setSelectedPair(e.target.value)}
          style={{
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            padding: '6px 12px',
            borderRadius: 4,
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          <option value="all">All Pairs</option>
          <option value="EURUSD">EURUSD</option>
          <option value="GBPUSD">GBPUSD</option>
          <option value="USDJPY">USDJPY</option>
        </select>

        <select
          value={selectedDirection}
          onChange={(e) => setSelectedDirection(e.target.value)}
          style={{
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            padding: '6px 12px',
            borderRadius: 4,
            fontSize: 12,
            cursor: 'pointer',
          }}
        >
          <option value="all">All Directions</option>
          <option value="BUY">BUY</option>
          <option value="SELL">SELL</option>
          <option value="HOLD">HOLD</option>
        </select>

        {(selectedPair !== 'all' || selectedDirection !== 'all') && (
          <button
            onClick={() => {
              setSelectedPair('all');
              setSelectedDirection('all');
            }}
            style={{
              background: 'transparent',
              border: '1px solid var(--border)',
              color: 'var(--text3)',
              padding: '6px 12px',
              borderRadius: 4,
              fontSize: 11,
              cursor: 'pointer',
            }}
          >
            Clear Filters
          </button>
        )}
      </div>

      {/* Table */}
      <div style={{ padding: 24 }}>
        {filteredHistory.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: 60,
            color: 'var(--text3)',
            fontSize: 14,
          }}>
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
                  <th style={thStyle}>Time</th>
                  <th style={thStyle}>Pair</th>
                  <th style={thStyle}>Direction</th>
                  <th style={thStyle}>Confidence</th>
                  <th style={thStyle}>Agreement</th>
                  <th style={thStyle}>Regime</th>
                  <th style={thStyle}>Price</th>
                  <th style={thStyle}>Lifecycle</th>
                  <th style={thStyle}></th>
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

const thStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--text3)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
};

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: 13,
  borderBottom: '1px solid var(--border)',
};

function HistoryRow({ signal, isExpanded, onToggle }: { 
  signal: Signal; 
  isExpanded: boolean; 
  onToggle: () => void;
}) {
  const directionColor = 
    signal.direction === 'BUY' ? 'var(--green)' :
    signal.direction === 'SELL' ? 'var(--red)' :
    'var(--text3)';

  const agreementColor =
    signal.agent_agreement === 'FULL' ? 'var(--green)' :
    signal.agent_agreement === 'PARTIAL' ? 'var(--amber)' :
    'var(--text3)';

  const lifecycleColor =
    signal.lifecycle_status === 'active' ? 'var(--green)' :
    signal.lifecycle_status === 'near_expiry' ? 'var(--amber)' :
    'var(--text3)';

  return (
    <>
      <tr style={{ cursor: 'pointer' }} onClick={onToggle} className="hover:bg-bg3">
        <td style={tdStyle} className="mono">
          {new Date(signal.timestamp).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })}
        </td>
        <td style={tdStyle} className="mono">
          {signal.pair.replace('=X', '')}
        </td>
        <td style={{ ...tdStyle, color: directionColor, fontWeight: 600 }}>
          {signal.direction}
        </td>
        <td style={tdStyle} className="mono">
          {(signal.confidence * 100).toFixed(0)}%
        </td>
        <td style={{ ...tdStyle, color: agreementColor }}>
          {signal.agent_agreement}
        </td>
        <td style={tdStyle}>
          {signal.macro_regime}
        </td>
        <td style={tdStyle} className="mono">
          {signal.price_at_signal?.toFixed(5) || '—'}
        </td>
        <td style={{ ...tdStyle, color: lifecycleColor, fontSize: 11 }}>
          {signal.lifecycle_status || 'active'}
        </td>
        <td style={{ ...tdStyle, textAlign: 'right' }}>
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>
            {isExpanded ? '▼' : '▶'}
          </span>
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={9} style={{
            padding: 20,
            background: 'var(--bg3)',
            borderBottom: '1px solid var(--border)',
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
              {/* Left column */}
              <div>
                <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8, fontWeight: 600 }}>
                  AGENT SIGNALS
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: 12 }}>
                    <span style={{ color: 'var(--text3)' }}>Macro:</span>{' '}
                    <span style={{ color: 'var(--text)' }}>{signal.tech_signal}</span>
                  </div>
                  <div style={{ fontSize: 12 }}>
                    <span style={{ color: 'var(--text3)' }}>Technical:</span>{' '}
                    <span style={{ color: 'var(--text)' }}>{signal.tech_signal}</span>
                  </div>
                  <div style={{ fontSize: 12 }}>
                    <span style={{ color: 'var(--text3)' }}>Sentiment:</span>{' '}
                    <span style={{ color: 'var(--text)' }}>{signal.sent_signal}</span>
                  </div>
                </div>

                {signal.entry_low && signal.entry_high && (
                  <>
                    <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 16, marginBottom: 8, fontWeight: 600 }}>
                      TRADE LEVELS
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      <div style={{ fontSize: 12 }} className="mono">
                        <span style={{ color: 'var(--text3)' }}>Entry:</span>{' '}
                        <span style={{ color: 'var(--text)' }}>
                          {signal.entry_low.toFixed(5)} - {signal.entry_high.toFixed(5)}
                        </span>
                      </div>
                      {signal.stop_estimate && (
                        <div style={{ fontSize: 12 }} className="mono">
                          <span style={{ color: 'var(--text3)' }}>Stop:</span>{' '}
                          <span style={{ color: 'var(--red)' }}>{signal.stop_estimate.toFixed(5)}</span>
                        </div>
                      )}
                      {signal.target_estimate && (
                        <div style={{ fontSize: 12 }} className="mono">
                          <span style={{ color: 'var(--text3)' }}>Target:</span>{' '}
                          <span style={{ color: 'var(--green)' }}>{signal.target_estimate.toFixed(5)}</span>
                        </div>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Right column */}
              <div>
                <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 8, fontWeight: 600 }}>
                  REASONING
                </div>
                <div style={{
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: 'var(--text2)',
                  whiteSpace: 'pre-wrap',
                }}>
                  {signal.reasoning}
                </div>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

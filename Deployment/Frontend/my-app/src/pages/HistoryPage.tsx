import { useState, useEffect } from 'react';
import type { Signal } from '../Types';
import { API_BASE_URL } from '../config/constants';

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
      setHistory((data.history || []).filter((s: Signal | null) => s && s.pair));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  const filteredHistory = history.filter(signal => {
    if (!signal || !signal.pair) return false;
    if (selectedPair !== 'all' && signal.pair.replace('=X', '') !== selectedPair) return false;
    if (selectedDirection !== 'all' && signal.direction !== selectedDirection) return false;
    return true;
  });

  const exportToCSV = () => {
    const headers = ['Timestamp', 'Pair', 'Direction', 'Confidence', 'Agreement', 'Regime', 'Price', 'Key Driver'];
    const rows = filteredHistory.map(s => [
      s.timestamp || '',
      (s.pair || '').replace('=X', ''),
      s.direction || '',
      ((s.confidence || 0) * 100).toFixed(0) + '%',
      s.agent_agreement || '',
      s.macro_regime || '',
      s.price_at_signal || '',
      s.key_driver || '',
    ]);
    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `fx-alphalab-history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click(); URL.revokeObjectURL(url);
  };

  if (loading) return <PageShell><div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)', fontSize: 14 }}>Loading history...</div></PageShell>;
  if (error) return <PageShell><div style={{ textAlign: 'center', padding: 60, color: 'var(--sell)', fontSize: 14 }}>Error: {error}</div></PageShell>;

  return (
    <PageShell>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div>
          <h1 className="mono" style={{ fontSize: 20, fontWeight: 700, color: 'var(--cyan)', marginBottom: 4, letterSpacing: '-0.3px' }}>Signal Ledger</h1>
          <div style={{ fontSize: 12, color: 'var(--text3)' }}>{filteredHistory.length} records {selectedPair !== 'all' || selectedDirection !== 'all' ? '(filtered)' : ''}</div>
        </div>
        <button onClick={exportToCSV} disabled={filteredHistory.length === 0} style={{
          background: filteredHistory.length > 0 ? 'var(--cyan)' : 'var(--bg3)', color: filteredHistory.length > 0 ? '#000' : 'var(--text3)',
          border: 'none', padding: '10px 20px', borderRadius: 8, fontSize: 12, fontWeight: 600, cursor: filteredHistory.length > 0 ? 'pointer' : 'not-allowed',
        }}>Export CSV</button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16, flexWrap: 'wrap' }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' }}>Filter</span>
        <select value={selectedPair} onChange={e => setSelectedPair(e.target.value)} style={selectStyle}>
          <option value="all">All Pairs</option><option value="EURUSD">EURUSD</option><option value="GBPUSD">GBPUSD</option><option value="USDJPY">USDJPY</option>
        </select>
        <select value={selectedDirection} onChange={e => setSelectedDirection(e.target.value)} style={selectStyle}>
          <option value="all">All Directions</option><option value="BUY">BUY</option><option value="SELL">SELL</option><option value="HOLD">HOLD</option>
        </select>
        {(selectedPair !== 'all' || selectedDirection !== 'all') && (
          <button onClick={() => { setSelectedPair('all'); setSelectedDirection('all'); }} style={{ background: 'transparent', border: '1px solid var(--border)', color: 'var(--text3)', padding: '6px 12px', borderRadius: 6, fontSize: 10, cursor: 'pointer' }}>Clear</button>
        )}
      </div>

      {/* Table */}
      {filteredHistory.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 60, color: 'var(--text3)', fontSize: 14 }}>No signals found</div>
      ) : (
        <div style={{ background: 'var(--bg1)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: 'var(--bg2)', borderBottom: '1px solid var(--border)' }}>
                {['Time', 'Pair', 'Direction', 'Conf', 'Agreement', 'Regime', 'Price', 'Driver', ''].map(h => (
                  <th key={h} className="mono" style={thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filteredHistory.map((signal, idx) => (
                <HistoryRow key={signal.timestamp + '-' + idx} signal={signal} isExpanded={expandedRow === idx} onToggle={() => setExpandedRow(expandedRow === idx ? null : idx)} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </PageShell>
  );
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      <div style={{ background: 'var(--bg1)', borderBottom: '1px solid var(--border)', padding: '12px 24px', display: 'flex', alignItems: 'center', gap: 16, backdropFilter: 'blur(12px)', position: 'sticky', top: 0, zIndex: 50 }}>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: 'linear-gradient(135deg, var(--cyan), var(--violet))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 800, color: '#000', boxShadow: '0 0 12px rgba(0,229,255,0.15)' }}>FX</div>
        <span className="mono" style={{ fontSize: 14, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.2px' }}>AlphaLab</span>
        <span style={{ color: 'var(--text3)', fontSize: 11, marginLeft: 'auto' }}>History</span>
      </div>
      <div style={{ maxWidth: 1400, margin: '0 auto', padding: '24px 20px' }}>{children}</div>
    </div>
  );
}

function HistoryRow({ signal, isExpanded, onToggle }: { signal: Signal; isExpanded: boolean; onToggle: () => void }) {
  if (!signal || !signal.pair) return null;
  const dirColor = signal.direction === 'BUY' ? 'var(--buy)' : signal.direction === 'SELL' ? 'var(--sell)' : 'var(--hold)';
  const agreementColor = signal.agent_agreement === 'FULL' ? 'var(--emerald)' : signal.agent_agreement === 'PARTIAL' ? 'var(--amber)' : 'var(--text3)';
  const ts = (() => { try { const d = new Date(signal.timestamp); return isNaN(d.getTime()) ? '--' : d.toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }); } catch { return '--'; } })();

  return (
    <>
      <tr onClick={onToggle} style={{ cursor: 'pointer', borderBottom: '1px solid var(--border)', transition: 'background 0.15s', background: isExpanded ? 'var(--bg2)' : 'transparent' }}>
        <td style={tdStyle} className="mono">{ts}</td>
        <td style={{ ...tdStyle, fontWeight: 600 }} className="mono">{signal.pair.replace('=X', '')}</td>
        <td style={{ ...tdStyle, color: dirColor, fontWeight: 700 }}>{signal.direction}</td>
        <td style={tdStyle} className="mono">{((signal.confidence || 0) * 100).toFixed(0)}%</td>
        <td style={{ ...tdStyle, color: agreementColor, fontWeight: 600, fontSize: 11 }}>{signal.agent_agreement}</td>
        <td style={tdStyle}>{signal.macro_regime || '?'}</td>
        <td style={tdStyle} className="mono">{signal.price_at_signal?.toFixed(5) || '—'}</td>
        <td style={{ ...tdStyle, color: 'var(--cyan)', fontSize: 10 }}>{signal.key_driver || '—'}</td>
        <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--text3)' }}>{isExpanded ? '▼' : '▶'}</td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={9} style={{ padding: 18, background: 'var(--bg2)', borderBottom: '1px solid var(--border)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 18 }}>
              <div>
                <div style={sectionLabel}>Agent Signals</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11 }}>
                  <AgentRow label="Macro" value={signal.macro_regime} color="var(--macro)" />
                  <AgentRow label="Technical" value={signal.tech_signal} color="var(--tech)" />
                  <AgentRow label="Sentiment" value={signal.sent_signal} color="var(--sent)" />
                </div>
              </div>
              <div>
                <div style={sectionLabel}>Reasoning</div>
                <div style={{ fontSize: 12, color: 'var(--text2)', lineHeight: 1.6, fontStyle: 'italic' }}>{signal.reasoning || 'No reasoning available'}</div>
                {signal.risk_note && <div style={{ marginTop: 10, padding: '8px 10px', background: 'var(--sell)06', border: '1px solid var(--sell)18', borderRadius: 6, fontSize: 10, color: 'var(--sell)' }}>⚠ {signal.risk_note}</div>}
              </div>
              <div>
                <div style={sectionLabel}>Analyst Reports</div>
                {signal.macro_agent && <MiniAnalyst data={typeof signal.macro_agent === 'string' ? JSON.parse(signal.macro_agent) : signal.macro_agent} color="var(--macro)" label="Macro" />}
                {signal.tech_agent && <MiniAnalyst data={typeof signal.tech_agent === 'string' ? JSON.parse(signal.tech_agent) : signal.tech_agent} color="var(--tech)" label="Technical" />}
                {signal.sent_agent && <MiniAnalyst data={typeof signal.sent_agent === 'string' ? JSON.parse(signal.sent_agent) : signal.sent_agent} color="var(--sent)" label="Sentiment" />}
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function AgentRow({ label, value, color }: { label: string; value: string; color: string }) {
  const v = (value || '').toUpperCase();
  const dot = v.includes('BUY') || v.includes('BULL') ? 'var(--buy)' : v.includes('SELL') || v.includes('BEAR') ? 'var(--sell)' : 'var(--hold)';
  return <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><span style={{ color: 'var(--text3)', minWidth: 65 }}>{label}</span><div style={{ width: 5, height: 5, borderRadius: '50%', background: dot }} /><span style={{ color: 'var(--text)' }}>{value || '?'}</span></div>;
}

function MiniAnalyst({ data, color, label }: { data: any; color: string; label: string }) {
  return (
    <div style={{ background: 'var(--bg3)', border: `1px solid ${color}18`, borderLeft: `2px solid ${color}`, borderRadius: 5, padding: 8, marginBottom: 6, fontSize: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ color, fontWeight: 700, fontSize: 9, textTransform: 'uppercase' }}>{label}</span>
        <span className="mono" style={{ color: 'var(--text2)', fontSize: 9 }}>{data.llm_signal} · {((data.llm_conf || 0) * 100).toFixed(0)}%</span>
      </div>
      {data.reasoning && <div style={{ color: 'var(--text2)', lineHeight: 1.4, fontStyle: 'italic', fontSize: 9 }}>{data.reasoning.slice(0, 120)}</div>}
      {data.override_flag && <span className="badge" style={{ background: 'var(--amber)12', color: 'var(--amber)', fontSize: 7, marginTop: 4, display: 'inline-block' }}>OVERRIDE</span>}
    </div>
  );
}

const thStyle: React.CSSProperties = { padding: '11px 14px', textAlign: 'left', fontSize: 9, fontWeight: 600, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '1px' };
const tdStyle: React.CSSProperties = { padding: '11px 14px', fontSize: 12 };
const selectStyle: React.CSSProperties = { background: 'var(--bg2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '7px 12px', borderRadius: 6, fontSize: 11, cursor: 'pointer', outline: 'none' };
const sectionLabel: React.CSSProperties = { fontSize: 9, color: 'var(--text3)', marginBottom: 8, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px' };
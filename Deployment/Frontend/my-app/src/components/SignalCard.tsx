import { useState } from 'react';
import type { Signal, Price, LiveContext } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';

interface SignalCardProps {
  signal: Signal;
  price?: Price;
  liveContext?: LiveContext;
  isSelected: boolean;
  onClick: () => void;
}

export default function SignalCard({ signal, price, liveContext, isSelected, onClick }: SignalCardProps) {
  const [expanded, setExpanded] = useState(false);
  const pair = signal.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;

  const dirColor = signal.direction === 'BUY' ? 'var(--buy)' : signal.direction === 'SELL' ? 'var(--sell)' : 'var(--hold)';
  const agreementColor = signal.agent_agreement === 'FULL' ? 'var(--emerald)' : signal.agent_agreement === 'PARTIAL' ? 'var(--amber)' : 'var(--text3)';

  const currentPrice = price?.price || signal.price_at_signal || 0;
  const priceChange = price?.change || 0;
  const priceChangePct = price?.change_pct || 0;

  const parsePacket = (data: any) => {
    if (!data) return null;
    if (typeof data === 'string') { try { return JSON.parse(data); } catch { return null; } }
    return data;
  };

  const macroAgent = parsePacket((signal as any).macro_agent);
  const techAgent = parsePacket((signal as any).tech_agent);
  const sentAgent = parsePacket((signal as any).sent_agent);
  const convictionData = parsePacket((signal as any).conviction_data);
  const hasAnalystPackets = !!(macroAgent || techAgent || sentAgent);

  return (
    <div onClick={onClick} className={`card-glow ${isSelected ? 'selected' : ''}`} style={{
      background: 'var(--bg1)',
      border: '1px solid var(--border)',
      borderRadius: 12,
      padding: 18,
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      position: 'relative',
      overflow: 'hidden',
      minHeight: 280,
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Top accent line */}
      <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, ${dirColor}, transparent)`, opacity: isSelected ? 1 : 0.5 }} />

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
            <span className="mono" style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>{pair}</span>
            {signal.source === 'fallback' && <span className="badge badge-outline" style={{ color: 'var(--amber)', fontSize: 7 }}>R</span>}
          </div>
          <div className="mono" style={{ fontSize: 9, color: 'var(--text3)' }}>
            {signal.key_driver ? `DRIVER: ${signal.key_driver}` : signal.age_hours ? `${signal.age_hours.toFixed(1)}h ago` : ''}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: 18, fontWeight: 700, color: 'var(--text)' }}>{currentPrice.toFixed(decimals)}</div>
          {price && (
            <div className="mono" style={{ fontSize: 10, color: priceChange >= 0 ? 'var(--buy)' : 'var(--sell)' }}>
              {priceChange >= 0 ? '↑' : '↓'} {Math.abs(priceChange).toFixed(decimals)} ({priceChangePct >= 0 ? '+' : ''}{priceChangePct.toFixed(2)}%)
            </div>
          )}
        </div>
      </div>

      {/* Direction + Agreement + Size */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <span className="badge" style={{ background: dirColor + '18', color: dirColor, border: `1px solid ${dirColor}30`, fontSize: 11, padding: '5px 10px', borderRadius: 6, fontWeight: 700 }}>{signal.direction}</span>
        <span className="badge badge-outline" style={{ color: agreementColor, fontSize: 9 }}>{signal.agent_agreement}</span>
        {signal.position_size > 0 && <span className="badge" style={{ background: 'var(--bg3)', color: 'var(--text2)', fontSize: 9, marginLeft: 'auto' }}>{(signal.position_size * 100).toFixed(0)}%</span>}
      </div>

      {/* Confidence */}
      <div style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span className="mono" style={{ fontSize: 8, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '1px' }}>Conviction</span>
          <span className="mono" style={{ fontSize: 10, color: dirColor, fontWeight: 600 }}>{(signal.confidence * 100).toFixed(0)}%</span>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${signal.confidence * 100}%`, background: `linear-gradient(90deg, ${dirColor}, ${dirColor}60)` }} />
        </div>
      </div>

      {/* Conviction Scores */}
      {convictionData && (
        <div style={{ marginBottom: 10 }}>
          <div style={{ display: 'flex', gap: 12, fontSize: 9 }}>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ color: 'var(--sell)', fontWeight: 500 }}>SELL</span>
                <span className="mono" style={{ color: 'var(--text2)' }}>{convictionData.sell?.toFixed(1)}</span>
              </div>
              <div className="progress-track" style={{ height: 2 }}>
                <div className="progress-fill" style={{ width: `${(convictionData.sell/4)*100}%`, background: 'var(--sell)', opacity: 0.7, height: 2 }} />
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                <span style={{ color: 'var(--buy)', fontWeight: 500 }}>BUY</span>
                <span className="mono" style={{ color: 'var(--text2)' }}>{convictionData.buy?.toFixed(1)}</span>
              </div>
              <div className="progress-track" style={{ height: 2 }}>
                <div className="progress-fill" style={{ width: `${(convictionData.buy/4)*100}%`, background: 'var(--buy)', opacity: 0.7, height: 2 }} />
              </div>
            </div>
          </div>
          {(convictionData.symmetry_active || convictionData.tokyo_active) && (
            <div style={{ display: 'flex', gap: 4, marginTop: 4 }}>
              {convictionData.symmetry_active && <span className="badge" style={{ background: 'var(--amber)15', color: 'var(--amber)', fontSize: 7 }}>SYM</span>}
              {convictionData.tokyo_active && <span className="badge" style={{ background: 'var(--cyan)15', color: 'var(--cyan)', fontSize: 7 }}>TKY</span>}
            </div>
          )}
        </div>
      )}

      {/* Agent Pills */}
      <div style={{ display: 'flex', gap: 5, marginBottom: hasAnalystPackets ? 8 : 0 }}>
        <AgentPill label="MACRO" value={signal.macro_regime} color="var(--macro)" />
        <AgentPill label="TECH" value={signal.tech_signal} color="var(--tech)" />
        <AgentPill label="SENT" value={signal.sent_signal} color="var(--sent)" />
      </div>

      {/* Reasoning Preview */}
      {signal.reasoning && (
        <div style={{ fontSize: 10, color: 'var(--text2)', lineHeight: 1.5, fontStyle: 'italic', opacity: 0.75, flex: 1 }}>
          {signal.reasoning.slice(0, 100)}{signal.reasoning.length > 100 ? '...' : ''}
        </div>
      )}

      {/* Expand Button */}
      {hasAnalystPackets && (
        <button onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }} style={{
          width: '100%', background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 6,
          padding: '6px 10px', color: 'var(--text2)', fontSize: 9, fontWeight: 600, cursor: 'pointer',
          textTransform: 'uppercase', letterSpacing: '0.5px', marginTop: 'auto',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 4,
        }}>
          {expanded ? '▼ Hide' : '▶'} Analyst Breakdown
        </button>
      )}

      {/* Analyst Sub-cards */}
      {expanded && hasAnalystPackets && (
        <div className="animate-slide-up" style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
          {macroAgent && <AnalystSubCard data={macroAgent} color="var(--macro)" label="Macro" />}
          {techAgent && <AnalystSubCard data={techAgent} color="var(--tech)" label="Technical" />}
          {sentAgent && <AnalystSubCard data={sentAgent} color="var(--sent)" label="Sentiment" />}
        </div>
      )}

      {/* Risk Note */}
      {signal.risk_note && (
        <div style={{ marginTop: 10, padding: '6px 8px', background: 'var(--sell)06', border: '1px solid var(--sell)18', borderRadius: 6, fontSize: 9, color: 'var(--sell)', lineHeight: 1.4 }}>
          ⚠ {signal.risk_note}
        </div>
      )}
    </div>
  );
}

function AgentPill({ label, value, color }: { label: string; value: string; color: string }) {
  const v = (value || '').toUpperCase();
  const active = v.includes('BUY') || v.includes('BULL');
  const negative = v.includes('SELL') || v.includes('BEAR');
  return (
    <div style={{ background: 'var(--bg3)', border: `1px solid ${color}30`, borderRadius: 12, padding: '3px 8px', fontSize: 8, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ color: 'var(--text3)' }}>{label}</span>
      <div style={{ width: 4, height: 4, borderRadius: '50%', background: active ? 'var(--buy)' : negative ? 'var(--sell)' : 'var(--hold)' }} />
      <span style={{ color: active ? 'var(--buy)' : negative ? 'var(--sell)' : 'var(--text2)' }}>{value}</span>
    </div>
  );
}

function AnalystSubCard({ data, color, label }: { data: any; color: string; label: string }) {
  const safeConf = data.llm_conf || 0;
  return (
    <div style={{ background: 'var(--bg2)', border: `1px solid ${color}20`, borderLeft: `2px solid ${color}`, borderRadius: 5, padding: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          <span style={{ fontSize: 9, fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '0.5px' }}>{label}</span>
          {data.override_flag && <span className="badge" style={{ background: 'var(--amber)15', color: 'var(--amber)', fontSize: 6 }}>OVERRIDE</span>}
        </div>
        <span className="mono" style={{ fontSize: 9, color: 'var(--text2)' }}>{data.llm_signal} · {(safeConf * 100).toFixed(0)}%</span>
      </div>
      {data.reasoning && <div style={{ fontSize: 9.5, color: 'var(--text2)', lineHeight: 1.5, marginBottom: 6, fontStyle: 'italic' }}>{data.reasoning}</div>}
      {data.key_drivers?.length > 0 && (
        <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', marginBottom: 4 }}>
          {data.key_drivers.map((d: string, i: number) => (
            <span key={i} className="badge" style={{ background: color + '10', color, fontSize: 7, border: `1px solid ${color}15` }}>{d}</span>
          ))}
        </div>
      )}
      {data.risk_flags?.length > 0 && (
        <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap' }}>
          {data.risk_flags.map((f: string, i: number) => (
            <span key={i} className="badge" style={{ background: 'var(--sell)08', color: 'var(--sell)', fontSize: 7, border: '1px solid var(--sell)12' }}>{f}</span>
          ))}
        </div>
      )}
      {data.override_reason && <div style={{ marginTop: 4, fontSize: 8, color: 'var(--amber)', fontStyle: 'italic' }}>Reason: {data.override_reason}</div>}
    </div>
  );
}
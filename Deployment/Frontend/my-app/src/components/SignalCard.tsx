import type { Signal } from '../Types';
import { fmtTime, fmtSize, agreementColor, pairLabel } from '../utils/formatters';

interface Props {
  signal:     Signal;
  isSelected: boolean;
  onClick:    () => void;
}

function AgentPill({ label, value, match, conflict }: { label: string; value: string; match?: boolean; conflict?: boolean }) {
  const base: React.CSSProperties = {
    fontFamily: 'var(--font-mono)', fontSize: 10, padding: '2px 8px',
    borderRadius: 99, border: '1px solid',
  };
  if (match)    return <span style={{ ...base, background: 'rgba(0,217,126,0.1)', color: 'var(--buy)', borderColor: 'rgba(0,217,126,0.3)' }}>{label}: {value}</span>;
  if (conflict) return <span style={{ ...base, background: 'rgba(255,77,109,0.1)', color: 'var(--sell)', borderColor: 'rgba(255,77,109,0.3)' }}>{label}: {value}</span>;
  return <span style={{ ...base, background: 'transparent', color: 'var(--text-muted)', borderColor: 'var(--border)' }}>{label}: {value}</span>;
}

function dirStyle(dir: string): React.CSSProperties {
  if (dir === 'BUY')  return { background: 'rgba(0,217,126,0.12)', color: 'var(--buy)',  border: '1px solid rgba(0,217,126,0.3)' };
  if (dir === 'SELL') return { background: 'rgba(255,77,109,0.12)', color: 'var(--sell)', border: '1px solid rgba(255,77,109,0.3)' };
  return { background: 'rgba(107,114,128,0.15)', color: 'var(--hold)', border: '1px solid rgba(107,114,128,0.3)' };
}

export default function SignalCard({ signal, isSelected, onClick }: Props) {
  const { pair, direction, confidence, position_size, macro_regime,
          tech_signal, sent_signal, agent_agreement, timestamp, source } = signal;

  const dir     = direction === 'BUY' ? 1 : direction === 'SELL' ? -1 : 0;
  const techDir = tech_signal?.includes('BUY') ? 1 : tech_signal?.includes('SELL') ? -1 : 0;
  const sentDir = sent_signal?.includes('HOLD') || sent_signal?.includes('LOW') ? 0 : sent_signal?.includes('BUY') ? 1 : -1;
  const macDir  = macro_regime === 'bullish' ? 1 : macro_regime === 'bearish' ? -1 : 0;

  const pct = Math.round(parseFloat(String(confidence)) * 100);
  const barColor = direction === 'BUY' ? 'var(--buy)' : direction === 'SELL' ? 'var(--sell)' : 'var(--hold)';

  return (
    <div
      onClick={onClick}
      className="animate-slide-up"
      style={{
        background: 'var(--card)',
        border: `1px solid ${isSelected ? 'var(--info)' : 'var(--border)'}`,
        borderRadius: 12, cursor: 'pointer',
        boxShadow: isSelected ? '0 0 0 1px rgba(56,189,248,0.2)' : 'none',
        opacity: direction === 'HOLD' ? 0.65 : 1,
        transition: 'border-color 0.15s, box-shadow 0.15s',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 14px 10px', borderBottom: '1px solid var(--border)' }}>
        <div>
          <div className="mono" style={{ fontSize: 15, fontWeight: 600, color: '#fff', letterSpacing: '0.05em' }}>
            {pairLabel(pair)}
          </div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
            {fmtTime(timestamp)}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          {source === 'groq' && (
            <span className="mono" style={{ fontSize: 10, color: 'var(--info)', border: '1px solid var(--border)', borderRadius: 4, padding: '1px 6px' }}>
              groq
            </span>
          )}
          <span className="mono" style={{ ...dirStyle(direction), fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 8 }}>
            {direction}
          </span>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 10 }}>
        {/* Confidence bar */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>confidence</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{pct}%</span>
          </div>
          <div style={{ height: 3, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${pct}%`, background: barColor, borderRadius: 2, transition: 'width 0.5s ease' }} />
          </div>
        </div>

        {/* Agent pills */}
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          <AgentPill label="macro" value={macro_regime} match={macDir === dir && dir !== 0} conflict={macDir === -dir && dir !== 0} />
          <AgentPill label="tech"  value={tech_signal?.split(' ')[0] || '--'} match={techDir === dir && dir !== 0} conflict={techDir === -dir && dir !== 0} />
          <AgentPill label="sent"  value={sent_signal?.includes('LOW') ? 'LOW' : sent_signal?.split(' ')[0] || '--'} match={sentDir === dir && dir !== 0} conflict={sentDir === -dir && dir !== 0} />
        </div>
      </div>

      {/* Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 14px', borderTop: '1px solid var(--border)' }}>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          size <span style={{ color: '#fff', fontWeight: 500 }}>{fmtSize(position_size)}</span>
        </span>
        <span className="mono" style={{ fontSize: 11, color: agreementColor(agent_agreement), fontWeight: 500 }}>
          {agent_agreement}
        </span>
      </div>
    </div>
  );
}
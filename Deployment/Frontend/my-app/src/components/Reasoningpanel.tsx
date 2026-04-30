import type { Signal } from '../Types';
import { fmtTime, fmtConf, fmtSize, agreementColor, pairLabel } from '../utils/formatters';

interface Props { signal: Signal | null; }

function dirStyle(dir: string): React.CSSProperties {
  if (dir === 'BUY')  return { background: 'rgba(0,217,126,0.12)', color: 'var(--buy)',  border: '1px solid rgba(0,217,126,0.3)' };
  if (dir === 'SELL') return { background: 'rgba(255,77,109,0.12)', color: 'var(--sell)', border: '1px solid rgba(255,77,109,0.3)' };
  return { background: 'rgba(107,114,128,0.15)', color: 'var(--hold)', border: '1px solid rgba(107,114,128,0.3)' };
}

function MetricBox({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div style={{ background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px' }}>
      <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 13, fontWeight: 500, color: '#fff' }}>{value}</div>
      {sub && <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

export default function ReasoningPanel({ signal }: Props) {
  if (!signal) {
    return (
      <div style={{ margin: '0 20px 16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: '32px', textAlign: 'center' }}>
        <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          ← click a signal card to see the LLM reasoning
        </span>
      </div>
    );
  }

  const { pair, direction, confidence, position_size, reasoning, key_driver,
          risk_note, macro_regime, tech_signal, sent_signal, agent_agreement,
          source, timestamp, macro_conf, tech_conf, sent_conf } = signal;

  return (
    <div className="animate-fade-in" style={{ margin: '0 20px 16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12 }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="mono" style={{ fontSize: 16, fontWeight: 600, color: '#fff', letterSpacing: '0.05em' }}>{pairLabel(pair)}</span>
          <span className="mono" style={{ ...dirStyle(direction), fontSize: 12, fontWeight: 600, padding: '4px 12px', borderRadius: 8 }}>{direction}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>conf {fmtConf(confidence)}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>{fmtTime(timestamp)}</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)', border: '1px solid var(--border)', borderRadius: 5, padding: '2px 8px' }}>
            {source || 'llm'} · llama-3.3-70b
          </span>
        </div>
      </div>

      {/* Body */}
      <div style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>

        {/* Reasoning */}
        <div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
            LLM Reasoning
          </div>
          <div style={{ background: 'var(--bg)', borderLeft: '2px solid var(--info)', borderRadius: '0 8px 8px 0', padding: '12px 14px' }}>
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              {reasoning || 'No reasoning available.'}
            </p>
          </div>
        </div>

        {/* Agent metrics */}
        <div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
            Agent outputs
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
            <MetricBox label="Macro agent" value={macro_regime}
              sub={macro_conf !== undefined ? `conf ${(parseFloat(String(macro_conf))*100).toFixed(0)}%` : undefined} />
            <MetricBox label="Tech agent" value={tech_signal?.split(' ')[0] || '--'}
              sub={tech_conf !== undefined ? `conf ${(parseFloat(String(tech_conf))*100).toFixed(0)}%` : undefined} />
            <MetricBox label="Sentiment" value={sent_signal?.includes('LOW') ? 'LOW-NEWS' : (sent_signal?.split(' ')[0] || '--')}
              sub={sent_conf !== undefined ? `conf ${(parseFloat(String(sent_conf))*100).toFixed(0)}%` : undefined} />
          </div>
        </div>

        {/* Risk note */}
        <div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
            Risk note
          </div>
          <div style={{ background: 'var(--bg)', borderLeft: '2px solid var(--sell)', borderRadius: '0 8px 8px 0', padding: '12px 14px' }}>
            <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.7 }}>
              {risk_note || 'No risk note available.'}
            </p>
          </div>
        </div>

        {/* Footer meta */}
        <div style={{ display: 'flex', gap: 20, paddingTop: 4, borderTop: '1px solid var(--border)' }}>
          {[
            { label: 'key driver',     value: key_driver || '--',             color: 'var(--info)' },
            { label: 'position size',  value: fmtSize(position_size),         color: '#fff' },
            { label: 'agreement',      value: agent_agreement,                color: agreementColor(agent_agreement) },
          ].map(({ label, value, color }) => (
            <div key={label} className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              {label} <span style={{ color, fontWeight: 500, marginLeft: 4 }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
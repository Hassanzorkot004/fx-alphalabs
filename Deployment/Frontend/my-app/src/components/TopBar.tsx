import { fmtTime, fmtCountdown } from '../utils/formatters';

interface Props {
  connected:   boolean;
  lastUpdate:  Date | null;
  nextCycle:   number | null;
  cycleNumber: number | null;
}

export default function TopBar({ connected, lastUpdate, nextCycle, cycleNumber }: Props) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '10px 20px', borderBottom: '1px solid var(--border)',
      background: 'var(--surface)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span className="mono" style={{ fontSize: 13, fontWeight: 600, letterSpacing: '0.12em', color: '#fff', textTransform: 'uppercase' }}>
          FX AlphaLab
        </span>
        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>|</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          EUR/USD · GBP/USD · USD/JPY
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <span className={connected ? 'animate-pulse-dot' : ''} style={{
            width: 7, height: 7, borderRadius: '50%',
            background: connected ? 'var(--buy)' : 'var(--sell)',
            display: 'inline-block',
          }} />
          <span className="mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
            {connected ? 'LIVE' : 'RECONNECTING'}
            {cycleNumber && <span style={{ color: 'var(--text-muted)', marginLeft: 5 }}>#{cycleNumber}</span>}
          </span>
        </div>

        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          last update <span style={{ color: 'var(--text-secondary)' }}>{fmtTime(lastUpdate)}</span>
        </span>

        <div className="mono" style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--card)', border: '1px solid var(--border)',
          borderRadius: 6, padding: '5px 12px',
        }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>next signal</span>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--info)' }}>
            {fmtCountdown(nextCycle)}
          </span>
        </div>
      </div>
    </div>
  );
}
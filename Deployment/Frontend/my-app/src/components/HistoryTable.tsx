import type { Signal } from '../Types';
import { fmtTime, fmtPips, fmtConf, fmtSize, pipsColor, pairLabel } from '../utils/formatters';

interface Props { history: Signal[]; }

function dirStyle(dir: string): React.CSSProperties {
  if (dir === 'BUY')  return { background: 'rgba(0,217,126,0.12)', color: 'var(--buy)',  border: '1px solid rgba(0,217,126,0.3)', borderRadius: 5, padding: '1px 7px', fontSize: 11 };
  if (dir === 'SELL') return { background: 'rgba(255,77,109,0.12)', color: 'var(--sell)', border: '1px solid rgba(255,77,109,0.3)', borderRadius: 5, padding: '1px 7px', fontSize: 11 };
  return { background: 'rgba(107,114,128,0.15)', color: 'var(--hold)', border: '1px solid rgba(107,114,128,0.3)', borderRadius: 5, padding: '1px 7px', fontSize: 11 };
}

const TH_STYLE: React.CSSProperties = {
  fontFamily: 'var(--font-mono)', fontSize: 10, fontWeight: 500,
  color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em',
  padding: '8px 14px', textAlign: 'left', borderBottom: '1px solid var(--border)',
};

const TD_STYLE: React.CSSProperties = {
  fontFamily: 'var(--font-mono)', fontSize: 12, padding: '9px 14px',
  borderBottom: '1px solid var(--border)', color: 'var(--text-secondary)',
};

export default function HistoryTable({ history }: Props) {
  if (!history || history.length === 0) {
    return (
      <div style={{ margin: '0 20px 16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, padding: 32, textAlign: 'center' }}>
        <span className="mono" style={{ fontSize: 12, color: 'var(--text-muted)' }}>no history yet</span>
      </div>
    );
  }

  return (
    <div style={{ margin: '0 20px 16px', background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 12, overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', borderBottom: '1px solid var(--border)' }}>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Signal history</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text-muted)' }}>{history.length} trades</span>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['Time','Pair','Signal','Conf','Size','Pips +12h','Agreement','Source'].map(h => (
                <th key={h} style={TH_STYLE}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {history.slice(0, 20).map((row, i) => (
              <tr key={i} style={{ transition: 'background 0.1s' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}>
                <td style={{ ...TD_STYLE, color: 'var(--text-muted)' }}>{fmtTime(row.timestamp)}</td>
                <td style={{ ...TD_STYLE, color: '#fff', fontWeight: 500 }}>{pairLabel(row.pair)}</td>
                <td style={TD_STYLE}><span style={dirStyle(row.direction)} className="mono">{row.direction}</span></td>
                <td style={TD_STYLE}>{fmtConf(row.confidence)}</td>
                <td style={TD_STYLE}>{fmtSize(row.position_size)}</td>
                <td style={{ ...TD_STYLE, color: row.pips !== undefined ? (parseFloat(String(row.pips)) >= 0 ? 'var(--buy)' : 'var(--sell)') : 'var(--text-muted)', fontWeight: 500 }}>
                  {row.pips !== undefined ? fmtPips(row.pips) : '—'}
                </td>
                <td style={TD_STYLE}>{row.agent_agreement}</td>
                <td style={{ ...TD_STYLE, color: 'var(--text-muted)' }}>{row.source || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
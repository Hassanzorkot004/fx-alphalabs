import type { Stats } from '../Types';
import { fmtPips } from '../utils/formatters';

interface Props { stats: Stats | null; }

function Card({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div style={{
      background: 'var(--card)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '12px 16px',
    }}>
      <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 22, fontWeight: 600, color: color || '#fff' }}>
        {value}
      </div>
      {sub && <div className="mono" style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{sub}</div>}
    </div>
  );
}

function SkeletonCard() {
  return (
    <div style={{ background: 'var(--card)', border: '1px solid var(--border)', borderRadius: 10, padding: '12px 16px' }}>
      <div style={{ height: 10, background: 'var(--border)', borderRadius: 4, width: '60%', marginBottom: 8 }} />
      <div style={{ height: 22, background: 'var(--border)', borderRadius: 4, width: '40%' }} />
    </div>
  );
}

export default function StatsRow({ stats }: Props) {
  if (!stats) {
    return (
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
        {[0,1,2,3].map(i => <SkeletonCard key={i} />)}
      </div>
    );
  }

  const wr  = (parseFloat(String(stats.win_rate)) * 100).toFixed(1);
  const pf  = parseFloat(String(stats.profit_factor)).toFixed(2);
  const dd  = parseFloat(String(stats.max_drawdown)).toFixed(2);
  const pip = parseFloat(String(stats.total_pips)).toFixed(1);
  const sh  = parseFloat(String(stats.sharpe ?? 0)).toFixed(2);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12, padding: '16px 20px', borderBottom: '1px solid var(--border)' }}>
      <Card label={`Win rate (${stats.n_trades} trades)`} value={`${wr}%`}
        color={parseFloat(wr) >= 55 ? 'var(--buy)' : 'var(--sell)'} />
      <Card label="Total pips" value={fmtPips(pip)}
        color={parseFloat(pip) >= 0 ? 'var(--buy)' : 'var(--sell)'}
        sub={`avg win +${parseFloat(String(stats.avg_win)).toFixed(1)} / avg loss ${parseFloat(String(stats.avg_loss)).toFixed(1)}`} />
      <Card label="Profit factor" value={pf}
        color={parseFloat(pf) >= 1.5 ? 'var(--buy)' : 'var(--text-secondary)'} />
      <Card label="Max drawdown" value={`${dd}%`} color="var(--sell)"
        sub={`Sharpe: ${sh}`} />
    </div>
  );
}
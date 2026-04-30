import type { Stats } from '../Types';

interface PerfStatsPanelProps {
  stats: Stats | null;
}

export default function PerfStatsPanel({ stats }: PerfStatsPanelProps) {
  if (!stats || typeof stats.n_trades === 'undefined') {
    return (
      <div style={{
        background: 'var(--bg2)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 16,
      }}>
        <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginBottom: 12 }}>
          PERFORMANCE
        </div>
        <div style={{ color: 'var(--text3)', fontSize: 12 }}>Loading stats...</div>
      </div>
    );
  }

  const winRateColor = stats.win_rate >= 0.6 ? 'var(--green)' : stats.win_rate >= 0.5 ? 'var(--amber)' : 'var(--red)';
  const pipsColor = stats.total_pips >= 0 ? 'var(--green)' : 'var(--red)';

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)' }}>
          PERFORMANCE
        </div>
        {stats.data_source && (
          <div className="mono" style={{ fontSize: 9, color: 'var(--text3)', textTransform: 'uppercase' }}>
            {stats.data_source.replace('_', ' ')}
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <StatItem label="Trades" value={stats.n_trades?.toString() || '0'} />
        <StatItem label="Win Rate" value={`${((stats.win_rate || 0) * 100).toFixed(1)}%`} color={winRateColor} />
        <StatItem label="Total Pips" value={(stats.total_pips || 0).toFixed(1)} color={pipsColor} />
        <StatItem label="Profit Factor" value={(stats.profit_factor || 0).toFixed(2)} />
        {stats.sharpe !== undefined && (
          <StatItem label="Sharpe" value={stats.sharpe.toFixed(2)} />
        )}
        {stats.max_drawdown_pips !== undefined && (
          <StatItem label="Max DD" value={`${stats.max_drawdown_pips.toFixed(0)} pips`} color="var(--red)" />
        )}
      </div>
    </div>
  );
}

function StatItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div>
      <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 4 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: color || 'var(--text)' }}>
        {value}
      </div>
    </div>
  );
}

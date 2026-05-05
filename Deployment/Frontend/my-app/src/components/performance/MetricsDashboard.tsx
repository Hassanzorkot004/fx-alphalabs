interface MetricsDashboardProps {
  summary: {
    total_signals: number;
    winning_signals: number;
    losing_signals: number;
    win_rate: number;
    total_pips: number;
    avg_win_pips: number;
    avg_loss_pips: number;
    profit_factor: number;
    max_drawdown_pips: number;
    max_drawdown_pct: number;
    sharpe_ratio: number;
    best_signal_pips: number;
    worst_signal_pips: number;
    avg_signal_duration_hours: number;
  };
}

export default function MetricsDashboard({ summary }: MetricsDashboardProps) {
  const metrics = [
    {
      label: 'Total Signals',
      value: summary.total_signals,
      format: (v: number) => v.toString(),
      color: 'var(--text)',
    },
    {
      label: 'Win Rate',
      value: summary.win_rate,
      format: (v: number) => `${(v * 100).toFixed(1)}%`,
      color: summary.win_rate >= 0.5 ? 'var(--green)' : 'var(--red)',
    },
    {
      label: 'Total Pips',
      value: summary.total_pips,
      format: (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(1)}`,
      color: summary.total_pips >= 0 ? 'var(--green)' : 'var(--red)',
    },
    {
      label: 'Profit Factor',
      value: summary.profit_factor,
      format: (v: number) => v.toFixed(2),
      color: summary.profit_factor >= 1.5 ? 'var(--green)' : summary.profit_factor >= 1 ? 'var(--amber)' : 'var(--red)',
    },
    {
      label: 'Avg Win',
      value: summary.avg_win_pips,
      format: (v: number) => `+${v.toFixed(1)} pips`,
      color: 'var(--green)',
    },
    {
      label: 'Avg Loss',
      value: summary.avg_loss_pips,
      format: (v: number) => `${v.toFixed(1)} pips`,
      color: 'var(--red)',
    },
    {
      label: 'Max Drawdown',
      value: summary.max_drawdown_pips,
      format: (v: number) => `${v.toFixed(1)} pips (${summary.max_drawdown_pct.toFixed(1)}%)`,
      color: 'var(--red)',
    },
    {
      label: 'Sharpe Ratio',
      value: summary.sharpe_ratio,
      format: (v: number) => v.toFixed(2),
      color: summary.sharpe_ratio >= 1 ? 'var(--green)' : summary.sharpe_ratio >= 0 ? 'var(--amber)' : 'var(--red)',
    },
    {
      label: 'Best Signal',
      value: summary.best_signal_pips,
      format: (v: number) => `+${v.toFixed(1)} pips`,
      color: 'var(--green)',
    },
    {
      label: 'Worst Signal',
      value: summary.worst_signal_pips,
      format: (v: number) => `${v.toFixed(1)} pips`,
      color: 'var(--red)',
    },
    {
      label: 'Avg Duration',
      value: summary.avg_signal_duration_hours,
      format: (v: number) => `${v.toFixed(1)}h`,
      color: 'var(--text2)',
    },
    {
      label: 'W/L Ratio',
      value: summary.winning_signals / (summary.losing_signals || 1),
      format: (v: number) => v.toFixed(2),
      color: 'var(--text2)',
    },
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: 16,
    }}>
      {metrics.map((metric, idx) => (
        <div
          key={idx}
          style={{
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: 16,
          }}
        >
          <div style={{
            fontSize: 11,
            color: 'var(--text3)',
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 8,
          }}>
            {metric.label}
          </div>
          <div
            className="mono"
            style={{
              fontSize: 20,
              fontWeight: 700,
              color: metric.color,
            }}
          >
            {metric.format(metric.value)}
          </div>
        </div>
      ))}
    </div>
  );
}

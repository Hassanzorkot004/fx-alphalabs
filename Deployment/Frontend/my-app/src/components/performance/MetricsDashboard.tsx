interface MetricsDashboardProps {
  summary: {
    total_signals: number;
    directional_signals?: number;
    hold_signals?: number;
    buy_signals?: number;
    sell_signals?: number;
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
    avg_confidence?: number;
  };
}

export default function MetricsDashboard({ summary }: MetricsDashboardProps) {
  const hasTradeData = summary.total_pips !== 0 || summary.winning_signals > 0;
  const directional  = summary.directional_signals ?? (summary.winning_signals + summary.losing_signals);
  const holdCount    = summary.hold_signals ?? (summary.total_signals - directional);
  const holdPct      = summary.total_signals > 0 ? Math.round(holdCount / summary.total_signals * 100) : 0;
  const avgConf      = summary.avg_confidence ?? 0;

  // Signal breakdown row — always shown
  const breakdown = [
    {
      label: 'Total Signals',
      value: summary.total_signals.toString(),
      sub: null,
      color: 'var(--text)',
    },
    {
      label: 'BUY',
      value: (summary.buy_signals ?? 0).toString(),
      sub: summary.total_signals > 0 ? `${Math.round((summary.buy_signals ?? 0) / summary.total_signals * 100)}%` : '—',
      color: 'var(--green)',
    },
    {
      label: 'SELL',
      value: (summary.sell_signals ?? 0).toString(),
      sub: summary.total_signals > 0 ? `${Math.round((summary.sell_signals ?? 0) / summary.total_signals * 100)}%` : '—',
      color: 'var(--red)',
    },
    {
      label: 'HOLD',
      value: holdCount.toString(),
      sub: `${holdPct}% of signals`,
      color: 'var(--text3)',
    },
    {
      label: 'Avg Confidence',
      value: `${(avgConf * 100).toFixed(0)}%`,
      sub: avgConf >= 0.6 ? 'high' : avgConf >= 0.5 ? 'medium' : 'low',
      color: avgConf >= 0.6 ? 'var(--green)' : avgConf >= 0.5 ? 'var(--cyan)' : 'var(--text3)',
    },
  ];

  // Performance metrics — only meaningful when there are directional signals with trade data
  const perfMetrics = [
    {
      label: 'Win Rate',
      value: `${(summary.win_rate * 100).toFixed(1)}%`,
      color: summary.win_rate >= 0.5 ? 'var(--green)' : 'var(--red)',
    },
    {
      label: 'Total Pips',
      value: `${summary.total_pips >= 0 ? '+' : ''}${summary.total_pips.toFixed(1)}`,
      color: summary.total_pips >= 0 ? 'var(--green)' : 'var(--red)',
    },
    {
      label: 'Profit Factor',
      value: summary.profit_factor.toFixed(2),
      color: summary.profit_factor >= 1.5 ? 'var(--green)' : summary.profit_factor >= 1 ? 'var(--cyan)' : 'var(--red)',
    },
    {
      label: 'Avg Win',
      value: `+${summary.avg_win_pips.toFixed(1)} pips`,
      color: 'var(--green)',
    },
    {
      label: 'Avg Loss',
      value: `${summary.avg_loss_pips.toFixed(1)} pips`,
      color: 'var(--red)',
    },
    {
      label: 'Max Drawdown',
      value: `${summary.max_drawdown_pips.toFixed(1)} pips`,
      color: 'var(--red)',
    },
    {
      label: 'Sharpe Ratio',
      value: summary.sharpe_ratio.toFixed(2),
      color: summary.sharpe_ratio >= 1 ? 'var(--green)' : summary.sharpe_ratio >= 0 ? 'var(--cyan)' : 'var(--red)',
    },
    {
      label: 'Best Signal',
      value: `+${summary.best_signal_pips.toFixed(1)} pips`,
      color: 'var(--green)',
    },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

      {/* Signal breakdown — always visible */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: 12,
      }}>
        {breakdown.map((m, i) => (
          <div key={i} style={{
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '14px 16px',
          }}>
            <div style={{ fontSize: 10, color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
              {m.label}
            </div>
            <div className="mono" style={{ fontSize: 22, fontWeight: 700, color: m.color, marginBottom: 2 }}>
              {m.value}
            </div>
            {m.sub && (
              <div style={{ fontSize: 10, color: 'var(--text3)' }}>{m.sub}</div>
            )}
          </div>
        ))}
      </div>

      {/* Performance metrics — shown when trade data exists, otherwise placeholder */}
      {hasTradeData ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 12,
        }}>
          {perfMetrics.map((m, i) => (
            <div key={i} style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '14px 16px',
            }}>
              <div style={{ fontSize: 10, color: 'var(--text3)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
                {m.label}
              </div>
              <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: m.color }}>
                {m.value}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{
          background: 'var(--bg2)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '20px 24px',
          display: 'flex',
          alignItems: 'center',
          gap: 14,
          color: 'var(--text3)',
        }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, opacity: 0.5 }}>
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <div>
            <div style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 3 }}>
              P&amp;L metrics pending — no directional signals with trade levels yet
            </div>
            <div style={{ fontSize: 11, color: 'var(--text3)' }}>
              The system has generated {summary.total_signals} signal{summary.total_signals !== 1 ? 's' : ''} so far, all HOLD.
              Win rate, pips, and drawdown will appear once BUY/SELL signals fire with entry and stop levels.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

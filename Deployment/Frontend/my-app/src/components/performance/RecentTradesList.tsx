interface RecentTradesListProps {
  data: {
    signals: Array<{
      timestamp: string;
      pair: string;
      direction: string;
      entry: number;
      exit: number;
      pips: number;
      outcome: 'win' | 'loss';
      confidence: number;
    }>;
  };
}

export default function RecentTradesList({ data }: RecentTradesListProps) {
  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: 20,
        borderBottom: '1px solid var(--border)',
      }}>
        <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text2)' }}>
          Recent Signals (Simulated Outcomes)
        </h3>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
          Shows what would have happened if you followed these signals
        </div>
      </div>
      
      <div style={{ maxHeight: 400, overflowY: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead style={{ position: 'sticky', top: 0, background: 'var(--bg3)', zIndex: 1 }}>
            <tr style={{ borderBottom: '1px solid var(--border)' }}>
              <th style={thStyle}>Time</th>
              <th style={thStyle}>Pair</th>
              <th style={thStyle}>Direction</th>
              <th style={thStyle}>Entry</th>
              <th style={thStyle}>Exit</th>
              <th style={thStyle}>Pips</th>
              <th style={thStyle}>Confidence</th>
              <th style={thStyle}>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {data.signals.map((signal, idx) => (
              <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
                <td style={tdStyle} className="mono">
                  {new Date(signal.timestamp).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </td>
                <td style={tdStyle} className="mono">
                  {signal.pair}
                </td>
                <td 
                  style={{ 
                    ...tdStyle, 
                    color: signal.direction === 'BUY' ? 'var(--green)' : 'var(--red)',
                    fontWeight: 600,
                  }}
                >
                  {signal.direction}
                </td>
                <td style={tdStyle} className="mono">
                  {signal.entry.toFixed(5)}
                </td>
                <td style={tdStyle} className="mono">
                  {signal.exit.toFixed(5)}
                </td>
                <td 
                  style={{ 
                    ...tdStyle, 
                    color: signal.pips >= 0 ? 'var(--green)' : 'var(--red)',
                    fontWeight: 600,
                  }} 
                  className="mono"
                >
                  {signal.pips >= 0 ? '+' : ''}{signal.pips.toFixed(1)}
                </td>
                <td style={tdStyle} className="mono">
                  {(signal.confidence * 100).toFixed(0)}%
                </td>
                <td style={tdStyle}>
                  <span style={{
                    display: 'inline-block',
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 11,
                    fontWeight: 600,
                    background: signal.outcome === 'win' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    color: signal.outcome === 'win' ? 'var(--green)' : 'var(--red)',
                  }}>
                    {signal.outcome.toUpperCase()}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: '12px 16px',
  textAlign: 'left',
  fontSize: 11,
  fontWeight: 600,
  color: 'var(--text3)',
  textTransform: 'uppercase',
  letterSpacing: '0.05em',
};

const tdStyle: React.CSSProperties = {
  padding: '12px 16px',
  fontSize: 13,
};

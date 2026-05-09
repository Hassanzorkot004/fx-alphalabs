interface PairComparisonProps {
  data: {
    pairs: Array<{
      pair: string;
      total_signals: number;  // Backend sends 'total_signals'
      win_rate: number;
      total_pips: number;
      profit_factor: number;
      sharpe_ratio: number;
    }>;
  };
}

export default function PairComparison({ data }: PairComparisonProps) {
  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg3)',
      }}>
        <div className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Pair Comparison
        </div>
      </div>
      
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: 'var(--bg3)', borderBottom: '1px solid var(--border)' }}>
            <th style={thStyle}>Pair</th>
            <th style={thStyle}>Signals</th>
            <th style={thStyle}>Win Rate</th>
            <th style={thStyle}>Total Pips</th>
            <th style={thStyle}>Profit Factor</th>
            <th style={thStyle}>Sharpe</th>
          </tr>
        </thead>
        <tbody>
          {data.pairs.map((pair, idx) => (
            <tr key={idx} style={{ borderBottom: '1px solid var(--border)' }}>
              <td style={{ ...tdStyle, fontWeight: 600 }} className="mono">
                {pair.pair}
              </td>
              <td style={tdStyle} className="mono">
                {pair.total_signals}
              </td>
              <td 
                style={{ 
                  ...tdStyle, 
                  color: pair.win_rate >= 0.5 ? 'var(--green)' : 'var(--red)',
                  fontWeight: 600,
                }} 
                className="mono"
              >
                {(pair.win_rate * 100).toFixed(1)}%
              </td>
              <td 
                style={{ 
                  ...tdStyle, 
                  color: pair.total_pips >= 0 ? 'var(--green)' : 'var(--red)',
                  fontWeight: 600,
                }} 
                className="mono"
              >
                {pair.total_pips >= 0 ? '+' : ''}{pair.total_pips.toFixed(1)}
              </td>
              <td 
                style={{ 
                  ...tdStyle, 
                  color: pair.profit_factor >= 1.5 ? 'var(--green)' : pair.profit_factor >= 1 ? 'var(--cyan)' : 'var(--red)',
                }} 
                className="mono"
              >
                {pair.profit_factor.toFixed(2)}
              </td>
              <td 
                style={{ 
                  ...tdStyle, 
                  color: pair.sharpe_ratio >= 1 ? 'var(--green)' : pair.sharpe_ratio >= 0 ? 'var(--cyan)' : 'var(--red)',
                }} 
                className="mono"
              >
                {pair.sharpe_ratio.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
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

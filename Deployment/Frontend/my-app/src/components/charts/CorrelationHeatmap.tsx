interface CorrelationHeatmapProps {
  data: any;
}

export default function CorrelationHeatmap({ data: chartData }: CorrelationHeatmapProps) {
  const { pairs, matrix, timeframe, data_points } = chartData;

  if (!pairs || !matrix) {
    return (
      <div style={{
        background: 'var(--bg3)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 16,
        marginTop: 12,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 12, color: 'var(--text3)' }}>
          No correlation data available
        </div>
      </div>
    );
  }

  // Helper to get color based on correlation value
  const getCorrelationColor = (value: number): string => {
    if (value === 1) return 'var(--text3)'; // Diagonal (self-correlation)
    
    const absValue = Math.abs(value);
    
    if (value > 0) {
      // Positive correlation: green shades
      if (absValue > 0.8) return 'var(--green)';
      if (absValue > 0.6) return '#4ade80';
      if (absValue > 0.4) return '#86efac';
      if (absValue > 0.2) return '#bbf7d0';
      return '#dcfce7';
    } else {
      // Negative correlation: red shades
      if (absValue > 0.8) return 'var(--red)';
      if (absValue > 0.6) return '#f87171';
      if (absValue > 0.4) return '#fca5a5';
      if (absValue > 0.2) return '#fecaca';
      return '#fee2e2';
    }
  };

  const getCorrelationLabel = (value: number): string => {
    if (value === 1) return 'SELF';
    
    const absValue = Math.abs(value);
    
    if (absValue > 0.8) return 'VERY STRONG';
    if (absValue > 0.6) return 'STRONG';
    if (absValue > 0.4) return 'MODERATE';
    if (absValue > 0.2) return 'WEAK';
    return 'VERY WEAK';
  };

  const cellSize = 120;
  const labelWidth = 80;

  return (
    <div style={{
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      marginTop: 12,
    }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
              Correlation Matrix
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {timeframe} · {data_points} data points
            </span>
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
          Shows how pairs move together. High correlation = similar movements.
        </div>
      </div>

      {/* Heatmap Grid */}
      <div style={{ 
        overflowX: 'auto',
        overflowY: 'visible',
      }}>
        <div style={{ 
          display: 'inline-block',
          minWidth: 'fit-content',
        }}>
          {/* Column headers */}
          <div style={{ display: 'flex', marginBottom: 4 }}>
            <div style={{ width: labelWidth }} />
            {pairs.map((pair, idx) => (
              <div
                key={idx}
                className="mono"
                style={{
                  width: cellSize,
                  textAlign: 'center',
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--text2)',
                  padding: '4px 0',
                }}
              >
                {pair}
              </div>
            ))}
          </div>

          {/* Rows */}
          {pairs.map((rowPair, rowIdx) => (
            <div key={rowIdx} style={{ display: 'flex', marginBottom: 4 }}>
              {/* Row label */}
              <div
                className="mono"
                style={{
                  width: labelWidth,
                  display: 'flex',
                  alignItems: 'center',
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--text2)',
                  paddingRight: 8,
                  justifyContent: 'flex-end',
                }}
              >
                {rowPair}
              </div>

              {/* Cells */}
              {pairs.map((colPair, colIdx) => {
                const value = matrix[rowIdx][colIdx];
                const color = getCorrelationColor(value);
                const label = getCorrelationLabel(value);
                const isDiagonal = rowIdx === colIdx;

                return (
                  <div
                    key={colIdx}
                    style={{
                      width: cellSize,
                      height: cellSize,
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems: 'center',
                      justifyContent: 'center',
                      background: isDiagonal ? 'var(--bg4)' : color + '20',
                      border: `2px solid ${isDiagonal ? 'var(--border)' : color}`,
                      borderRadius: 6,
                      marginRight: 4,
                      cursor: isDiagonal ? 'default' : 'pointer',
                      transition: 'all 0.2s ease',
                      position: 'relative',
                    }}
                    className={!isDiagonal ? 'hover:scale-105' : ''}
                    title={`${rowPair} vs ${colPair}: ${value.toFixed(3)}`}
                  >
                    {/* Correlation value */}
                    <div
                      className="mono"
                      style={{
                        fontSize: 20,
                        fontWeight: 700,
                        color: isDiagonal ? 'var(--text3)' : color,
                        marginBottom: 4,
                      }}
                    >
                      {isDiagonal ? '—' : value.toFixed(2)}
                    </div>

                    {/* Label */}
                    {!isDiagonal && (
                      <div
                        style={{
                          fontSize: 9,
                          fontWeight: 600,
                          color: color,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                        }}
                      >
                        {label}
                      </div>
                    )}

                    {/* Direction indicator */}
                    {!isDiagonal && (
                      <div
                        style={{
                          fontSize: 16,
                          marginTop: 2,
                        }}
                      >
                        {value > 0 ? '↗' : '↙'}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Legend */}
      <div style={{
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text3)', marginBottom: 8 }}>
          INTERPRETATION
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, fontSize: 11 }}>
          <div>
            <span style={{ color: 'var(--green)', fontWeight: 600 }}>Positive (+1.0)</span>
            <span style={{ color: 'var(--text3)' }}> → Pairs move together</span>
          </div>
          <div>
            <span style={{ color: 'var(--red)', fontWeight: 600 }}>Negative (-1.0)</span>
            <span style={{ color: 'var(--text3)' }}> → Pairs move opposite</span>
          </div>
          <div>
            <span style={{ color: 'var(--text2)', fontWeight: 600 }}>Strong (&gt;0.7)</span>
            <span style={{ color: 'var(--text3)' }}> → High correlation risk</span>
          </div>
          <div>
            <span style={{ color: 'var(--text2)', fontWeight: 600 }}>Weak (&lt;0.3)</span>
            <span style={{ color: 'var(--text3)' }}> → Good diversification</span>
          </div>
        </div>
      </div>

      {/* Risk Warning */}
      {(() => {
        // Find highest correlation (excluding diagonal)
        let maxCorr = 0;
        let maxPair1 = '';
        let maxPair2 = '';
        
        for (let i = 0; i < pairs.length; i++) {
          for (let j = i + 1; j < pairs.length; j++) {
            const corr = Math.abs(matrix[i][j]);
            if (corr > maxCorr) {
              maxCorr = corr;
              maxPair1 = pairs[i];
              maxPair2 = pairs[j];
            }
          }
        }

        if (maxCorr > 0.7) {
          return (
            <div style={{
              marginTop: 12,
              padding: 12,
              background: 'var(--amber)10',
              border: '1px solid var(--amber)40',
              borderRadius: 6,
              fontSize: 12,
              color: 'var(--amber)',
            }}>
              ⚠️ <strong>High Correlation Warning:</strong> {maxPair1} and {maxPair2} are {(maxCorr * 100).toFixed(0)}% correlated.
              Taking positions in both increases risk without diversification.
            </div>
          );
        }
        return null;
      })()}
    </div>
  );
}

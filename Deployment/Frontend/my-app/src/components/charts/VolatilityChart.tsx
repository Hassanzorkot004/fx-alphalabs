import { Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, ComposedChart } from 'recharts';

interface VolatilityChartProps {
  data: any;
}

export default function VolatilityChart({ data: chartData }: VolatilityChartProps) {
  const { pair, timeframe, data, current_atr, avg_atr, volatility_state, z_score } = chartData;

  if (!data || data.length === 0) {
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
          No volatility data available
        </div>
      </div>
    );
  }

  // Format data for chart
  const formattedData = data.map((d: any) => ({
    time: new Date(d.time).toLocaleString('en-US', { 
      month: 'short', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }),
    atr: d.atr,
    avg: avg_atr,
  }));

  // Volatility state colors and labels
  const stateConfig: Record<string, { color: string; label: string; emoji: string }> = {
    low: { color: 'var(--green)', label: 'Low Volatility', emoji: '😴' },
    normal: { color: 'var(--blue)', label: 'Normal Volatility', emoji: '📊' },
    high: { color: 'var(--amber)', label: 'High Volatility', emoji: '⚡' },
    extreme: { color: 'var(--red)', label: 'Extreme Volatility', emoji: '🔥' },
  };

  const currentState = stateConfig[volatility_state] || stateConfig.normal;

  // Calculate percentage difference from average
  const pctDiff = ((current_atr - avg_atr) / avg_atr * 100).toFixed(1);
  const isAboveAvg = current_atr > avg_atr;

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
              {pair} Volatility (ATR 14)
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {timeframe}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              fontSize: 11,
              color: currentState.color,
              fontWeight: 600,
              padding: '4px 8px',
              background: currentState.color + '20',
              borderRadius: 4,
              border: `1px solid ${currentState.color}40`,
            }}>
              {currentState.emoji} {currentState.label}
            </span>
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
          Current ATR: <span className="mono" style={{ color: 'var(--text)', fontWeight: 600 }}>{(current_atr * 10000).toFixed(1)}</span> pips
          {' · '}
          <span style={{ color: isAboveAvg ? 'var(--red)' : 'var(--green)' }}>
            {isAboveAvg ? '+' : ''}{pctDiff}% vs avg
          </span>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={250}>
        <ComposedChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis 
            dataKey="time" 
            stroke="var(--text3)" 
            style={{ fontSize: 10 }}
            tick={{ fill: 'var(--text3)' }}
            angle={-45}
            textAnchor="end"
            height={80}
          />
          <YAxis 
            stroke="var(--text3)" 
            style={{ fontSize: 10 }}
            tick={{ fill: 'var(--text3)' }}
            tickFormatter={(value) => (value * 10000).toFixed(0)}
            label={{ value: 'ATR (pips)', angle: -90, position: 'insideLeft', style: { fill: 'var(--text3)', fontSize: 11 } }}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              fontSize: 11,
            }}
            labelStyle={{ color: 'var(--text3)', marginBottom: 8 }}
            formatter={(value: any, name: string) => {
              const pips = (value * 10000).toFixed(1);
              const labels: any = {
                atr: 'Current ATR',
                avg: 'Average ATR',
              };
              return [`${pips} pips`, labels[name] || name];
            }}
          />
          
          {/* Average ATR reference line */}
          <ReferenceLine
            y={avg_atr}
            stroke="var(--blue)"
            strokeDasharray="5 5"
            strokeOpacity={0.5}
            label={{ 
              value: 'Average', 
              position: 'right', 
              fill: 'var(--blue)', 
              fontSize: 10 
            }}
          />
          
          {/* Area under ATR line */}
          <defs>
            <linearGradient id="atrGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={currentState.color} stopOpacity={0.3} />
              <stop offset="100%" stopColor={currentState.color} stopOpacity={0.05} />
            </linearGradient>
          </defs>
          
          <Area
            type="monotone"
            dataKey="atr"
            fill="url(#atrGradient)"
            stroke="none"
          />
          
          {/* ATR line */}
          <Line
            type="monotone"
            dataKey="atr"
            stroke={currentState.color}
            strokeWidth={3}
            dot={{ fill: currentState.color, r: 3 }}
            name="atr"
          />
          
          {/* Average line */}
          <Line
            type="monotone"
            dataKey="avg"
            stroke="var(--blue)"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={false}
            name="avg"
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Stats Grid */}
      <div style={{
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid var(--border)',
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 12,
      }}>
        <StatCard
          label="Current ATR"
          value={`${(current_atr * 10000).toFixed(1)} pips`}
          color={currentState.color}
        />
        <StatCard
          label="Average ATR"
          value={`${(avg_atr * 10000).toFixed(1)} pips`}
          color="var(--blue)"
        />
        <StatCard
          label="Z-Score"
          value={z_score.toFixed(2)}
          color={Math.abs(z_score) > 1.5 ? 'var(--red)' : 'var(--text2)'}
        />
      </div>

      {/* Interpretation */}
      <div style={{
        marginTop: 16,
        padding: 12,
        background: 'var(--bg4)',
        borderRadius: 6,
        fontSize: 11,
      }}>
        <div style={{ fontWeight: 600, color: 'var(--text2)', marginBottom: 6 }}>
          TRADING IMPLICATIONS
        </div>
        <div style={{ color: 'var(--text3)', lineHeight: 1.6 }}>
          {volatility_state === 'low' && (
            <>
              <strong style={{ color: 'var(--green)' }}>Low volatility</strong> - Market is calm. 
              Consider larger position sizes, but watch for potential breakout.
            </>
          )}
          {volatility_state === 'normal' && (
            <>
              <strong style={{ color: 'var(--blue)' }}>Normal volatility</strong> - Standard market conditions. 
              Use regular position sizing.
            </>
          )}
          {volatility_state === 'high' && (
            <>
              <strong style={{ color: 'var(--amber)' }}>High volatility</strong> - Market is active. 
              Reduce position sizes by 30-50% to manage risk.
            </>
          )}
          {volatility_state === 'extreme' && (
            <>
              <strong style={{ color: 'var(--red)' }}>Extreme volatility</strong> - Market is very volatile. 
              Reduce position sizes by 50-70% or avoid trading until conditions normalize.
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{
      background: 'var(--bg4)',
      padding: 12,
      borderRadius: 4,
      textAlign: 'center',
    }}>
      <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 4 }}>
        {label}
      </div>
      <div className="mono" style={{ fontSize: 14, fontWeight: 600, color }}>
        {value}
      </div>
    </div>
  );
}

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface RSIChartProps {
  data: any;
}

export default function RSIChart({ data: chartData }: RSIChartProps) {
  const { data, pair, timeframe, levels, current_value } = chartData;

  // Format data for display
  const formattedData = data.map((d: any) => ({
    time: new Date(d.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    rsi: d.rsi,
  }));

  // Determine RSI status
  const getRSIStatus = (rsi: number) => {
    if (rsi > 70) return { label: 'Overbought', color: 'var(--red)' };
    if (rsi < 30) return { label: 'Oversold', color: 'var(--green)' };
    return { label: 'Neutral', color: 'var(--text3)' };
  };

  const currentStatus = current_value ? getRSIStatus(current_value) : null;

  return (
    <div style={{
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      marginTop: 12,
    }}>
      {/* Header */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span className="mono" style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
              {pair} RSI (14)
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {timeframe}
            </span>
          </div>
          {current_value && currentStatus && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="mono" style={{ fontSize: 16, fontWeight: 600, color: currentStatus.color }}>
                {current_value.toFixed(1)}
              </span>
              <span style={{
                fontSize: 10,
                color: currentStatus.color,
                padding: '4px 8px',
                background: currentStatus.color + '20',
                borderRadius: 4,
                fontWeight: 600,
              }}>
                {currentStatus.label}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis 
            dataKey="time" 
            stroke="var(--text3)" 
            style={{ fontSize: 10 }}
            tick={{ fill: 'var(--text3)' }}
          />
          <YAxis 
            stroke="var(--text3)" 
            style={{ fontSize: 10 }}
            tick={{ fill: 'var(--text3)' }}
            domain={[0, 100]}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              fontSize: 11,
            }}
            labelStyle={{ color: 'var(--text3)' }}
          />
          
          {/* Overbought line */}
          <ReferenceLine
            y={levels.overbought}
            stroke="var(--red)"
            strokeDasharray="3 3"
            strokeOpacity={0.5}
          />
          
          {/* Oversold line */}
          <ReferenceLine
            y={levels.oversold}
            stroke="var(--green)"
            strokeDasharray="3 3"
            strokeOpacity={0.5}
          />
          
          {/* Midline */}
          <ReferenceLine
            y={50}
            stroke="var(--text3)"
            strokeDasharray="1 1"
            strokeOpacity={0.3}
          />
          
          {/* RSI line */}
          <Line
            type="monotone"
            dataKey="rsi"
            stroke="var(--amber)"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div style={{
        display: 'flex',
        gap: 16,
        marginTop: 12,
        fontSize: 10,
        color: 'var(--text3)',
        justifyContent: 'center',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: 'var(--red)', opacity: 0.5 }} />
          <span>Overbought (70)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: 'var(--green)', opacity: 0.5 }} />
          <span>Oversold (30)</span>
        </div>
      </div>
    </div>
  );
}

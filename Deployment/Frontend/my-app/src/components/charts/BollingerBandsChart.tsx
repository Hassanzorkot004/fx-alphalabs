import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, ComposedChart } from 'recharts';

interface BollingerBandsChartProps {
  data: any;
}

export default function BollingerBandsChart({ data: chartData }: BollingerBandsChartProps) {
  const { data, pair, timeframe } = chartData;

  // Format data for display
  const formattedData = data.map((d: any) => ({
    time: new Date(d.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    price: d.price,
    upper: d.upper,
    middle: d.middle,
    lower: d.lower,
  }));

  // Get current values (last data point)
  const current = data[data.length - 1];
  
  // Calculate BB position (0 = lower band, 0.5 = middle, 1 = upper band)
  const bbPosition = current ? 
    (current.price - current.lower) / (current.upper - current.lower) : 0.5;
  
  const getPositionStatus = (pos: number) => {
    if (pos > 0.8) return { label: 'Near Upper', color: 'var(--red)' };
    if (pos < 0.2) return { label: 'Near Lower', color: 'var(--green)' };
    return { label: 'Middle Range', color: 'var(--text3)' };
  };

  const status = getPositionStatus(bbPosition);

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
              {pair} Bollinger Bands (20, 2)
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {timeframe}
            </span>
          </div>
          {current && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ textAlign: 'right' }}>
                <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
                  Position
                </div>
                <div className="mono" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
                  {(bbPosition * 100).toFixed(0)}%
                </div>
              </div>
              <span style={{
                fontSize: 10,
                color: status.color,
                padding: '4px 8px',
                background: status.color + '20',
                borderRadius: 4,
                fontWeight: 600,
              }}>
                {status.label}
              </span>
            </div>
          )}
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
          />
          <YAxis 
            stroke="var(--text3)" 
            style={{ fontSize: 10 }}
            tick={{ fill: 'var(--text3)' }}
            domain={['auto', 'auto']}
            tickFormatter={(value) => value.toFixed(5)}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              fontSize: 11,
            }}
            labelStyle={{ color: 'var(--text3)' }}
            formatter={(value: any) => value.toFixed(5)}
          />
          
          {/* Shaded area between bands */}
          <defs>
            <linearGradient id="bbGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--blue)" stopOpacity={0.1} />
              <stop offset="100%" stopColor="var(--blue)" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          
          {/* Upper band */}
          <Line
            type="monotone"
            dataKey="upper"
            stroke="var(--red)"
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={false}
            name="Upper Band"
          />
          
          {/* Middle band (SMA) */}
          <Line
            type="monotone"
            dataKey="middle"
            stroke="var(--blue)"
            strokeWidth={2}
            dot={false}
            name="Middle (SMA)"
          />
          
          {/* Lower band */}
          <Line
            type="monotone"
            dataKey="lower"
            stroke="var(--green)"
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={false}
            name="Lower Band"
          />
          
          {/* Price line */}
          <Line
            type="monotone"
            dataKey="price"
            stroke="var(--amber)"
            strokeWidth={2.5}
            dot={false}
            name="Price"
          />
        </ComposedChart>
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
          <div style={{ width: 12, height: 2, background: 'var(--amber)' }} />
          <span>Price</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: 'var(--blue)' }} />
          <span>Middle (SMA 20)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: 'var(--red)', opacity: 0.6 }} />
          <span>Upper Band (+2σ)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: 'var(--green)', opacity: 0.6 }} />
          <span>Lower Band (-2σ)</span>
        </div>
      </div>

      {/* Current Values */}
      {current && (
        <div style={{
          marginTop: 12,
          padding: 12,
          background: 'var(--bg4)',
          borderRadius: 4,
          display: 'grid',
          gridTemplateColumns: 'repeat(2, 1fr)',
          gap: 8,
          fontSize: 10,
        }}>
          <div>
            <span style={{ color: 'var(--text3)' }}>Price: </span>
            <span className="mono" style={{ color: 'var(--amber)', fontWeight: 600 }}>
              {current.price.toFixed(5)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Middle: </span>
            <span className="mono" style={{ color: 'var(--blue)', fontWeight: 500 }}>
              {current.middle.toFixed(5)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Upper: </span>
            <span className="mono" style={{ color: 'var(--red)', fontWeight: 500 }}>
              {current.upper.toFixed(5)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Lower: </span>
            <span className="mono" style={{ color: 'var(--green)', fontWeight: 500 }}>
              {current.lower.toFixed(5)}
            </span>
          </div>
          <div style={{ gridColumn: '1 / -1' }}>
            <span style={{ color: 'var(--text3)' }}>Bandwidth: </span>
            <span className="mono" style={{ color: 'var(--text)', fontWeight: 500 }}>
              {((current.upper - current.lower) / current.middle * 100).toFixed(2)}%
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

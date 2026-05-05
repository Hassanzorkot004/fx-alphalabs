import { Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Bar, ComposedChart } from 'recharts';

interface MACDChartProps {
  data: any;
}

export default function MACDChart({ data: chartData }: MACDChartProps) {
  const { data, pair, timeframe } = chartData;

  // Format data for display
  const formattedData = data.map((d: any) => ({
    time: new Date(d.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    macd: d.macd,
    signal: d.signal,
    histogram: d.histogram,
  }));

  // Get current values (last data point)
  const current = data[data.length - 1];
  const isBullish = current?.histogram > 0;

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
              {pair} MACD (12, 26, 9)
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {timeframe}
            </span>
          </div>
          {current && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ textAlign: 'right' }}>
                <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
                  Histogram
                </div>
                <div className="mono" style={{ 
                  fontSize: 14, 
                  fontWeight: 600, 
                  color: isBullish ? 'var(--green)' : 'var(--red)' 
                }}>
                  {current.histogram.toFixed(6)}
                </div>
              </div>
              <span style={{
                fontSize: 10,
                color: isBullish ? 'var(--green)' : 'var(--red)',
                padding: '4px 8px',
                background: (isBullish ? 'var(--green)' : 'var(--red)') + '20',
                borderRadius: 4,
                fontWeight: 600,
              }}>
                {isBullish ? 'BULLISH' : 'BEARISH'}
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
            tickFormatter={(value) => value.toFixed(4)}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              fontSize: 11,
            }}
            labelStyle={{ color: 'var(--text3)' }}
            formatter={(value: any) => value.toFixed(6)}
          />
          
          {/* Zero line */}
          <ReferenceLine
            y={0}
            stroke="var(--text3)"
            strokeDasharray="3 3"
            strokeOpacity={0.5}
          />
          
          {/* Histogram bars */}
          <Bar 
            dataKey="histogram" 
            fill="var(--amber)"
            opacity={0.6}
          />
          
          {/* MACD line */}
          <Line
            type="monotone"
            dataKey="macd"
            stroke="var(--blue)"
            strokeWidth={2}
            dot={false}
            name="MACD"
          />
          
          {/* Signal line */}
          <Line
            type="monotone"
            dataKey="signal"
            stroke="var(--red)"
            strokeWidth={2}
            dot={false}
            name="Signal"
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
          <div style={{ width: 12, height: 2, background: 'var(--blue)' }} />
          <span>MACD Line</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 2, background: 'var(--red)' }} />
          <span>Signal Line</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <div style={{ width: 12, height: 8, background: 'var(--amber)', opacity: 0.6 }} />
          <span>Histogram</span>
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
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 8,
          fontSize: 10,
        }}>
          <div>
            <span style={{ color: 'var(--text3)' }}>MACD: </span>
            <span className="mono" style={{ color: 'var(--blue)', fontWeight: 500 }}>
              {current.macd.toFixed(6)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Signal: </span>
            <span className="mono" style={{ color: 'var(--red)', fontWeight: 500 }}>
              {current.signal.toFixed(6)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Histogram: </span>
            <span className="mono" style={{ 
              color: isBullish ? 'var(--green)' : 'var(--red)', 
              fontWeight: 500 
            }}>
              {current.histogram.toFixed(6)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

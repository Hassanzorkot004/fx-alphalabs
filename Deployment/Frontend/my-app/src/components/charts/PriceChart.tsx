import { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Area, ComposedChart } from 'recharts';

interface PriceChartProps {
  data: any;
}

export default function PriceChart({ data }: PriceChartProps) {
  const { candles, signal_levels, pair, timeframe } = data;

  // Format data for recharts
  const chartData = useMemo(() => {
    return candles.map((candle: any) => ({
      time: new Date(candle.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      close: candle.close,
      high: candle.high,
      low: candle.low,
    }));
  }, [candles]);

  const directionColor = signal_levels?.direction === 'BUY' ? 'var(--green)' : 
                        signal_levels?.direction === 'SELL' ? 'var(--red)' : 'var(--text3)';

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
              {pair} Price Chart
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {timeframe}
            </span>
          </div>
          {signal_levels && (
            <div style={{
              fontSize: 10,
              color: directionColor,
              fontWeight: 600,
              padding: '4px 8px',
              background: directionColor + '20',
              borderRadius: 4,
            }}>
              {signal_levels.direction}
            </div>
          )}
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={chartData}>
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
          
          {/* High-Low range */}
          <Area
            type="monotone"
            dataKey="high"
            stroke="none"
            fill="var(--text3)"
            fillOpacity={0.1}
          />
          <Area
            type="monotone"
            dataKey="low"
            stroke="none"
            fill="var(--text3)"
            fillOpacity={0.1}
          />
          
          {/* Close price line */}
          <Line
            type="monotone"
            dataKey="close"
            stroke="var(--amber)"
            strokeWidth={2}
            dot={false}
          />

          {/* Signal levels */}
          {signal_levels?.entry_low && (
            <ReferenceLine
              y={signal_levels.entry_low}
              stroke="var(--green)"
              strokeDasharray="3 3"
              label={{ value: 'Entry', position: 'right', fill: 'var(--green)', fontSize: 10 }}
            />
          )}
          {signal_levels?.stop && (
            <ReferenceLine
              y={signal_levels.stop}
              stroke="var(--red)"
              strokeDasharray="3 3"
              label={{ value: 'Stop', position: 'right', fill: 'var(--red)', fontSize: 10 }}
            />
          )}
          {signal_levels?.target && (
            <ReferenceLine
              y={signal_levels.target}
              stroke="var(--green)"
              strokeDasharray="5 5"
              strokeWidth={2}
              label={{ value: 'Target', position: 'right', fill: 'var(--green)', fontSize: 10 }}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      {signal_levels && (
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
          {signal_levels.entry_low && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 12, height: 2, background: 'var(--green)', opacity: 0.6 }} />
              <span>Entry</span>
            </div>
          )}
          {signal_levels.stop && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 12, height: 2, background: 'var(--red)', opacity: 0.6 }} />
              <span>Stop</span>
            </div>
          )}
          {signal_levels.target && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <div style={{ width: 12, height: 2, background: 'var(--green)' }} />
              <span>Target</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

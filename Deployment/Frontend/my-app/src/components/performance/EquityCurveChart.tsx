import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface EquityCurveChartProps {
  data: {
    data: Array<{
      time: string;
      cumulative_pips: number;
      signal_pips: number;  // Backend sends 'signal_pips'
      pair: string;
      direction: string;
    }>;
  };
}

export default function EquityCurveChart({ data }: EquityCurveChartProps) {
  // Safety check for data
  if (!data || !data.data || !Array.isArray(data.data)) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: 'var(--text3)' }}>
        No equity curve data available
      </div>
    );
  }

  const chartData = data.data.map(point => ({
    time: new Date(point.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    pips: point.cumulative_pips,
    trade: point.signal_pips,  // Backend sends 'signal_pips', not 'trade_pips'
    pair: point.pair.replace('=X', ''),
    direction: point.direction,
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || !payload[0]) return null;

    const data = payload[0].payload;
    return (
      <div style={{
        background: 'var(--bg3)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: 12,
        fontSize: 12,
      }}>
        <div style={{ color: 'var(--text3)', marginBottom: 6 }}>{data.time}</div>
        <div style={{ color: 'var(--cyan)', fontWeight: 600, marginBottom: 4 }}>
          Cumulative: {data.pips >= 0 ? '+' : ''}{data.pips.toFixed(1)} pips
        </div>
        {data.trade !== undefined && data.trade !== null && (
          <div style={{ color: data.trade >= 0 ? 'var(--green)' : 'var(--red)', fontSize: 11 }}>
            Trade: {data.trade >= 0 ? '+' : ''}{data.trade.toFixed(1)} pips ({data.direction})
          </div>
        )}
        {data.pair && (
          <div style={{ color: 'var(--text3)', fontSize: 11, marginTop: 4 }}>
            {data.pair}
          </div>
        )}
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis 
          dataKey="time" 
          stroke="var(--text3)" 
          style={{ fontSize: 11 }}
          tick={{ fill: 'var(--text3)' }}
        />
        <YAxis 
          stroke="var(--text3)" 
          style={{ fontSize: 11 }}
          tick={{ fill: 'var(--text3)' }}
          label={{ value: 'Pips', angle: -90, position: 'insideLeft', fill: 'var(--text3)', fontSize: 11 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="var(--text3)" strokeDasharray="3 3" />
        <Line 
          type="monotone" 
          dataKey="pips" 
          stroke="var(--cyan)" 
          strokeWidth={2}
          dot={{ fill: 'var(--cyan)', r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

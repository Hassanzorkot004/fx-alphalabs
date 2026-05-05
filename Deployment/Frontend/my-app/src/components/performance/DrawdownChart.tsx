import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

interface DrawdownChartProps {
  data: {
    data: Array<{
      time: string;
      drawdown_pips: number;
      drawdown_pct: number;
    }>;
  };
}

export default function DrawdownChart({ data }: DrawdownChartProps) {
  // Safety check for data
  if (!data || !data.data || !Array.isArray(data.data)) {
    return (
      <div style={{ padding: 20, textAlign: 'center', color: 'var(--text3)' }}>
        No drawdown data available
      </div>
    );
  }

  const chartData = data.data.map(point => ({
    time: new Date(point.time).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    pips: point.drawdown_pips,
    pct: point.drawdown_pct,
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
        <div style={{ color: 'var(--red)', fontWeight: 600 }}>
          {data.pips.toFixed(1)} pips ({data.pct.toFixed(1)}%)
        </div>
      </div>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={chartData} margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
        <defs>
          <linearGradient id="drawdownGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="var(--red)" stopOpacity={0.3} />
            <stop offset="95%" stopColor="var(--red)" stopOpacity={0.05} />
          </linearGradient>
        </defs>
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
          label={{ value: 'Drawdown (pips)', angle: -90, position: 'insideLeft', fill: 'var(--text3)', fontSize: 11 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="var(--text3)" strokeDasharray="3 3" />
        <Area 
          type="monotone" 
          dataKey="pips" 
          stroke="var(--red)" 
          strokeWidth={2}
          fill="url(#drawdownGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

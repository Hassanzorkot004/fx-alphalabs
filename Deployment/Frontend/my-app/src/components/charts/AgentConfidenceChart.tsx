import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine } from 'recharts';

interface AgentConfidenceChartProps {
  data: any;
}

export default function AgentConfidenceChart({ data: chartData }: AgentConfidenceChartProps) {
  const { pair, data, count } = chartData;

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
          No agent confidence history available
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
    overall: (d.overall_confidence * 100).toFixed(1),
    macro: (d.macro_conf * 100).toFixed(1),
    technical: (d.tech_conf * 100).toFixed(1),
    sentiment: (d.sent_conf * 100).toFixed(1),
    direction: d.direction,
    agreement: d.agreement,
    // Store raw values for tooltip
    raw: d,
  }));

  // Get current (latest) values
  const current = data[data.length - 1];
  const currentOverall = (current.overall_confidence * 100).toFixed(0);
  const direction = current.direction;
  const agreement = current.agreement;

  const directionColor = direction === 'BUY' ? 'var(--green)' : direction === 'SELL' ? 'var(--red)' : 'var(--text3)';

  // Calculate trend (comparing first and last)
  const firstOverall = data[0].overall_confidence * 100;
  const lastOverall = current.overall_confidence * 100;
  const trend = lastOverall - firstOverall;
  const trendLabel = trend > 5 ? '📈 Strengthening' : trend < -5 ? '📉 Weakening' : '➡️ Stable';

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
              {pair} Confidence Evolution
            </span>
            <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 8 }}>
              {count} signals
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              fontSize: 11,
              color: directionColor,
              fontWeight: 600,
              padding: '4px 8px',
              background: directionColor + '20',
              borderRadius: 4,
              border: `1px solid ${directionColor}40`,
            }}>
              {direction}
            </span>
            <span className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
              {currentOverall}%
            </span>
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
          {trendLabel} · Agreement: {agreement}
        </div>
      </div>

      {/* Confidence Over Time Chart */}
      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={formattedData}>
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
            domain={[0, 100]}
            label={{ value: 'Confidence %', angle: -90, position: 'insideLeft', style: { fill: 'var(--text3)', fontSize: 11 } }}
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
              const labels: any = {
                overall: 'Overall',
                macro: 'Macro',
                technical: 'Technical',
                sentiment: 'Sentiment',
              };
              return [`${value}%`, labels[name] || name];
            }}
          />
          <Legend 
            wrapperStyle={{ fontSize: 11 }}
            iconType="line"
          />
          
          {/* Reference line at 50% */}
          <ReferenceLine
            y={50}
            stroke="var(--text3)"
            strokeDasharray="3 3"
            strokeOpacity={0.3}
          />
          
          {/* Reference line at 70% (high confidence) */}
          <ReferenceLine
            y={70}
            stroke="var(--green)"
            strokeDasharray="3 3"
            strokeOpacity={0.3}
            label={{ value: 'High Confidence', position: 'right', fill: 'var(--green)', fontSize: 10 }}
          />
          
          {/* Overall confidence line */}
          <Line
            type="monotone"
            dataKey="overall"
            stroke="var(--amber)"
            strokeWidth={3}
            dot={{ fill: 'var(--amber)', r: 4 }}
            name="Overall"
          />
          
          {/* Macro confidence line */}
          <Line
            type="monotone"
            dataKey="macro"
            stroke="var(--blue)"
            strokeWidth={2}
            dot={{ fill: 'var(--blue)', r: 3 }}
            name="Macro"
          />
          
          {/* Technical confidence line */}
          <Line
            type="monotone"
            dataKey="technical"
            stroke="var(--green)"
            strokeWidth={2}
            dot={{ fill: 'var(--green)', r: 3 }}
            name="Technical"
          />
          
          {/* Sentiment confidence line */}
          <Line
            type="monotone"
            dataKey="sentiment"
            stroke="var(--red)"
            strokeWidth={2}
            dot={{ fill: 'var(--red)', r: 3 }}
            name="Sentiment"
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Current Agent Breakdown */}
      <div style={{
        marginTop: 16,
        paddingTop: 16,
        borderTop: '1px solid var(--border)',
      }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text3)', marginBottom: 12 }}>
          CURRENT AGENT SIGNALS
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          <AgentCard
            name="Macro"
            signal={current.macro_regime}
            confidence={(current.macro_conf * 100).toFixed(0)}
            color="var(--blue)"
          />
          <AgentCard
            name="Technical"
            signal={current.tech_signal}
            confidence={(current.tech_conf * 100).toFixed(0)}
            color="var(--green)"
          />
          <AgentCard
            name="Sentiment"
            signal={current.sent_signal}
            confidence={(current.sent_conf * 100).toFixed(0)}
            color="var(--red)"
          />
        </div>
      </div>

      {/* Trend Analysis */}
      {Math.abs(trend) > 5 && (
        <div style={{
          marginTop: 12,
          padding: 12,
          background: trend > 0 ? 'var(--green)10' : 'var(--red)10',
          border: `1px solid ${trend > 0 ? 'var(--green)40' : 'var(--red)40'}`,
          borderRadius: 6,
          fontSize: 12,
          color: trend > 0 ? 'var(--green)' : 'var(--red)',
        }}>
          {trend > 0 ? '📈' : '📉'} <strong>Confidence {trend > 0 ? 'increased' : 'decreased'} by {Math.abs(trend).toFixed(1)}%</strong> over the last {count} signals.
          {trend > 0 ? ' Signal is strengthening.' : ' Signal is weakening - review recommended.'}
        </div>
      )}
    </div>
  );
}

function AgentCard({ name, signal, confidence, color }: {
  name: string;
  signal: string;
  confidence: string;
  color: string;
}) {
  return (
    <div style={{
      background: 'var(--bg4)',
      padding: 12,
      borderRadius: 4,
      border: `1px solid ${color}40`,
    }}>
      <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 4, fontWeight: 600 }}>
        {name}
      </div>
      <div style={{ fontSize: 13, fontWeight: 600, color, marginBottom: 2 }}>
        {signal}
      </div>
      <div className="mono" style={{ fontSize: 11, color: 'var(--text2)' }}>
        {confidence}% conf
      </div>
    </div>
  );
}

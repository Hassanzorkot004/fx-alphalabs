import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

interface AgentConfidenceChartProps {
  data: any;
}

export default function AgentConfidenceChart({ data: chartData }: AgentConfidenceChartProps) {
  const { pair, data } = chartData;

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
          No agent data available
        </div>
      </div>
    );
  }

  const currentData = data[0]; // Currently only showing latest signal

  // Prepare data for bar chart - showing agent probabilities
  const macroData = [
    { name: 'Bull', value: (currentData.macro.bull_prob * 100), color: 'var(--green)' },
    { name: 'Neutral', value: (currentData.macro.neut_prob * 100), color: 'var(--text3)' },
    { name: 'Bear', value: (currentData.macro.bear_prob * 100), color: 'var(--red)' },
  ];

  const technicalData = [
    { name: 'Buy', value: (currentData.technical.p_buy * 100), color: 'var(--green)' },
    { name: 'Hold', value: (currentData.technical.p_hold * 100), color: 'var(--text3)' },
    { name: 'Sell', value: (currentData.technical.p_sell * 100), color: 'var(--red)' },
  ];

  const sentimentData = [
    { name: 'Bullish', value: (currentData.sentiment.p_bullish * 100), color: 'var(--green)' },
    { name: 'Bearish', value: ((1 - currentData.sentiment.p_bullish) * 100), color: 'var(--red)' },
  ];

  // Overall confidence
  const overallConfidence = (currentData.overall.confidence * 100).toFixed(0);
  const agreement = currentData.overall.agreement || 'N/A';
  const direction = currentData.overall.direction;

  const directionColor = direction === 'BUY' ? 'var(--green)' : direction === 'SELL' ? 'var(--red)' : 'var(--text3)';

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
              {pair} Agent Analysis
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
            <span className="mono" style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>
              {overallConfidence}%
            </span>
          </div>
        </div>
      </div>

      {/* Agent Breakdown */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16 }}>
        
        {/* Macro Agent */}
        <AgentSection
          title="Macro Agent"
          subtitle={`Regime: ${currentData.macro.regime}`}
          data={macroData}
        />

        {/* Technical Agent */}
        <AgentSection
          title="Technical Agent"
          subtitle={`Signal: ${currentData.technical.signal} (conf: ${(currentData.technical.confidence * 100).toFixed(0)}%)`}
          data={technicalData}
        />

        {/* Sentiment Agent */}
        <AgentSection
          title="Sentiment Agent"
          subtitle={`Signal: ${currentData.sentiment.signal} (${currentData.sentiment.n_articles} articles)`}
          data={sentimentData}
        />
      </div>

      {/* Agreement Indicator */}
      <div style={{
        marginTop: 16,
        padding: 12,
        background: 'var(--bg4)',
        borderRadius: 4,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 10, color: 'var(--text3)', marginBottom: 4 }}>
          Agent Agreement
        </div>
        <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
          {agreement}
        </div>
      </div>
    </div>
  );
}

function AgentSection({ title, subtitle, data }: { title: string; subtitle: string; data: any[] }) {
  return (
    <div style={{
      background: 'var(--bg4)',
      padding: 12,
      borderRadius: 4,
    }}>
      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text)' }}>
          {title}
        </div>
        <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>
          {subtitle}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={80}>
        <BarChart data={data} layout="vertical">
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis 
            type="number" 
            stroke="var(--text3)" 
            style={{ fontSize: 9 }}
            tick={{ fill: 'var(--text3)' }}
            domain={[0, 100]}
          />
          <YAxis 
            type="category" 
            dataKey="name" 
            stroke="var(--text3)" 
            style={{ fontSize: 9 }}
            tick={{ fill: 'var(--text3)' }}
            width={50}
          />
          <Tooltip
            contentStyle={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 4,
              fontSize: 10,
            }}
            labelStyle={{ color: 'var(--text3)' }}
            formatter={(value: any) => `${value.toFixed(1)}%`}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]}>
            {data.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

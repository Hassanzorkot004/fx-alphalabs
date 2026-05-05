interface RiskChartProps {
  data: any;
}

export default function RiskChart({ data }: RiskChartProps) {
  const {
    pair,
    current_price,
    entry_low,
    entry_high,
    stop_loss,
    take_profit,
    risk_pips,
    reward_pips,
    rr_ratio,
    position_size,
    risk_level,
  } = data;

  const riskLevelColor = risk_level === 'LOW' ? 'var(--green)' :
                         risk_level === 'MEDIUM' ? 'var(--amber)' : 'var(--red)';

  // Calculate visual positions (normalized to 0-100 scale)
  const prices = [stop_loss, entry_low, entry_high, current_price, take_profit].filter(Boolean);
  const minPrice = Math.min(...prices);
  const maxPrice = Math.max(...prices);
  const range = maxPrice - minPrice;

  const getPosition = (price: number) => {
    if (!price || range === 0) return 50;
    return ((price - minPrice) / range) * 100;
  };

  const stopPos = getPosition(stop_loss);
  const entryLowPos = getPosition(entry_low);
  const entryHighPos = getPosition(entry_high);
  const currentPos = getPosition(current_price);
  const targetPos = getPosition(take_profit);

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
              {pair} Risk Analysis
            </span>
          </div>
          <div style={{
            fontSize: 10,
            color: riskLevelColor,
            fontWeight: 600,
            padding: '4px 8px',
            background: riskLevelColor + '20',
            borderRadius: 4,
            border: `1px solid ${riskLevelColor}40`,
          }}>
            {risk_level} RISK
          </div>
        </div>
      </div>

      {/* Visual Risk/Reward Bar */}
      <div style={{ marginBottom: 20 }}>
        <div style={{
          position: 'relative',
          height: 60,
          background: 'var(--bg4)',
          borderRadius: 4,
          overflow: 'hidden',
        }}>
          {/* Risk zone (stop to entry) */}
          <div style={{
            position: 'absolute',
            left: `${Math.min(stopPos, entryLowPos)}%`,
            width: `${Math.abs(entryLowPos - stopPos)}%`,
            height: '100%',
            background: 'var(--red)20',
            borderLeft: '2px solid var(--red)',
            borderRight: '2px solid var(--green)',
          }} />

          {/* Reward zone (entry to target) */}
          <div style={{
            position: 'absolute',
            left: `${Math.min(entryHighPos, targetPos)}%`,
            width: `${Math.abs(targetPos - entryHighPos)}%`,
            height: '100%',
            background: 'var(--green)20',
            borderLeft: '2px solid var(--green)',
            borderRight: '2px solid var(--green)',
          }} />

          {/* Current price marker */}
          <div style={{
            position: 'absolute',
            left: `${currentPos}%`,
            top: 0,
            bottom: 0,
            width: 2,
            background: 'var(--amber)',
            boxShadow: '0 0 8px var(--amber)',
          }}>
            <div style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              background: 'var(--amber)',
              color: 'var(--bg)',
              padding: '2px 6px',
              borderRadius: 3,
              fontSize: 9,
              fontWeight: 600,
              whiteSpace: 'nowrap',
            }}>
              NOW
            </div>
          </div>

          {/* Stop loss label */}
          <div style={{
            position: 'absolute',
            left: `${stopPos}%`,
            bottom: -20,
            transform: 'translateX(-50%)',
            fontSize: 9,
            color: 'var(--red)',
            fontWeight: 600,
          }}>
            STOP
          </div>

          {/* Target label */}
          <div style={{
            position: 'absolute',
            left: `${targetPos}%`,
            bottom: -20,
            transform: 'translateX(-50%)',
            fontSize: 9,
            color: 'var(--green)',
            fontWeight: 600,
          }}>
            TARGET
          </div>
        </div>
      </div>

      {/* Metrics Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gap: 12,
        marginTop: 32,
      }}>
        <MetricCard
          label="Risk/Reward"
          value={`1:${rr_ratio.toFixed(2)}`}
          color={rr_ratio >= 2 ? 'var(--green)' : rr_ratio >= 1.5 ? 'var(--amber)' : 'var(--red)'}
        />
        <MetricCard
          label="Position Size"
          value={`${position_size.toFixed(2)}%`}
          color={position_size <= 1 ? 'var(--green)' : position_size <= 2 ? 'var(--amber)' : 'var(--red)'}
        />
        <MetricCard
          label="Risk"
          value={`${risk_pips.toFixed(0)} pips`}
          color="var(--red)"
        />
        <MetricCard
          label="Reward"
          value={`${reward_pips.toFixed(0)} pips`}
          color="var(--green)"
        />
      </div>

      {/* Price Levels */}
      <div style={{
        marginTop: 16,
        padding: 12,
        background: 'var(--bg4)',
        borderRadius: 4,
        fontSize: 10,
      }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 8 }}>
          <div>
            <span style={{ color: 'var(--text3)' }}>Entry: </span>
            <span className="mono" style={{ color: 'var(--text)', fontWeight: 500 }}>
              {entry_low?.toFixed(5)} - {entry_high?.toFixed(5)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Current: </span>
            <span className="mono" style={{ color: 'var(--amber)', fontWeight: 600 }}>
              {current_price?.toFixed(5)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Stop: </span>
            <span className="mono" style={{ color: 'var(--red)', fontWeight: 500 }}>
              {stop_loss?.toFixed(5)}
            </span>
          </div>
          <div>
            <span style={{ color: 'var(--text3)' }}>Target: </span>
            <span className="mono" style={{ color: 'var(--green)', fontWeight: 500 }}>
              {take_profit?.toFixed(5)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string; color: string }) {
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
      <div className="mono" style={{ fontSize: 16, fontWeight: 600, color }}>
        {value}
      </div>
    </div>
  );
}

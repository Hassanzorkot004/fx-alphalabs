import type { Signal, Price } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';

interface SignalCardProps {
  signal: Signal;
  price?: Price;
  isSelected: boolean;
  onClick: () => void;
}

export default function SignalCardNew({ signal, price, isSelected, onClick }: SignalCardProps) {
  const pair = signal.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;
  
  // Direction color
  const directionColor = 
    signal.direction === 'BUY' ? 'var(--green)' :
    signal.direction === 'SELL' ? 'var(--red)' :
    'var(--text3)';

  // Agreement badge color
  const agreementColor =
    signal.agent_agreement === 'FULL' ? 'var(--green)' :
    signal.agent_agreement === 'PARTIAL' ? 'var(--amber)' :
    'var(--text3)';

  // Lifecycle status
  const lifecycleColor =
    signal.lifecycle_status === 'active' ? 'var(--green)' :
    signal.lifecycle_status === 'near_expiry' ? 'var(--amber)' :
    'var(--text3)';

  const lifecycleLabel =
    signal.lifecycle_status === 'active' ? 'Active' :
    signal.lifecycle_status === 'near_expiry' ? 'Near Expiry' :
    'Expired';

  // Current price display
  const currentPrice = price?.price || signal.price_at_signal || 0;
  const priceChange = price?.change || 0;
  const priceChangePct = price?.change_pct || 0;

  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--bg2)',
        border: `1px solid ${isSelected ? 'var(--amber)' : 'var(--border)'}`,
        borderRadius: 8,
        padding: 16,
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        borderBottomWidth: isSelected ? 3 : 1,
        borderBottomColor: isSelected ? 'var(--amber)' : 'var(--border)',
      }}
      className="hover:border-border2"
    >
      {/* Header: Pair + Price */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--text)' }}>
            {pair}
          </div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
            {signal.age_hours ? `${signal.age_hours.toFixed(1)}h ago` : ''}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>
            {currentPrice.toFixed(decimals)}
          </div>
          {price && (
            <div className="mono" style={{ 
              fontSize: 11, 
              color: priceChange >= 0 ? 'var(--green)' : 'var(--red)' 
            }}>
              {priceChange >= 0 ? '+' : ''}{priceChange.toFixed(decimals)} ({priceChangePct >= 0 ? '+' : ''}{priceChangePct.toFixed(2)}%)
            </div>
          )}
        </div>
      </div>

      {/* Direction + Agreement */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <div style={{
          background: directionColor + '20',
          color: directionColor,
          padding: '4px 10px',
          borderRadius: 4,
          fontSize: 12,
          fontWeight: 600,
          border: `1px solid ${directionColor}40`,
        }}>
          {signal.direction}
        </div>
        <div style={{
          background: agreementColor + '20',
          color: agreementColor,
          padding: '4px 10px',
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 500,
          border: `1px solid ${agreementColor}40`,
        }}>
          {signal.agent_agreement}
        </div>
        <div style={{
          background: lifecycleColor + '20',
          color: lifecycleColor,
          padding: '4px 10px',
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 500,
          border: `1px solid ${lifecycleColor}40`,
          marginLeft: 'auto',
        }}>
          {lifecycleLabel}
        </div>
      </div>

      {/* Confidence bar */}
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>Confidence</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text2)' }}>
            {(signal.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div style={{ 
          height: 4, 
          background: 'var(--bg4)', 
          borderRadius: 2, 
          overflow: 'hidden' 
        }}>
          <div style={{
            height: '100%',
            width: `${signal.confidence * 100}%`,
            background: `linear-gradient(90deg, ${directionColor}, ${directionColor}80)`,
            transition: 'width 0.3s ease',
          }} />
        </div>
      </div>

      {/* Agent pills */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        <AgentPill label="Macro" signal={signal.macro_regime} />
        <AgentPill label="Tech" signal={signal.tech_signal} />
        <AgentPill label="Sent" signal={signal.sent_signal} />
      </div>
    </div>
  );
}

function AgentPill({ label, signal }: { label: string; signal: string }) {
  const signalUpper = signal.toUpperCase();
  const color = 
    signalUpper.includes('BUY') || signalUpper.includes('BULLISH') ? 'var(--green)' :
    signalUpper.includes('SELL') || signalUpper.includes('BEARISH') ? 'var(--red)' :
    'var(--text3)';

  return (
    <div style={{
      background: 'var(--bg3)',
      border: `1px solid ${color}40`,
      borderRadius: 12,
      padding: '4px 10px',
      fontSize: 10,
      display: 'flex',
      alignItems: 'center',
      gap: 6,
    }}>
      <span style={{ color: 'var(--text3)', fontWeight: 500 }}>{label}</span>
      <span style={{ color, fontWeight: 600 }}>{signal}</span>
    </div>
  );
}

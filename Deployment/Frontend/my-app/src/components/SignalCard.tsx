import type { Signal, Price, LiveContext } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';

interface SignalCardProps {
  signal: Signal;
  price?: Price;
  liveContext?: LiveContext;
  isSelected: boolean;
  onClick: () => void;
}

export default function SignalCardNew({ signal, price, liveContext, isSelected, onClick }: SignalCardProps) {
  const pair = signal.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;
  
  // Use live context if available
  const validity = liveContext?.validity;
  const priceContext = liveContext?.price_context;
  const techIndicators = liveContext?.tech_indicators;
  
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

  // Validity status color
  const validityColor =
    validity?.status === 'VALID' ? 'var(--green)' :
    validity?.status === 'WARNING' || validity?.status === 'NEAR_EXPIRY' ? 'var(--amber)' :
    'var(--red)';

  const validityLabel =
    validity?.status === 'VALID' ? 'Active' :
    validity?.status === 'WARNING' ? 'Warning' :
    validity?.status === 'NEAR_EXPIRY' ? 'Near Expiry' :
    validity?.status === 'STOPPED_OUT' ? 'Stopped Out' :
    validity?.status === 'TARGET_HIT' ? 'Target Hit' :
    validity?.status === 'EXPIRED' ? 'Expired' :
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
        opacity: validity?.status === 'EXPIRED' || validity?.status === 'STOPPED_OUT' ? 0.6 : 1,
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
            {liveContext?.signal_age_display || (signal.age_hours ? `${signal.age_hours.toFixed(1)}h ago` : '')}
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

      {/* Direction + Agreement + Validity */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
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
          background: validityColor + '20',
          color: validityColor,
          padding: '4px 10px',
          borderRadius: 4,
          fontSize: 11,
          fontWeight: 500,
          border: `1px solid ${validityColor}40`,
          marginLeft: 'auto',
        }}>
          {validityLabel}
        </div>
      </div>

      {/* Validity Warning/Info */}
      {validity && validity.status !== 'VALID' && (
        <div style={{
          background: validityColor + '10',
          border: `1px solid ${validityColor}30`,
          borderRadius: 4,
          padding: 8,
          marginBottom: 12,
          fontSize: 11,
          color: 'var(--text2)',
        }}>
          <div style={{ fontWeight: 600, marginBottom: 4, color: validityColor }}>
            {validity.reason}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text3)' }}>
            {validity.action_recommended}
          </div>
        </div>
      )}

      {/* Price Context (vs entry/stop/target) */}
      {priceContext && (priceContext.vs_entry || priceContext.vs_stop || priceContext.vs_target) && (
        <div style={{
          background: 'var(--bg3)',
          borderRadius: 4,
          padding: 8,
          marginBottom: 12,
          fontSize: 10,
          display: 'flex',
          gap: 12,
          flexWrap: 'wrap',
        }}>
          {priceContext.vs_entry && (
            <div>
              <span style={{ color: 'var(--text3)' }}>Entry: </span>
              <span className="mono" style={{ color: 'var(--text2)', fontWeight: 500 }}>
                {priceContext.vs_entry}
              </span>
            </div>
          )}
          {priceContext.vs_stop && (
            <div>
              <span style={{ color: 'var(--text3)' }}>Stop: </span>
              <span className="mono" style={{ color: 'var(--text2)', fontWeight: 500 }}>
                {priceContext.vs_stop}
              </span>
            </div>
          )}
          {priceContext.vs_target && (
            <div>
              <span style={{ color: 'var(--text3)' }}>Target: </span>
              <span className="mono" style={{ color: 'var(--text2)', fontWeight: 500 }}>
                {priceContext.vs_target}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Technical Indicators from Model */}
      {techIndicators && (techIndicators.p_buy !== undefined || techIndicators.rsi_14 !== null) && (
        <div style={{
          background: 'var(--bg3)',
          borderRadius: 4,
          padding: 8,
          marginBottom: 12,
          fontSize: 10,
        }}>
          <div style={{ 
            color: 'var(--text3)', 
            marginBottom: 6, 
            fontSize: 9,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            fontWeight: 600,
          }}>
            Technical Agent Output
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {techIndicators.rsi_14 !== null && techIndicators.rsi_14 !== undefined && (
              <div>
                <span style={{ color: 'var(--text3)' }}>RSI: </span>
                <span className="mono" style={{ 
                  color: techIndicators.rsi_14 > 70 ? 'var(--red)' : 
                         techIndicators.rsi_14 < 30 ? 'var(--green)' : 'var(--text2)',
                  fontWeight: 500 
                }}>
                  {techIndicators.rsi_14.toFixed(1)}
                </span>
              </div>
            )}
            {techIndicators.p_buy !== undefined && (
              <div>
                <span style={{ color: 'var(--text3)' }}>P(BUY): </span>
                <span className="mono" style={{ 
                  color: techIndicators.p_buy > 0.5 ? 'var(--green)' : 'var(--text2)',
                  fontWeight: 500 
                }}>
                  {(techIndicators.p_buy * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {techIndicators.p_sell !== undefined && (
              <div>
                <span style={{ color: 'var(--text3)' }}>P(SELL): </span>
                <span className="mono" style={{ 
                  color: techIndicators.p_sell > 0.5 ? 'var(--red)' : 'var(--text2)',
                  fontWeight: 500 
                }}>
                  {(techIndicators.p_sell * 100).toFixed(0)}%
                </span>
              </div>
            )}
            {techIndicators.p_hold !== undefined && (
              <div>
                <span style={{ color: 'var(--text3)' }}>P(HOLD): </span>
                <span className="mono" style={{ color: 'var(--text2)', fontWeight: 500 }}>
                  {(techIndicators.p_hold * 100).toFixed(0)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )}

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

      {/* Time remaining */}
      {liveContext?.time_remaining && (
        <div style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: '1px solid var(--border)',
          fontSize: 10,
          color: 'var(--text3)',
          textAlign: 'center',
        }}>
          {liveContext.time_remaining}
        </div>
      )}
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

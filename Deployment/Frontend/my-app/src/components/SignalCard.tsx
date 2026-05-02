import { useState } from 'react';
import type { Signal, Price, LiveContext } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';
import { useTrading } from '../hooks/useTrading';

interface SignalCardProps {
  signal: Signal;
  price?: Price;
  liveContext?: LiveContext;
  isSelected: boolean;
  onClick: () => void;
}

type BreakdownItem = {
  label: string;
  score: number;
  signal: string;
  color: string;
};

export default function SignalCardNew({
  signal,
  price,
  liveContext,
  isSelected,
  onClick,
}: SignalCardProps) {
  const pair = signal.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;

  const { openTrade } = useTrading();

  const [tradeMessage, setTradeMessage] = useState<string | null>(null);
  const [tradeMessageType, setTradeMessageType] = useState<'success' | 'error'>('success');

  const validity = liveContext?.validity;
  const priceContext = liveContext?.price_context;
  const techIndicators = liveContext?.tech_indicators;

  const currentPrice = price?.price || signal.price_at_signal || 0;
  const priceChange = price?.change || 0;
  const priceChangePct = price?.change_pct || 0;

  const directionColor =
    signal.direction === 'BUY'
      ? 'var(--green)'
      : signal.direction === 'SELL'
        ? 'var(--red)'
        : 'var(--text3)';

  const agreementColor =
    signal.agent_agreement === 'FULL'
      ? 'var(--green)'
      : signal.agent_agreement === 'PARTIAL'
        ? 'var(--amber)'
        : 'var(--text3)';

  const validityColor =
    validity?.status === 'VALID'
      ? 'var(--green)'
      : validity?.status === 'WARNING' || validity?.status === 'NEAR_EXPIRY'
        ? 'var(--amber)'
        : 'var(--red)';

  const validityLabel =
    validity?.status === 'VALID'
      ? 'Active'
      : validity?.status === 'WARNING'
        ? 'Warning'
        : validity?.status === 'NEAR_EXPIRY'
          ? 'Near Expiry'
          : validity?.status === 'STOPPED_OUT'
            ? 'Stopped Out'
            : validity?.status === 'TARGET_HIT'
              ? 'Target Hit'
              : validity?.status === 'EXPIRED'
                ? 'Expired'
                : signal.lifecycle_status === 'active'
                  ? 'Active'
                  : signal.lifecycle_status === 'near_expiry'
                    ? 'Near Expiry'
                    : 'Expired';

  const breakdown = getDecisionBreakdown(signal);

  async function handleOpenTrade(e: React.MouseEvent) {
    e.stopPropagation();

    if (signal.direction === 'HOLD') {
      setTradeMessageType('error');
      setTradeMessage('Cannot open HOLD trades');
      return;
    }

    if (!currentPrice || currentPrice <= 0) {
      setTradeMessageType('error');
      setTradeMessage('Invalid current price');
      return;
    }

    try {
      await openTrade({
        symbol: pair,
        side: signal.direction,
        entry_price: currentPrice,
        quantity: 1000,
        stop_loss: signal.stop_estimate ?? null,
        take_profit: signal.target_estimate ?? null,
        source_signal_id: `${pair}-${signal.timestamp}`,
      });

      setTradeMessageType('success');
      setTradeMessage(`${signal.direction} trade opened on ${pair}`);

      setTimeout(() => setTradeMessage(null), 2500);
    } catch (err) {
      console.error(err);
      setTradeMessageType('error');
      setTradeMessage('Failed to open trade');
    }
  }

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
        opacity:
          validity?.status === 'EXPIRED' || validity?.status === 'STOPPED_OUT'
            ? 0.6
            : 1,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
        <div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 600 }}>
            {pair}
          </div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
            {liveContext?.signal_age_display ||
              (signal.age_hours ? `${signal.age_hours.toFixed(1)}h ago` : '')}
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <div className="mono" style={{ fontSize: 18, fontWeight: 600 }}>
            {currentPrice.toFixed(decimals)}
          </div>

          {price && (
            <div
              className="mono"
              style={{
                fontSize: 11,
                color: priceChange >= 0 ? 'var(--green)' : 'var(--red)',
              }}
            >
              {priceChange >= 0 ? '+' : ''}
              {priceChange.toFixed(decimals)} ({priceChangePct >= 0 ? '+' : ''}
              {priceChangePct.toFixed(2)}%)
            </div>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap' }}>
        <Badge label={signal.direction} color={directionColor} />
        <Badge label={signal.agent_agreement} color={agreementColor} />

        <div style={{ marginLeft: 'auto' }}>
          <Badge label={validityLabel} color={validityColor} />
        </div>
      </div>

      {validity && validity.status !== 'VALID' && (
        <div
          style={{
            background: validityColor + '10',
            border: `1px solid ${validityColor}30`,
            borderRadius: 4,
            padding: 8,
            marginBottom: 12,
            fontSize: 11,
            color: 'var(--text2)',
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4, color: validityColor }}>
            {validity.reason}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text3)' }}>
            {validity.action_recommended}
          </div>
        </div>
      )}

      {priceContext &&
        (priceContext.vs_entry || priceContext.vs_stop || priceContext.vs_target) && (
          <div
            style={{
              background: 'var(--bg3)',
              borderRadius: 4,
              padding: 8,
              marginBottom: 12,
              fontSize: 10,
              display: 'flex',
              gap: 12,
              flexWrap: 'wrap',
            }}
          >
            {priceContext.vs_entry && <SmallInfo label="Entry" value={priceContext.vs_entry} />}
            {priceContext.vs_stop && <SmallInfo label="Stop" value={priceContext.vs_stop} />}
            {priceContext.vs_target && <SmallInfo label="Target" value={priceContext.vs_target} />}
          </div>
        )}

      {techIndicators && (
        <div
          style={{
            background: 'var(--bg3)',
            borderRadius: 4,
            padding: 8,
            marginBottom: 12,
            fontSize: 10,
          }}
        >
          <SectionLabel label="Technical Agent Output" />

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {techIndicators.rsi_14 !== null && techIndicators.rsi_14 !== undefined && (
              <SmallInfo label="RSI" value={techIndicators.rsi_14.toFixed(1)} />
            )}
            <SmallInfo label="P(BUY)" value={`${(techIndicators.p_buy * 100).toFixed(0)}%`} />
            <SmallInfo label="P(SELL)" value={`${(techIndicators.p_sell * 100).toFixed(0)}%`} />
            <SmallInfo label="P(HOLD)" value={`${(techIndicators.p_hold * 100).toFixed(0)}%`} />
          </div>
        </div>
      )}

      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: 'var(--text3)' }}>Confidence</span>
          <span className="mono" style={{ fontSize: 11, color: 'var(--text2)' }}>
            {(signal.confidence * 100).toFixed(0)}%
          </span>
        </div>

        <div
          style={{
            height: 4,
            background: 'var(--bg4)',
            borderRadius: 2,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${signal.confidence * 100}%`,
              background: directionColor,
            }}
          />
        </div>
      </div>

      <DecisionBreakdown
        items={breakdown.items}
        dominantAgent={breakdown.dominantAgent}
        consensusStrength={breakdown.consensusStrength}
      />

      <RiskManagementLayer signal={signal} />

      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 12 }}>
        <AgentPill label="Macro" signal={signal.macro_regime} />
        <AgentPill label="Tech" signal={signal.tech_signal} />
        <AgentPill label="Sent" signal={signal.sent_signal} />
      </div>

      {signal.direction !== 'HOLD' && (
        <div
          style={{
            marginTop: 14,
            paddingTop: 12,
            borderTop: '1px solid var(--border)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 10,
          }}
        >
          <button
            onClick={handleOpenTrade}
            style={{
              background: signal.direction === 'BUY' ? 'var(--green)' : 'var(--red)',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              padding: '8px 12px',
              fontSize: 12,
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            Open {signal.direction}
          </button>

          <div style={{ fontSize: 10, color: 'var(--text3)' }}>
            Qty: 1000
          </div>
        </div>
      )}

      {tradeMessage && (
        <div
          style={{
            marginTop: 10,
            padding: '8px 10px',
            borderRadius: 6,
            fontSize: 11,
            fontWeight: 600,
            color: tradeMessageType === 'success' ? 'var(--green)' : 'var(--red)',
            background:
              tradeMessageType === 'success'
                ? 'rgba(0, 255, 150, 0.08)'
                : 'rgba(255, 80, 80, 0.08)',
            border:
              tradeMessageType === 'success'
                ? '1px solid rgba(0, 255, 150, 0.25)'
                : '1px solid rgba(255, 80, 80, 0.25)',
          }}
        >
          {tradeMessage}
        </div>
      )}

      {liveContext?.time_remaining && (
        <div
          style={{
            marginTop: 12,
            paddingTop: 12,
            borderTop: '1px solid var(--border)',
            fontSize: 10,
            color: 'var(--text3)',
            textAlign: 'center',
          }}
        >
          {liveContext.time_remaining}
        </div>
      )}
    </div>
  );
}

function DecisionBreakdown({
  items,
  dominantAgent,
  consensusStrength,
}: {
  items: BreakdownItem[];
  dominantAgent: string;
  consensusStrength: string;
}) {
  return (
    <div
      style={{
        background: 'var(--bg3)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: 10,
        marginTop: 12,
        marginBottom: 4,
      }}
    >
      <SectionLabel label="AI Decision Breakdown" />

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {items.map((item) => (
          <div key={item.label}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                marginBottom: 4,
                fontSize: 10,
              }}
            >
              <span style={{ color: 'var(--text2)', fontWeight: 600 }}>
                {item.label}
              </span>
              <span className="mono" style={{ color: item.color, fontWeight: 700 }}>
                {item.score}%
              </span>
            </div>

            <div
              style={{
                height: 5,
                background: 'var(--bg4)',
                borderRadius: 999,
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  height: '100%',
                  width: `${item.score}%`,
                  background: item.color,
                  borderRadius: 999,
                }}
              />
            </div>

            <div style={{ marginTop: 3, fontSize: 9, color: 'var(--text3)' }}>
              {item.signal}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          marginTop: 10,
          paddingTop: 8,
          borderTop: '1px solid var(--border)',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 8,
          fontSize: 10,
        }}
      >
        <InfoBlock label="Dominant Driver" value={dominantAgent} />
        <InfoBlock label="Consensus" value={consensusStrength} />
      </div>
    </div>
  );
}

function RiskManagementLayer({ signal }: { signal: Signal }) {
  const entry = signal.price_at_signal || 0;
  const stop = signal.stop_estimate || 0;
  const target = signal.target_estimate || 0;

  let rrRatio = 0;

  if (entry && stop && target) {
    const risk = Math.abs(entry - stop);
    const reward = Math.abs(target - entry);

    if (risk > 0) {
      rrRatio = reward / risk;
    }
  }

  const qualityScore = Math.min(
    100,
    Math.round(
      signal.confidence * 55 +
        (signal.agent_agreement === 'FULL'
          ? 30
          : signal.agent_agreement === 'PARTIAL'
            ? 18
            : 8)
    )
  );

  const riskLevel =
    rrRatio >= 2
      ? 'Low'
      : rrRatio >= 1.2
        ? 'Medium'
        : rrRatio > 0
          ? 'High'
          : 'Unknown';

  const riskColor =
    riskLevel === 'Low'
      ? 'var(--green)'
      : riskLevel === 'Medium'
        ? 'var(--amber)'
        : riskLevel === 'High'
          ? 'var(--red)'
          : 'var(--text3)';

  const suggestedRisk =
    qualityScore >= 80
      ? '2.0%'
      : qualityScore >= 65
        ? '1.0%'
        : '0.5%';

  return (
    <div
      style={{
        marginTop: 12,
        background: 'var(--bg3)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        padding: 10,
      }}
    >
      <SectionLabel label="Risk Management Layer" />

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 10,
        }}
      >
        <RiskCard
          label="Trade Quality"
          value={`${qualityScore}/100`}
          color={
            qualityScore >= 75
              ? 'var(--green)'
              : qualityScore >= 55
                ? 'var(--amber)'
                : 'var(--red)'
          }
        />

        <RiskCard label="Risk Level" value={riskLevel} color={riskColor} />

        <RiskCard
          label="RR Ratio"
          value={rrRatio ? `1 : ${rrRatio.toFixed(1)}` : 'N/A'}
          color={
            rrRatio >= 2
              ? 'var(--green)'
              : rrRatio >= 1.2
                ? 'var(--amber)'
                : rrRatio > 0
                  ? 'var(--red)'
                  : 'var(--text3)'
          }
        />

        <RiskCard label="Suggested Risk" value={suggestedRisk} color="var(--blue)" />
      </div>
    </div>
  );
}

function RiskCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div
      style={{
        background: 'var(--bg2)',
        border: `1px solid ${color}30`,
        borderRadius: 6,
        padding: 10,
      }}
    >
      <div
        style={{
          fontSize: 9,
          color: 'var(--text3)',
          textTransform: 'uppercase',
          marginBottom: 6,
          letterSpacing: '0.5px',
          fontWeight: 700,
        }}
      >
        {label}
      </div>

      <div className="mono" style={{ color, fontSize: 14, fontWeight: 800 }}>
        {value}
      </div>
    </div>
  );
}

function InfoBlock({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div style={{ color: 'var(--text3)', marginBottom: 2 }}>{label}</div>
      <div style={{ color: 'var(--text)', fontWeight: 700 }}>{value}</div>
    </div>
  );
}

function SectionLabel({ label }: { label: string }) {
  return (
    <div
      style={{
        color: 'var(--text3)',
        marginBottom: 8,
        fontSize: 9,
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        fontWeight: 700,
      }}
    >
      {label}
    </div>
  );
}

function getDecisionBreakdown(signal: Signal): {
  items: BreakdownItem[];
  dominantAgent: string;
  consensusStrength: string;
} {
  const macroScore = normalizeScore(signal.macro_score, inferMacroScore(signal));
  const technicalScore = normalizeScore(signal.technical_score, inferTechnicalScore(signal));
  const sentimentScore = normalizeScore(signal.sentiment_score, inferSentimentScore(signal));

  const total = macroScore + technicalScore + sentimentScore || 1;

  const items: BreakdownItem[] = [
    {
      label: 'Macro Agent',
      score: Math.round((macroScore / total) * 100),
      signal: signal.macro_regime || 'neutral',
      color: getSignalColor(signal.macro_regime),
    },
    {
      label: 'Technical Agent',
      score: Math.round((technicalScore / total) * 100),
      signal: signal.tech_signal || 'neutral',
      color: getSignalColor(signal.tech_signal),
    },
    {
      label: 'Sentiment Agent',
      score: Math.round((sentimentScore / total) * 100),
      signal: signal.sent_signal || 'neutral',
      color: getSignalColor(signal.sent_signal),
    },
  ];

  const dominant = items.reduce((max, item) => (item.score > max.score ? item : max), items[0]);

  return {
    items,
    dominantAgent: signal.dominant_agent || dominant.label.replace(' Agent', ''),
    consensusStrength: signal.consensus_strength || inferConsensus(signal.agent_agreement),
  };
}

function normalizeScore(value: number | undefined, fallback: number) {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return Math.max(0, Math.min(100, value));
  }

  return fallback;
}

function inferMacroScore(signal: Signal) {
  const macro = signal.macro_regime?.toLowerCase() || '';

  if (macro.includes('bull') || macro.includes('bear')) return 40;
  if (macro.includes('neutral')) return 25;

  return 30;
}

function inferTechnicalScore(signal: Signal) {
  const pBuy = signal.p_buy ?? 0;
  const pSell = signal.p_sell ?? 0;
  const pHold = signal.p_hold ?? 0;

  const maxProb = Math.max(pBuy, pSell, pHold);

  if (maxProb > 0) return Math.round(maxProb * 100);

  return Math.round((signal.confidence || 0.5) * 60);
}

function inferSentimentScore(signal: Signal) {
  const articles = signal.n_articles ?? 0;
  const raw = Math.abs(signal.sent_raw ?? 0);

  if (articles === 0) return 15;

  return Math.min(45, 20 + Math.round(raw * 25));
}

function inferConsensus(agentAgreement: string) {
  if (agentAgreement === 'FULL') return 'Strong';
  if (agentAgreement === 'PARTIAL') return 'Medium';

  return 'Weak';
}

function getSignalColor(value: string) {
  const normalized = value?.toUpperCase() || '';

  if (normalized.includes('BUY') || normalized.includes('BULLISH')) return 'var(--green)';
  if (normalized.includes('SELL') || normalized.includes('BEARISH')) return 'var(--red)';
  if (normalized.includes('HOLD') || normalized.includes('NEUTRAL')) return 'var(--amber)';

  return 'var(--blue)';
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <div
      style={{
        background: color + '20',
        color,
        padding: '4px 10px',
        borderRadius: 4,
        fontSize: 11,
        fontWeight: 600,
        border: `1px solid ${color}40`,
      }}
    >
      {label}
    </div>
  );
}

function SmallInfo({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span style={{ color: 'var(--text3)' }}>{label}: </span>
      <span className="mono" style={{ color: 'var(--text2)', fontWeight: 500 }}>
        {value}
      </span>
    </div>
  );
}

function AgentPill({ label, signal }: { label: string; signal: string }) {
  const color = getSignalColor(signal);

  return (
    <div
      style={{
        background: 'var(--bg3)',
        border: `1px solid ${color}40`,
        borderRadius: 12,
        padding: '4px 10px',
        fontSize: 10,
        display: 'flex',
        alignItems: 'center',
        gap: 6,
      }}
    >
      <span style={{ color: 'var(--text3)', fontWeight: 500 }}>{label}</span>
      <span style={{ color, fontWeight: 600 }}>{signal}</span>
    </div>
  );
}
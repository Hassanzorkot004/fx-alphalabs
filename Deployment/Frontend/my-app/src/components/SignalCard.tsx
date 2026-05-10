import { useState } from 'react';
import type { Signal, Price, LiveContext } from '../Types';
import { PAIR_DECIMALS } from '../config/constants';

interface SignalCardProps {
  signal: Signal;
  price?: Price;
  liveContext?: LiveContext;
  isSelected: boolean;
  onClick: () => void;
}

export default function SignalCard({ signal, price, liveContext, isSelected, onClick }: SignalCardProps) {
  const [analystOpen, setAnalystOpen] = useState(false);
  const pair = signal.pair.replace('=X', '');
  const decimals = PAIR_DECIMALS[pair] || 5;

  const currentPrice = price?.price || signal.price_at_signal || 0;
  const priceChange = price?.change || 0;
  const priceChangePct = price?.change_pct || 0;

  const isHold = signal.direction === 'HOLD';

  const dirColor =
    signal.direction === 'BUY'  ? 'var(--green)' :
    signal.direction === 'SELL' ? 'var(--red)'   : 'var(--text3)';

  const confidence = Math.round(signal.confidence * 100);
  const convictionScore = (signal.confidence * 5).toFixed(1);

  // What direction is the system leaning even when HOLD?
  const leanDir = (signal.p_sell ?? 0) > (signal.p_buy ?? 0) ? 'SELL' : 'BUY';
  const leanColor = leanDir === 'BUY' ? 'var(--green)' : 'var(--red)';
  const leanStrength = Math.round(Math.max(signal.p_sell ?? 0, signal.p_buy ?? 0) * 100);

  const driverLabel = signal.source ? signal.source.toUpperCase() : 'GROQ';
  const riskAlert = liveContext?.validity?.reason || null;
  const hasRiskAlert = riskAlert && liveContext?.validity?.status !== 'VALID';

  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--bg2)',
        border: `1px solid ${isSelected ? 'var(--cyan)' : isHold ? 'var(--border)' : dirColor + '55'}`,
        borderRadius: 8,
        cursor: 'pointer',
        transition: 'border-color 0.15s ease',
        overflow: 'hidden',
        opacity: liveContext?.validity?.status === 'STOPPED_OUT' ? 0.55 : 1,
      }}
    >
      {/* ── Header: Pair + Price ─────────────────────────────── */}
      <div style={{ padding: '14px 16px 10px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 10 }}>
          <div>
            <div className="mono" style={{ fontSize: 17, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' }}>
              {pair}
            </div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Driver: {driverLabel}
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div className="mono" style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.02em' }}>
              {currentPrice.toFixed(decimals)}
            </div>
            {price && (
              <div className="mono" style={{ fontSize: 11, color: priceChange >= 0 ? 'var(--green)' : 'var(--red)', marginTop: 2 }}>
                {priceChange >= 0 ? '▲' : '▼'} {Math.abs(priceChange).toFixed(decimals)} ({priceChangePct >= 0 ? '+' : ''}{priceChangePct.toFixed(2)}%)
              </div>
            )}
          </div>
        </div>

        {isHold ? (
          /* ── HOLD STATE ─────────────────────────────────────── */
          <div style={{ marginBottom: 10 }}>
            {/* Big HOLD banner */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              marginBottom: 8,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: 'var(--text3)',
                  boxShadow: '0 0 6px var(--text3)',
                }} />
                <span className="mono" style={{ fontSize: 15, fontWeight: 800, color: 'var(--text2)', letterSpacing: '0.08em' }}>
                  HOLD
                </span>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>—</span>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                  {signal.agent_agreement === 'CONFLICT' ? 'Conflicting signals' : 'Insufficient conviction'}
                </span>
              </div>
              <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
                {confidence}% conf
              </span>
            </div>

            {/* Lean indicator */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '7px 14px',
              background: leanColor + '0a',
              border: `1px solid ${leanColor}25`,
              borderRadius: 6,
            }}>
              <span style={{ fontSize: 10, color: 'var(--text3)' }}>System leaning:</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: leanColor }}>{leanDir}</span>
              <div style={{ flex: 1, height: 3, background: 'var(--bg4)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  height: '100%',
                  width: `${leanStrength}%`,
                  background: leanColor + '60',
                  borderRadius: 2,
                }} />
              </div>
              <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>{leanStrength}%</span>
              <span style={{ fontSize: 10, color: 'var(--text3)' }}>— not tradeable yet</span>
            </div>
          </div>
        ) : (
          /* ── ACTIVE SIGNAL STATE ─────────────────────────────── */
          <>
            {/* Big direction banner */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              background: dirColor + '12',
              border: `1px solid ${dirColor}40`,
              borderRadius: 6,
              marginBottom: 8,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: dirColor,
                  boxShadow: `0 0 8px ${dirColor}`,
                  animation: 'pulse-dot 1.5s ease-in-out infinite',
                }} />
                <span className="mono" style={{ fontSize: 18, fontWeight: 800, color: dirColor, letterSpacing: '0.06em' }}>
                  {signal.direction}
                </span>
                <span style={{ fontSize: 11, color: 'var(--text3)' }}>—</span>
                <span style={{ fontSize: 11, color: 'var(--text2)' }}>
                  {signal.agent_agreement === 'FULL' ? 'All agents agree' :
                   signal.agent_agreement === 'PARTIAL' ? 'Majority agree' : 'Weak signal'}
                </span>
              </div>
              <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: dirColor }}>
                {confidence}%
              </span>
            </div>

            {/* Conviction bar */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Conviction
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
                  {signal.direction === 'SELL' ? convictionScore : '0.0'}
                </span>
                <div style={{ width: 120, height: 4, background: 'var(--bg4)', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{
                    height: '100%',
                    width: `${confidence}%`,
                    background: `linear-gradient(90deg, ${dirColor}80, ${dirColor})`,
                    transition: 'width 0.3s ease',
                  }} />
                </div>
                <span className="mono" style={{ fontSize: 11, color: dirColor, fontWeight: 600 }}>
                  {signal.direction === 'BUY' ? convictionScore : '0.0'}
                </span>
              </div>
            </div>
          </>
        )}

        {/* ── Agent Pills Row ───────────────────────────────── */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 10 }}>
          <AgentPill label="MACRO" signal={signal.macro_regime} />
          <AgentPill label="TECH"  signal={signal.tech_signal} />
          <AgentPill label="SENT"  signal={signal.sent_signal} />
        </div>
      </div>

      {/* ── Analyst Breakdown Toggle ──────────────────────── */}
      <div
        onClick={e => { e.stopPropagation(); setAnalystOpen(v => !v); }}
        style={{
          padding: '7px 16px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          cursor: 'pointer',
          background: analystOpen ? 'var(--bg3)' : 'transparent',
          transition: 'background 0.15s ease',
          userSelect: 'none',
        }}
      >
        <span style={{
          fontSize: 9,
          color: 'var(--cyan)',
          transform: analystOpen ? 'rotate(90deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s ease',
          display: 'inline-block',
        }}>▶</span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
          {analystOpen ? 'Hide' : 'Show'} Analyst Breakdown
        </span>
      </div>

      {/* ── Analyst Breakdown Panel ───────────────────────── */}
      {analystOpen && (
        <div
          onClick={e => e.stopPropagation()}
          style={{
            borderTop: '1px solid var(--border)',
            background: 'var(--bg3)',
            padding: '12px 16px',
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            animation: 'slide-up 0.2s ease',
          }}
        >
          <AnalystSection
            label="MACRO"
            signal={signal.macro_regime}
            confidence={signal.regime_prob_bull || signal.regime_prob_neut || signal.regime_prob_bear ? confidence : null}
            features={[
              signal.yield_z != null ? `Yield curve: ${signal.yield_z > 0.3 ? 'steepening (USD bullish)' : signal.yield_z < -0.3 ? 'inverted (risk-off)' : 'flat (neutral)'}` : null,
              signal.vix_z   != null ? `Volatility: ${signal.vix_z > 0.5 ? 'elevated (risk-off)' : signal.vix_z < -0.5 ? 'suppressed (risk-on)' : 'normal'}` : null,
              signal.carry_signal != null && signal.carry_signal !== 0 ? `Carry: ${signal.carry_signal > 0 ? 'favours long USD' : 'favours short USD'}` : null,
              signal.regime_prob_bull != null ? `Bull/Bear odds: ${Math.round((signal.regime_prob_bull || 0) * 100)}% / ${Math.round((signal.regime_prob_bear || 0) * 100)}%` : null,
            ].filter(Boolean) as string[]}
            narrative={signal.macro_analyst || buildMacroNarrative(signal)}
            keyFeature={signal.macro_key_feat}
            override={signal.macro_override}
          />
          <AnalystSection
            label="TECHNICAL"
            signal={signal.tech_signal}
            confidence={signal.model_conf != null ? Math.round(signal.model_conf * 100) : null}
            features={[
              signal.rsi14 != null ? `RSI: ${signal.rsi14.toFixed(0)} — ${signal.rsi14 > 70 ? 'overbought' : signal.rsi14 < 30 ? 'oversold' : 'neutral'}` : null,
              signal.macd_hist != null ? `MACD momentum: ${signal.macd_hist > 0 ? 'bullish' : 'bearish'}` : null,
              signal.bb_pos != null ? `Price vs Bollinger: ${signal.bb_pos > 0.8 ? 'near upper band' : signal.bb_pos < 0.2 ? 'near lower band' : 'mid-range'}` : null,
            ].filter(Boolean) as string[]}
            narrative={signal.tech_analyst || buildTechNarrative(signal)}
            keyFeature={signal.tech_key_feat}
            override={signal.tech_override}
          />
          <AnalystSection
            label="SENTIMENT"
            signal={signal.sent_signal}
            confidence={signal.p_bullish != null ? Math.round(signal.p_bullish * 100) : null}
            features={[
              signal.n_articles != null ? `News coverage: ${signal.n_articles} article${signal.n_articles !== 1 ? 's' : ''} analysed` : null,
              signal.sent_raw   != null ? `Sentiment tone: ${signal.sent_raw > 0.1 ? 'bullish' : signal.sent_raw < -0.1 ? 'bearish' : 'neutral'} (${signal.sent_raw > 0 ? '+' : ''}${signal.sent_raw.toFixed(2)})` : null,
            ].filter(Boolean) as string[]}
            narrative={signal.sent_analyst || buildSentNarrative(signal)}
            keyFeature={signal.sent_key_feat}
            override={signal.sent_override}
          />
        </div>
      )}

      {/* ── Risk Alert Footer ─────────────────────────────── */}
      {hasRiskAlert && (
        <div style={{
          padding: '8px 16px',
          borderTop: '1px solid rgba(255,71,87,0.2)',
          background: 'rgba(255,71,87,0.05)',
          fontSize: 11,
          color: 'var(--red)',
          lineHeight: 1.5,
          display: 'flex',
          gap: 6,
          alignItems: 'flex-start',
        }}>
          <span style={{ flexShrink: 0, marginTop: 1 }}>⚠</span>
          <span>{riskAlert}</span>
        </div>
      )}
    </div>
  );
}

/* ── Direction Button ──────────────────────────────────────────── */
function DirectionButton({ label, active, color }: { label: string; active: boolean; color: string }) {
  return (
    <div style={{
      padding: '4px 12px',
      borderRadius: 4,
      fontSize: 11,
      fontWeight: 700,
      letterSpacing: '0.04em',
      background: active ? color + '22' : 'var(--bg4)',
      color: active ? color : 'var(--text3)',
      border: `1px solid ${active ? color + '55' : 'var(--border)'}`,
      transition: 'all 0.15s ease',
      userSelect: 'none',
    }}>
      {label}
    </div>
  );
}

/* ── Agent Pill ────────────────────────────────────────────────── */
function AgentPill({ label, signal }: { label: string; signal: string }) {
  const upper = signal.toUpperCase();
  const color =
    upper.includes('BUY') || upper.includes('BULLISH') ? 'var(--green)' :
    upper.includes('SELL') || upper.includes('BEARISH') ? 'var(--red)'  : 'var(--text3)';

  const dot =
    upper.includes('BUY') || upper.includes('BULLISH') ? 'var(--green)' :
    upper.includes('SELL') || upper.includes('BEARISH') ? 'var(--red)'  : 'var(--text3)';

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 5,
      padding: '3px 8px',
      background: 'var(--bg4)',
      border: '1px solid var(--border)',
      borderRadius: 4,
      fontSize: 10,
    }}>
      <span className="mono" style={{ color: 'var(--text3)', fontWeight: 500 }}>{label}</span>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: dot, flexShrink: 0 }} />
      <span className="mono" style={{ color, fontWeight: 600 }}>{signal}</span>
    </div>
  );
}

/* ── Analyst Section ───────────────────────────────────────────── */
function AnalystSection({
  label, signal, confidence, features, narrative, keyFeature, override,
}: {
  label: string;
  signal: string;
  confidence: number | null;
  features: string[];
  narrative: string;
  keyFeature?: string;
  override?: boolean;
}) {
  const upper = signal.toUpperCase();
  const color =
    upper.includes('BUY') || upper.includes('BULLISH') ? 'var(--green)' :
    upper.includes('SELL') || upper.includes('BEARISH') ? 'var(--red)'  : 'var(--text3)';

  const isOverride = override || upper.includes('OVERRIDE');

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      padding: '10px 12px',
    }}>
      {/* Section header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--cyan)', letterSpacing: '0.06em' }}>
          {label}
        </span>
        <div style={{
          padding: '2px 7px',
          borderRadius: 3,
          fontSize: 9,
          fontWeight: 700,
          background: color + '18',
          color,
          border: `1px solid ${color}40`,
          letterSpacing: '0.04em',
        }}>
          {signal.toUpperCase()}
        </div>
        {keyFeature && (
          <span className="mono" style={{
            fontSize: 9,
            color: 'var(--cyan)',
            background: 'rgba(0,212,255,0.08)',
            border: '1px solid rgba(0,212,255,0.2)',
            padding: '1px 5px',
            borderRadius: 3,
            letterSpacing: '0.02em',
          }}>
            KEY: {keyFeature.toUpperCase()}
          </span>
        )}
        {confidence != null && (
          <span className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginLeft: 'auto' }}>
            {confidence}%
          </span>
        )}
        {isOverride && (
          <span style={{
            padding: '2px 6px',
            borderRadius: 3,
            fontSize: 9,
            fontWeight: 700,
            background: 'rgba(255,71,87,0.15)',
            color: 'var(--red)',
            border: '1px solid rgba(255,71,87,0.3)',
            letterSpacing: '0.04em',
          }}>
            OVERRIDE
          </span>
        )}
      </div>

      {/* Narrative */}
      {narrative && (
        <p style={{ fontSize: 11, color: 'var(--text2)', lineHeight: 1.55, marginBottom: features.length > 0 ? 8 : 0 }}>
          {narrative}
        </p>
      )}

      {/* Feature tags */}
      {features.length > 0 && (
        <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
          {features.map(f => (
            <span key={f} className="mono" style={{
              fontSize: 9,
              color: 'var(--text3)',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              padding: '2px 6px',
              borderRadius: 3,
              letterSpacing: '0.02em',
            }}>
              {f}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Narrative builders ────────────────────────────────────────── */
function buildMacroNarrative(signal: Signal): string {
  if (signal.reasoning) {
    // Extract macro-relevant portion
    const r = signal.reasoning;
    const macroIdx = r.toLowerCase().indexOf('macro');
    if (macroIdx !== -1) {
      const snippet = r.slice(macroIdx, macroIdx + 220);
      return snippet.length < r.length ? snippet + '…' : snippet;
    }
    return r.slice(0, 200) + (r.length > 200 ? '…' : '');
  }
  const regime = signal.macro_regime || 'neutral';
  return `The macro regime is ${regime}, indicating ${
    regime.includes('bull') ? 'a risk-on environment.' :
    regime.includes('bear') ? 'a risk-off environment.' :
    'a balanced market with no strong directional bias.'
  }`;
}

function buildTechNarrative(signal: Signal): string {
  const parts: string[] = [];
  if (signal.rsi14 != null) {
    if (signal.rsi14 > 70) parts.push(`RSI at ${signal.rsi14.toFixed(1)} is overbought.`);
    else if (signal.rsi14 < 30) parts.push(`RSI at ${signal.rsi14.toFixed(1)} is oversold.`);
    else parts.push(`RSI at ${signal.rsi14.toFixed(1)} is neutral.`);
  }
  if (signal.macd_hist != null) {
    parts.push(`MACD histogram is ${signal.macd_hist > 0 ? 'positive' : 'negative'} (${signal.macd_hist.toFixed(5)}).`);
  }
  if (signal.bb_pos != null) {
    if (signal.bb_pos > 0.8) parts.push('Price is near the upper Bollinger Band.');
    else if (signal.bb_pos < 0.2) parts.push('Price is near the lower Bollinger Band.');
  }
  if (parts.length === 0) {
    return `Technical model output: ${signal.tech_signal}.`;
  }
  return parts.join(' ');
}

function buildSentNarrative(signal: Signal): string {
  const parts: string[] = [];
  if (signal.n_articles != null) {
    parts.push(`Based on ${signal.n_articles} article${signal.n_articles !== 1 ? 's' : ''}.`);
  }
  if (signal.p_bullish != null) {
    const pct = Math.round(signal.p_bullish * 100);
    parts.push(`Bullish sentiment probability: ${pct}%.`);
  }
  if (signal.sent_raw != null) {
    parts.push(`Raw sentiment score: ${signal.sent_raw.toFixed(3)}.`);
  }
  if (parts.length === 0) {
    return `Sentiment signal: ${signal.sent_signal}.`;
  }
  return parts.join(' ');
}

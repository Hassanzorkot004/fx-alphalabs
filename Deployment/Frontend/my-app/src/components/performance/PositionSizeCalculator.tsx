import { useState } from 'react';

interface PositionSizeCalculatorProps {
  totalPips: number;
}

export default function PositionSizeCalculator({ totalPips }: PositionSizeCalculatorProps) {
  const [capital, setCapital] = useState(10000);
  const [riskPercent, setRiskPercent] = useState(1);
  const [pipValue, setPipValue] = useState(10); // Standard lot = $10/pip

  const riskAmount = capital * (riskPercent / 100);
  const projectedReturn = totalPips * pipValue;
  const projectedReturnPct = (projectedReturn / capital) * 100;

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 20,
    }}>
      <div style={{ marginBottom: 16 }}>
        <div className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
          Position Size Calculator
        </div>
        <div style={{ fontSize: 12, color: 'var(--text3)' }}>
          "What if" calculator — projected returns based on your capital
        </div>
      </div>

      <div style={{ 
        display: 'grid', 
        gridTemplateColumns: '1fr 1fr 1fr', 
        gap: 20,
        marginBottom: 20,
      }}>
        {/* Capital Input */}
        <div>
          <label style={{ 
            display: 'block', 
            fontSize: 11, 
            color: 'var(--text3)', 
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 8,
          }}>
            Account Capital
          </label>
          <input
            type="number"
            value={capital}
            onChange={(e) => setCapital(Number(e.target.value))}
            style={{
              width: '100%',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              padding: '8px 12px',
              borderRadius: 6,
              fontSize: 14,
              fontWeight: 600,
            }}
            className="mono"
          />
        </div>

        {/* Risk Percent */}
        <div>
          <label style={{ 
            display: 'block', 
            fontSize: 11, 
            color: 'var(--text3)', 
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 8,
          }}>
            Risk Per Trade (%)
          </label>
          <input
            type="number"
            value={riskPercent}
            onChange={(e) => setRiskPercent(Number(e.target.value))}
            min={0.1}
            max={10}
            step={0.1}
            style={{
              width: '100%',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              padding: '8px 12px',
              borderRadius: 6,
              fontSize: 14,
              fontWeight: 600,
            }}
            className="mono"
          />
        </div>

        {/* Pip Value */}
        <div>
          <label style={{ 
            display: 'block', 
            fontSize: 11, 
            color: 'var(--text3)', 
            fontWeight: 600,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            marginBottom: 8,
          }}>
            Pip Value ($)
          </label>
          <select
            value={pipValue}
            onChange={(e) => setPipValue(Number(e.target.value))}
            style={{
              width: '100%',
              background: 'var(--bg3)',
              border: '1px solid var(--border)',
              color: 'var(--text)',
              padding: '8px 12px',
              borderRadius: 6,
              fontSize: 14,
              fontWeight: 600,
              cursor: 'pointer',
            }}
            className="mono"
          >
            <option value={1}>Micro ($1/pip)</option>
            <option value={10}>Standard ($10/pip)</option>
            <option value={100}>Large ($100/pip)</option>
          </select>
        </div>
      </div>

      {/* Results */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr 1fr 1fr',
        gap: 16,
        padding: 16,
        background: 'var(--bg3)',
        borderRadius: 6,
      }}>
        <div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 4 }}>
            Risk Amount
          </div>
          <div className="mono" style={{ fontSize: 16, fontWeight: 600, color: 'var(--cyan)' }}>
            ${riskAmount.toFixed(2)}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 4 }}>
            Strategy Pips
          </div>
          <div className="mono" style={{ 
            fontSize: 16, 
            fontWeight: 600, 
            color: totalPips >= 0 ? 'var(--green)' : 'var(--red)',
          }}>
            {totalPips >= 0 ? '+' : ''}{totalPips.toFixed(1)}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 4 }}>
            Projected Return
          </div>
          <div className="mono" style={{ 
            fontSize: 16, 
            fontWeight: 600, 
            color: projectedReturn >= 0 ? 'var(--green)' : 'var(--red)',
          }}>
            ${projectedReturn >= 0 ? '+' : ''}{projectedReturn.toFixed(2)}
          </div>
        </div>

        <div>
          <div style={{ fontSize: 11, color: 'var(--text3)', marginBottom: 4 }}>
            Return %
          </div>
          <div className="mono" style={{ 
            fontSize: 16, 
            fontWeight: 600, 
            color: projectedReturnPct >= 0 ? 'var(--green)' : 'var(--red)',
          }}>
            {projectedReturnPct >= 0 ? '+' : ''}{projectedReturnPct.toFixed(2)}%
          </div>
        </div>
      </div>

      <div style={{
        marginTop: 12,
        padding: 12,
        background: 'rgba(0, 212, 255, 0.08)',
        border: '1px solid rgba(0, 212, 255, 0.25)',
        borderRadius: 6,
        fontSize: 11,
        color: 'var(--text3)',
        lineHeight: 1.5,
      }}>
        <strong style={{ color: 'var(--cyan)' }}>Note:</strong> This calculator shows hypothetical returns based on historical signal performance. 
        Past performance does not guarantee future results. Always use proper risk management.
      </div>
    </div>
  );
}

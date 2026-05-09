import { useState, useEffect } from 'react';
import { API_BASE_URL } from '../config/constants';
import EquityCurveChart from '../components/performance/EquityCurveChart';
import DrawdownChart from '../components/performance/DrawdownChart';
import MetricsDashboard from '../components/performance/MetricsDashboard';
import PairComparison from '../components/performance/PairComparison';
import RecentTradesList from '../components/performance/RecentTradesList';
import PositionSizeCalculator from '../components/performance/PositionSizeCalculator';

interface PerformanceSummary {
  total_signals: number;
  winning_signals: number;
  losing_signals: number;
  win_rate: number;
  total_pips: number;
  avg_win_pips: number;
  avg_loss_pips: number;
  profit_factor: number;
  max_drawdown_pips: number;
  max_drawdown_pct: number;
  sharpe_ratio: number;
  best_signal_pips: number;
  worst_signal_pips: number;
  avg_signal_duration_hours: number;
}

interface EquityData {
  type: string;
  data: Array<{
    time: string;
    cumulative_pips: number;
    signal_pips: number;
    pair: string;
    direction: string;
  }>;
  pair_filter?: string;
}

interface DrawdownData {
  type: string;
  data: Array<{
    time: string;
    drawdown_pips: number;
    drawdown_pct: number;
  }>;
  pair_filter?: string;
}

interface PairComparisonData {
  type: string;
  pairs: Array<{
    pair: string;
    total_signals: number;
    win_rate: number;
    total_pips: number;
    profit_factor: number;
    sharpe_ratio: number;
  }>;
}

interface RecentSignalsData {
  type: string;
  signals: Array<{
    timestamp: string;
    pair: string;
    direction: string;
    entry: number;
    exit: number;
    pips: number;
    outcome: 'win' | 'loss';
    confidence: number;
  }>;
}

export default function PerformancePage() {
  const [selectedPair, setSelectedPair] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [summary, setSummary] = useState<PerformanceSummary | null>(null);
  const [equityData, setEquityData] = useState<EquityData | null>(null);
  const [drawdownData, setDrawdownData] = useState<DrawdownData | null>(null);
  const [pairComparison, setPairComparison] = useState<PairComparisonData | null>(null);
  const [recentSignals, setRecentSignals] = useState<RecentSignalsData | null>(null);

  useEffect(() => {
    fetchPerformanceData();
  }, [selectedPair]);

  const fetchPerformanceData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const pairParam = selectedPair !== 'all' ? `?pair=${selectedPair}` : '';
      
      const [summaryRes, equityRes, drawdownRes, pairsRes, tradesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/backtest/summary${pairParam}`),
        fetch(`${API_BASE_URL}/api/backtest/equity${pairParam}`),
        fetch(`${API_BASE_URL}/api/backtest/drawdown${pairParam}`),
        fetch(`${API_BASE_URL}/api/backtest/pairs`),
        fetch(`${API_BASE_URL}/api/backtest/trades${pairParam}`),
      ]);

      if (!summaryRes.ok) throw new Error('Failed to load performance summary');
      if (!equityRes.ok) throw new Error('Failed to load equity data');
      if (!drawdownRes.ok) throw new Error('Failed to load drawdown data');
      if (!pairsRes.ok) throw new Error('Failed to load pair comparison');
      if (!tradesRes.ok) throw new Error('Failed to load trades data');

      const [summaryData, equityData, drawdownData, pairsData, tradesData] = await Promise.all([
        summaryRes.json(),
        equityRes.json(),
        drawdownRes.json(),
        pairsRes.json(),
        tradesRes.json(),
      ]);

      setSummary(summaryData);
      setEquityData(equityData);
      setDrawdownData(drawdownData);
      setPairComparison(pairsData);
      setRecentSignals(tradesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load performance data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{
        minHeight: 'calc(100vh - 49px)',
        background: 'var(--bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        color: 'var(--text3)',
      }}>
        <span className="mono" style={{ fontSize: 12 }}>Loading performance data…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: 'calc(100vh - 49px)', background: 'var(--bg)', padding: 40, color: 'var(--red)' }}>
        Error: {error}
      </div>
    );
  }

  // No signals yet — show a friendly empty state
  const hasData = summary && summary.total_signals > 0;

  return (
    <div style={{ minHeight: 'calc(100vh - 49px)', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Header */}
      <div style={{
        padding: '20px 24px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-end',
      }}>
        <div>
          <h1 className="mono" style={{ fontSize: 22, fontWeight: 700, color: 'var(--cyan)', marginBottom: 4 }}>
            Strategy Performance
          </h1>
          <div style={{ fontSize: 13, color: 'var(--text3)' }}>
            Signal quality metrics and analytics
          </div>
        </div>

        {/* Pair Filter */}
        <select
          value={selectedPair}
          onChange={(e) => setSelectedPair(e.target.value)}
          style={{
            background: 'var(--bg3)',
            border: '1px solid var(--border)',
            color: 'var(--text)',
            padding: '7px 28px 7px 12px',
            borderRadius: 6,
            fontSize: 12,
            cursor: 'pointer',
            fontWeight: 600,
            outline: 'none',
          }}
        >
          <option value="all">All Pairs</option>
          <option value="EURUSD">EURUSD</option>
          <option value="GBPUSD">GBPUSD</option>
          <option value="USDJPY">USDJPY</option>
        </select>
      </div>

      {/* Content */}
      <div style={{ padding: '20px 24px' }}>

        {/* Signal Overview — always shown when we have any signals */}
        {hasData && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(6, 1fr)',
            gap: 12,
            marginBottom: 20,
          }}>
            {[
              { label: 'Total Signals', value: summary!.total_signals, color: 'var(--text)' },
              { label: 'BUY', value: (summary as any).buy_signals ?? 0, color: 'var(--green)' },
              { label: 'SELL', value: (summary as any).sell_signals ?? 0, color: 'var(--red)' },
              { label: 'HOLD', value: (summary as any).hold_signals ?? 0, color: 'var(--text3)' },
              { label: 'Avg Confidence', value: `${Math.round(((summary as any).avg_confidence ?? 0) * 100)}%`, color: 'var(--cyan)' },
              { label: 'Win Rate', value: summary!.win_rate > 0 ? `${Math.round(summary!.win_rate * 100)}%` : '—', color: 'var(--green)' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                background: 'var(--bg2)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                padding: '14px 16px',
                textAlign: 'center',
              }}>
                <div className="mono" style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
                <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginTop: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</div>
              </div>
            ))}
          </div>
        )}

        {/* No data yet */}
        {!hasData && (
          <div style={{
            background: 'var(--bg2)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            padding: '48px 24px',
            textAlign: 'center',
            marginBottom: 20,
          }}>
            <div className="mono" style={{ fontSize: 13, color: 'var(--text3)', marginBottom: 8 }}>No signal data yet</div>
            <div style={{ fontSize: 12, color: 'var(--text3)', lineHeight: 1.6 }}>
              Hit <strong style={{ color: 'var(--cyan)' }}>RUN NOW</strong> on the dashboard to generate signals.
            </div>
          </div>
        )}

        {/* Metrics Dashboard */}
        {summary && hasData && <MetricsDashboard summary={summary} />}

        {/* Charts Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 16,
          marginTop: 16,
        }}>
          {equityData && (
            <div style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '14px 16px 16px',
            }}>
              <div className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 14 }}>
                Cumulative Pips
              </div>
              <EquityCurveChart data={equityData} />
            </div>
          )}

          {drawdownData && (
            <div style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: '14px 16px 16px',
            }}>
              <div className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 14 }}>
                Drawdown Analysis
              </div>
              <DrawdownChart data={drawdownData} />
            </div>
          )}
        </div>

        {pairComparison && selectedPair === 'all' && (
          <div style={{ marginTop: 16 }}>
            <PairComparison data={pairComparison} />
          </div>
        )}

        {recentSignals && (
          <div style={{ marginTop: 16 }}>
            <RecentTradesList data={recentSignals} />
          </div>
        )}

        <div style={{ marginTop: 16 }}>
          <PositionSizeCalculator totalPips={summary?.total_pips || 0} />
        </div>
      </div>
    </div>
  );
}

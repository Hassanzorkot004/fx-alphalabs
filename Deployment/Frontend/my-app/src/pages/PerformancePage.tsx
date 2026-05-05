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
        minHeight: '100vh', 
        background: 'var(--bg)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        color: 'var(--text3)',
      }}>
        Loading performance data...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        minHeight: '100vh', 
        background: 'var(--bg)', 
        padding: 40,
        color: 'var(--red)',
      }}>
        Error: {error}
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Header */}
      <div style={{
        background: 'var(--bg1)',
        borderBottom: '1px solid var(--border)',
        padding: '16px 24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <div>
          <h1 className="mono" style={{ fontSize: 20, fontWeight: 600, color: 'var(--amber)', marginBottom: 4 }}>
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
            padding: '8px 16px',
            borderRadius: 6,
            fontSize: 13,
            cursor: 'pointer',
            fontWeight: 600,
          }}
        >
          <option value="all">All Pairs</option>
          <option value="EURUSD">EURUSD</option>
          <option value="GBPUSD">GBPUSD</option>
          <option value="USDJPY">USDJPY</option>
        </select>
      </div>

      {/* Content */}
      <div style={{ padding: 24 }}>
        {/* Metrics Dashboard */}
        {summary && <MetricsDashboard summary={summary} />}

        {/* Charts Grid */}
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: '1fr 1fr', 
          gap: 20, 
          marginTop: 20,
        }}>
          {/* Equity Curve */}
          {equityData && (
            <div style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: 20,
            }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text2)', marginBottom: 16 }}>
                Cumulative Pips
              </h3>
              <EquityCurveChart data={equityData} />
            </div>
          )}

          {/* Drawdown */}
          {drawdownData && (
            <div style={{
              background: 'var(--bg2)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: 20,
            }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, color: 'var(--text2)', marginBottom: 16 }}>
                Drawdown Analysis
              </h3>
              <DrawdownChart data={drawdownData} />
            </div>
          )}
        </div>

        {/* Pair Comparison */}
        {pairComparison && selectedPair === 'all' && (
          <div style={{ marginTop: 20 }}>
            <PairComparison data={pairComparison} />
          </div>
        )}

        {/* Recent Trades */}
        {recentSignals && (
          <div style={{ marginTop: 20 }}>
            <RecentTradesList data={recentSignals} />
          </div>
        )}

        {/* Position Size Calculator */}
        <div style={{ marginTop: 20 }}>
          <PositionSizeCalculator totalPips={summary?.total_pips || 0} />
        </div>
      </div>
    </div>
  );
}

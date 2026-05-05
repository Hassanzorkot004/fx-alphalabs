import { useState, useEffect } from 'react';
import PriceChart from './PriceChart';
import RSIChart from './RSIChart';
import MACDChart from './MACDChart';
import BollingerBandsChart from './BollingerBandsChart';
import RiskChart from './RiskChart';
import AgentConfidenceChart from './AgentConfidenceChart';
import { API_BASE_URL } from '../../config/constants';

interface ChartRendererProps {
  chartCommand: string;  // e.g., "CHART:price:24h" or "CHART:rsi:24h" or "CHART:risk"
  pair: string;
}

export default function ChartRenderer({ chartCommand, pair }: ChartRendererProps) {
  const [chartData, setChartData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchChartData();
  }, [chartCommand, pair]);

  const fetchChartData = async () => {
    setLoading(true);
    setError(null);

    try {
      // Parse chart command: CHART:type:period or CHART:type
      const parts = chartCommand.replace('[', '').replace(']', '').split(':');
      const chartType = parts[1];
      const period = parts[2] || '24h';

      let url = '';

      if (chartType === 'price') {
        url = `${API_BASE_URL}/api/charts/price/${pair}?period=${period}`;
      } else if (chartType === 'rsi' || chartType === 'macd' || chartType === 'bb') {
        url = `${API_BASE_URL}/api/charts/indicator/${pair}/${chartType}?period=${period}`;
      } else if (chartType === 'risk') {
        url = `${API_BASE_URL}/api/charts/risk/${pair}`;
      } else if (chartType === 'agents') {
        url = `${API_BASE_URL}/api/charts/agents/${pair}`;
      } else {
        setError(`Unknown chart type: ${chartType}`);
        setLoading(false);
        return;
      }

      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setChartData(data);
    } catch (err) {
      console.error('Chart fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load chart');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{
        background: 'var(--bg3)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: 32,
        marginTop: 12,
        textAlign: 'center',
      }}>
        <div style={{ fontSize: 12, color: 'var(--text3)' }}>
          Loading chart...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        background: 'var(--red)10',
        border: '1px solid var(--red)40',
        borderRadius: 8,
        padding: 16,
        marginTop: 12,
      }}>
        <div style={{ fontSize: 12, color: 'var(--red)' }}>
          Chart error: {error}
        </div>
      </div>
    );
  }

  if (!chartData) {
    return null;
  }

  // Render appropriate chart based on type
  if (chartData.type === 'price') {
    return <PriceChart data={chartData} />;
  } else if (chartData.type === 'indicator') {
    // Handle different indicator types
    if (chartData.indicator === 'rsi') {
      return <RSIChart data={chartData} />;
    } else if (chartData.indicator === 'macd') {
      return <MACDChart data={chartData} />;
    } else if (chartData.indicator === 'bollinger_bands') {
      return <BollingerBandsChart data={chartData} />;
    }
  } else if (chartData.type === 'risk') {
    return <RiskChart data={chartData} />;
  } else if (chartData.type === 'agent_confidence') {
    return <AgentConfidenceChart data={chartData} />;
  }

  // Fallback for unsupported chart types
  return (
    <div style={{
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      marginTop: 12,
    }}>
      <div style={{ fontSize: 12, color: 'var(--text3)' }}>
        Chart type not yet implemented: {chartData.type} {chartData.indicator ? `(${chartData.indicator})` : ''}
      </div>
    </div>
  );
}

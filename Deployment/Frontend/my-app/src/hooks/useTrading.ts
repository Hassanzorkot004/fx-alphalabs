import { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config/constants';
import type {
  Portfolio,
  VirtualTrade,
  OpenTradePayload,
  CloseTradePayload,
} from '../Types';

function getAuthHeaders() {
  const token = localStorage.getItem('fx_token');

  return {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };
}

export function useTrading() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [trades, setTrades] = useState<VirtualTrade[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openTrades = trades.filter((trade: VirtualTrade) => trade.status === 'OPEN');
  const closedTrades = trades.filter((trade: VirtualTrade) => trade.status === 'CLOSED');

  async function fetchPortfolio() {
    const res = await fetch(`${API_BASE_URL}/api/trading/portfolio`, {
      headers: getAuthHeaders(),
    });

    if (!res.ok) throw new Error('Failed to load portfolio');

    setPortfolio(await res.json());
  }

  async function fetchTrades() {
    const res = await fetch(`${API_BASE_URL}/api/trading/trades`, {
      headers: getAuthHeaders(),
    });

    if (!res.ok) throw new Error('Failed to load trades');

    setTrades(await res.json());
  }

  async function refreshTrading() {
    try {
      setLoading(true);
      setError(null);
      await Promise.all([fetchPortfolio(), fetchTrades()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trading error');
    } finally {
      setLoading(false);
    }
  }

  async function openTrade(payload: OpenTradePayload) {
    const res = await fetch(`${API_BASE_URL}/api/trading/open`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error('Failed to open trade');

    await refreshTrading();
  }

  async function closeTrade(tradeId: number, payload: CloseTradePayload) {
    const res = await fetch(`${API_BASE_URL}/api/trading/close/${tradeId}`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error('Failed to close trade');

    await refreshTrading();
  }

  useEffect(() => {
    refreshTrading();
  }, []);

  return {
    portfolio,
    trades,
    openTrades,
    closedTrades,
    loading,
    error,
    refreshTrading,
    openTrade,
    closeTrade,
  };
}
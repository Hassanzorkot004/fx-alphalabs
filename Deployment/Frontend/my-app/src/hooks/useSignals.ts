import { useState, useEffect, useRef, useCallback } from 'react';
import type { Signal, Stats, CalendarEvent, NewsArticle, Price, WSMessage } from '../Types';
import { WS_URL } from '../config/constants';

interface SignalsState {
  signals: Signal[];
  history: Signal[];
  stats: Stats | null;
  calendar: CalendarEvent[];
  news: NewsArticle[];
  prices: Record<string, Price>;
  connected: boolean;
  lastUpdate: string | null;
  nextCycle: number | null;
}

const INITIAL_STATE: SignalsState = {
  signals: [],
  history: [],
  stats: null,
  calendar: [],
  news: [],
  prices: {},
  connected: false,
  lastUpdate: null,
  nextCycle: null,
};

export function useSignals() {
  const [state, setState] = useState<SignalsState>(INITIAL_STATE);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const reconnectAttempts = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);

      ws.onopen = () => {
        console.log('[WS] Connected');
        reconnectAttempts.current = 0;
        setState(prev => ({ ...prev, connected: true }));
      };

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data);

          if (msg.type === 'full_update') {
            console.log('[WS] Received full_update:', {
              signalCount: msg.signals?.length,
              pairs: msg.signals?.map(s => s.pair),
              hasStats: !!msg.stats,
              statsKeys: msg.stats ? Object.keys(msg.stats) : []
            });
            
            setState(prev => ({
              ...prev,
              signals: msg.signals || prev.signals,
              history: msg.history || prev.history,
              stats: msg.stats || prev.stats,
              calendar: msg.calendar || prev.calendar,
              news: msg.news || prev.news,
              prices: msg.prices || prev.prices,
              lastUpdate: new Date().toISOString(),
              nextCycle: msg.next_cycle || prev.nextCycle,
            }));
          } else if (msg.type === 'price_update') {
            setState(prev => ({
              ...prev,
              prices: { ...prev.prices, ...(msg.prices || {}) },
            }));
          }
        } catch (err) {
          console.error('[WS] Parse error:', err);
        }
      };

      ws.onerror = (err) => {
        console.error('[WS] Error:', err);
      };

      ws.onclose = () => {
        console.log('[WS] Disconnected');
        setState(prev => ({ ...prev, connected: false }));
        wsRef.current = null;

        // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current++;
        
        reconnectTimeoutRef.current = window.setTimeout(() => {
          console.log(`[WS] Reconnecting (attempt ${reconnectAttempts.current})...`);
          connect();
        }, delay);
      };

      wsRef.current = ws;
    } catch (err) {
      console.error('[WS] Connection failed:', err);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return state;
}

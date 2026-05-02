import { useState, useEffect, useRef, useCallback } from 'react';
import type { Signal, Stats, CalendarEvent, NewsArticle, Price, WSMessage, LiveContext } from '../Types';
import { WS_URL } from '../config/constants';

interface SignalsState {
  signals: Signal[];
  history: Signal[];
  stats: Stats | null;
  calendar: CalendarEvent[];
  news: NewsArticle[];
  prices: Record<string, Price>;
  liveContexts: Record<string, LiveContext>;
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
  liveContexts: {},
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
      const token = localStorage.getItem('fx_token');
const wsUrl = token ? `${WS_URL}?token=${encodeURIComponent(token)}` : WS_URL;
const ws = new WebSocket(wsUrl);

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
              hasContexts: !!msg.live_contexts,
              nextCycle: msg.next_cycle,
            });
            
            setState(prev => ({
              ...prev,
              signals: msg.signals || prev.signals,
              history: msg.history || prev.history,
              stats: msg.stats || prev.stats,
              calendar: msg.calendar || prev.calendar,
              news: msg.news || prev.news,
              prices: msg.prices || prev.prices,
              liveContexts: msg.live_contexts || prev.liveContexts,
              lastUpdate: new Date().toISOString(),
              nextCycle: msg.next_cycle ?? prev.nextCycle,
            }));
          } else if (msg.type === 'context_update') {
            // Lightweight update: just prices and live contexts
            console.log('[WS] Received context_update:', {
              priceCount: Object.keys(msg.prices || {}).length,
              contextCount: Object.keys(msg.live_contexts || {}).length,
            });
            setState(prev => ({
              ...prev,
              prices: { ...prev.prices, ...(msg.prices || {}) },
              liveContexts: { ...prev.liveContexts, ...(msg.live_contexts || {}) },
              lastUpdate: msg.timestamp || new Date().toISOString(),
            }));
          } else if (msg.type === 'news_alert') {
            // News spike detected
            console.log('[WS] News alert:', msg);
            // Could show a toast notification here
          } else if (msg.type === 'price_update') {
            // Legacy support
            setState(prev => ({
              ...prev,
              prices: { ...prev.prices, ...(msg.prices || {}) },
            }));
          } else if (msg.type === 'ping') {
            // Ignore ping messages
          } else {
            console.log('[WS] Unknown message type:', msg.type);
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

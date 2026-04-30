import { useState, useEffect, useRef, useCallback } from 'react';
import { WS_URL, RECONNECT_DELAY, ENABLE_DEBUG } from '../config/constants';
import type { Signal, Stats, WSMessage } from '../Types';

interface WSState {
  signals:    Signal[];
  history:    Signal[];
  stats:      Stats | null;
  connected:  boolean;
  lastUpdate: Date | null;
  nextCycle:  number | null;
}

export function useWebSocket(): WSState {
  const [signals,    setSignals]    = useState<Signal[]>([]);
  const [history,    setHistory]    = useState<Signal[]>([]);
  const [stats,      setStats]      = useState<Stats | null>(null);
  const [connected,  setConnected]  = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [nextCycle,  setNextCycle]  = useState<number | null>(null);

  const wsRef           = useRef<WebSocket | null>(null);
  const reconnectTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      if (ENABLE_DEBUG) console.log('[WS] Connecting to', WS_URL);
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (ENABLE_DEBUG) console.log('[WS] Connected successfully');
        setConnected(true);
        if (reconnectTimer.current) {
          clearTimeout(reconnectTimer.current);
          reconnectTimer.current = null;
        }
      };

      ws.onmessage = (e: MessageEvent) => {
        try {
          if (ENABLE_DEBUG) console.log('[WS] Raw message received:', e.data);
          const msg: WSMessage = JSON.parse(e.data as string);
          if (ENABLE_DEBUG) console.log('[WS] Parsed message type:', msg.type);

          if (msg.type === 'signals' && msg.data) {
            setSignals(msg.data);
            setLastUpdate(new Date());
          } else if (msg.type === 'history' && msg.data) {
            setHistory(msg.data);
          } else if (msg.type === 'stats' && msg.data) {
            setStats(msg.data as unknown as Stats);
          } else if (msg.type === 'next_cycle') {
            setNextCycle(msg.seconds_remaining ?? null);
          } else if (msg.type === 'full_update') {
            if (ENABLE_DEBUG) console.log('[WS] Full update received:', {
              signals: msg.signals?.length,
              history: msg.history?.length,
              stats: !!msg.stats
            });
            if (msg.signals)              setSignals(msg.signals);
            if (msg.history)              setHistory(msg.history);
            if (msg.stats)                setStats(msg.stats);
            if (msg.next_cycle !== undefined) setNextCycle(msg.next_cycle);
            setLastUpdate(new Date());
          }
        } catch (err) {
          console.error('[WS] Parse error:', err, 'Raw data:', e.data);
        }
      };

      ws.onclose = (e) => {
        if (ENABLE_DEBUG) console.log('[WS] Connection closed:', e.code, e.reason);
        setConnected(false);
        reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
      };

      ws.onerror = (err) => {
        if (ENABLE_DEBUG) console.error('[WS] Error:', err);
        // Don't close here - let onclose handle reconnection
      };

    } catch (err) {
      console.error('[WS] Connect error:', err);
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connect]);

  // Countdown timer
  useEffect(() => {
    if (nextCycle === null) return;
    const interval = setInterval(() => {
      setNextCycle(prev => (prev !== null && prev > 0 ? prev - 1 : prev));
    }, 1000);
    return () => clearInterval(interval);
  }, [nextCycle]);

  return { signals, history, stats, connected, lastUpdate, nextCycle };
}
/**
 * WhisperAlert.tsx
 *
 * Drop-in notification stack for Market Whisperer alerts.
 *
 * Usage in App.tsx:
 *   import WhisperAlertStack, { useWhisperAlerts } from './components/WhisperAlert';
 *
 *   const { alerts, addAlert, dismiss } = useWhisperAlerts();
 *
 *   // In your WebSocket message handler (useSignals.ts), add:
 *   if (msg.type === 'whisper_alert') { addAlert(msg); }
 *
 *   // In App JSX, just before closing </div>:
 *   <WhisperAlertStack
 *     alerts={alerts}
 *     onDismiss={dismiss}
 *     onAskAlphaBot={(prompt) => alphaBotSendRef.current?.(prompt)}
 *   />
 */

import { useEffect, useRef, useState, useCallback } from 'react';

// ─────────────────────────────────────────────
//  Types — match what the backend sends
// ─────────────────────────────────────────────

export type AlertSeverity = 'ALERT' | 'OPPORTUNITY' | 'WARNING';

export interface WhisperAlertData {
  id: string;               // added client-side
  pair: string;
  severity: AlertSeverity;
  alert_type: string;
  message: string;
  alphabot_prompt: string;
  timestamp: string;
}

interface StackProps {
  alerts: WhisperAlertData[];
  onDismiss: (id: string) => void;
  onAskAlphaBot: (prompt: string) => void;
}

// ─────────────────────────────────────────────
//  Severity config — matches app CSS variables
// ─────────────────────────────────────────────

const CFG = {
  ALERT: {
    border: '1px solid rgba(239,68,68,0.55)',
    glow: '0 0 24px rgba(239,68,68,0.30)',
    accent: '#ef4444',
    accentMuted: 'rgba(239,68,68,0.15)',
    accentHover: 'rgba(239,68,68,0.25)',
    label: '#f87171',
    icon: '🔴',
    tag: 'ALERT',
  },
  OPPORTUNITY: {
    border: '1px solid rgba(34,211,238,0.55)',
    glow: '0 0 24px rgba(34,211,238,0.25)',
    accent: '#22d3ee',
    accentMuted: 'rgba(34,211,238,0.12)',
    accentHover: 'rgba(34,211,238,0.22)',
    label: '#67e8f9',
    icon: '⚡',
    tag: 'OPPORTUNITY',
  },
  WARNING: {
    border: '1px solid rgba(251,191,36,0.55)',
    glow: '0 0 24px rgba(251,191,36,0.25)',
    accent: '#fbbf24',
    accentMuted: 'rgba(251,191,36,0.12)',
    accentHover: 'rgba(251,191,36,0.22)',
    label: '#fcd34d',
    icon: '⚠️',
    tag: 'WARNING',
  },
} as const;

const AUTO_DISMISS_MS = 30_000;

// ─────────────────────────────────────────────
//  Single card
// ─────────────────────────────────────────────

function WhisperCard({
  alert,
  onDismiss,
  onAskAlphaBot,
}: {
  alert: WhisperAlertData;
  onDismiss: () => void;
  onAskAlphaBot: () => void;
}) {
  const cfg = CFG[alert.severity] ?? CFG.WARNING;
  const [progress, setProgress] = useState(100);
  const [mounted, setMounted] = useState(false);
  const [leaving, setLeaving] = useState(false);
  const startRef = useRef(Date.now());

  // Entrance
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 20);
    return () => clearTimeout(t);
  }, []);

  // Progress bar
  useEffect(() => {
    if ('speechSynthesis' in window) {
    const lines = alert.message.split('\n').filter(Boolean);
    const body  = lines.slice(1).join(' ');
    const text  = `${alert.pair}. ${body}`;
    
    const utterance        = new SpeechSynthesisUtterance(text);
    utterance.rate         = 0.9;
    utterance.pitch        = 1.0;
    utterance.volume       = 0.8;
    utterance.lang         = 'en-US';
    
    // Choisir une voix masculine professionnelle si disponible
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      v.name.includes('Google UK English Male') ||
      v.name.includes('Daniel') ||
      v.name.includes('Alex')
    );
    if (preferred) utterance.voice = preferred;
    
    window.speechSynthesis.speak(utterance);
  }







    startRef.current = Date.now();
    const iv = setInterval(() => {
      const pct = Math.max(0, 100 - ((Date.now() - startRef.current) / AUTO_DISMISS_MS) * 100);
      setProgress(pct);
    }, 150);
    return () => clearInterval(iv);
  }, []);

  // Auto-dismiss
  useEffect(() => {
    const t = setTimeout(() => handleDismiss(), AUTO_DISMISS_MS);
    return () => clearTimeout(t);
  }, []);

  const handleDismiss = useCallback(() => {
      window.speechSynthesis.cancel();

    setLeaving(true);
    setTimeout(onDismiss, 280);
  }, [onDismiss]);

  const handleAsk = useCallback(() => {
    onAskAlphaBot();
    handleDismiss();
  }, [onAskAlphaBot, handleDismiss]);

  // Parse message lines
  const lines = alert.message.split('\n').filter(Boolean);
  // First line: "🔴 ALERT — 14:32 UTC" → extract just the time part
  const headerLine = lines[0] ?? '';
  const timeMatch = headerLine.match(/(\d{2}:\d{2} UTC)/);
  const timeStr = timeMatch ? timeMatch[1] : '';
  const body = lines.slice(1).join(' ');

  const transitionStyle: React.CSSProperties = {
    transform: mounted && !leaving ? 'translateX(0) scale(1)' : 'translateX(110%) scale(0.95)',
    opacity: mounted && !leaving ? 1 : 0,
    transition: 'transform 0.28s cubic-bezier(0.34,1.56,0.64,1), opacity 0.25s ease',
  };

  return (
    <div style={{
      position: 'relative',
      overflow: 'hidden',
      width: 360,
      maxWidth: 'calc(100vw - 2rem)',
      borderRadius: 12,
      border: cfg.border,
      boxShadow: cfg.glow,
      background: 'rgba(10,10,15,0.94)',
      backdropFilter: 'blur(12px)',
      willChange: 'transform, opacity',
      ...transitionStyle,
    }}>
      {/* Top accent bar */}
      <div style={{
        position: 'absolute',
        top: 0, left: 0, right: 0,
        height: 2,
        background: cfg.accent,
      }} />

      {/* Progress bar */}
      <div style={{
        position: 'absolute',
        bottom: 0, left: 0,
        height: 2,
        width: `${progress}%`,
        background: `${cfg.accent}80`,
        transition: 'width 0.15s linear',
      }} />

      <div style={{ padding: '14px 14px 16px' }}>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
            <span style={{ fontSize: 15, lineHeight: 1, flexShrink: 0 }}>{cfg.icon}</span>
            <div style={{ minWidth: 0 }}>
              <div className="mono" style={{
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: '0.1em',
                color: cfg.label,
                textTransform: 'uppercase',
              }}>
                {cfg.tag}
              </div>
              {timeStr && (
                <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginTop: 1 }}>
                  {timeStr}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
            {/* Pair badge */}
            <span className="mono" style={{
              fontSize: 10,
              fontWeight: 600,
              padding: '2px 7px',
              borderRadius: 5,
              background: 'var(--bg3, rgba(255,255,255,0.06))',
              border: '1px solid var(--border, rgba(255,255,255,0.1))',
              color: 'var(--text2, #ccc)',
            }}>
              {alert.pair}
            </span>
            {/* Dismiss X */}
            <button
              onClick={handleDismiss}
              style={{
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                color: 'var(--text3, #666)',
                fontSize: 14,
                lineHeight: 1,
                padding: '2px 4px',
                transition: 'color 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.color = 'var(--text, #eee)')}
              onMouseLeave={e => (e.currentTarget.style.color = 'var(--text3, #666)')}
              aria-label="Dismiss"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Body text */}
        {body && (
          <p style={{
            fontSize: 12,
            lineHeight: 1.55,
            color: 'var(--text2, #ccc)',
            margin: '0 0 12px',
            fontWeight: 300,
          }}>
            {body}
          </p>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={handleAsk}
            style={{
              flex: 1,
              padding: '6px 10px',
              borderRadius: 7,
              border: `1px solid ${cfg.accent}60`,
              background: cfg.accentMuted,
              color: cfg.label,
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.15s',
              fontFamily: 'inherit',
            }}
            onMouseEnter={e => (e.currentTarget.style.background = cfg.accentHover)}
            onMouseLeave={e => (e.currentTarget.style.background = cfg.accentMuted)}
          >
            Ask AlphaBot →
          </button>
          <button
            onClick={handleDismiss}
            style={{
              padding: '6px 10px',
              borderRadius: 7,
              border: '1px solid var(--border, rgba(255,255,255,0.1))',
              background: 'transparent',
              color: 'var(--text3, #666)',
              fontSize: 11,
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'color 0.15s, border-color 0.15s',
              fontFamily: 'inherit',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.color = 'var(--text, #eee)';
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.25)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.color = 'var(--text3, #666)';
              e.currentTarget.style.borderColor = 'var(--border, rgba(255,255,255,0.1))';
            }}
          >
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────
//  Stack — fixed top-right, max 4
// ─────────────────────────────────────────────

export default function WhisperAlertStack({ alerts, onDismiss, onAskAlphaBot }: StackProps) {
  const visible = alerts.slice(-4);

  return (
    <div
      style={{
        position: 'fixed',
        top: 16,
        right: 16,
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        alignItems: 'flex-end',
        pointerEvents: 'none',
      }}
      aria-live="polite"
      aria-label="Market alerts"
    >
      {visible.map(alert => (
        <div key={alert.id} style={{ pointerEvents: 'auto' }}>
          <WhisperCard
            alert={alert}
            onDismiss={() => onDismiss(alert.id)}
            onAskAlphaBot={() => onAskAlphaBot(alert.alphabot_prompt)}
          />
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────
//  Hook — use in App.tsx
// ─────────────────────────────────────────────

let _counter = 0;

export function useWhisperAlerts() {
  const [alerts, setAlerts] = useState<WhisperAlertData[]>([]);

  const addAlert = useCallback((raw: Omit<WhisperAlertData, 'id'>) => {
    const id = `whisper-${Date.now()}-${++_counter}`;
    setAlerts(prev => [...prev, { ...raw, id }]);
  }, []);

  const dismiss = useCallback((id: string) => {
    setAlerts(prev => prev.filter(a => a.id !== id));
  }, []);

  return { alerts, addAlert, dismiss };
}
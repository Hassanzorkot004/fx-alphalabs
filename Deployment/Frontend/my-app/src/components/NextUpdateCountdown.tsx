import { useState, useEffect } from 'react';

interface NextUpdateCountdownProps {
  nextCycleSeconds: number | null;
}

export default function NextUpdateCountdown({ nextCycleSeconds }: NextUpdateCountdownProps) {
  const [remaining, setRemaining] = useState(nextCycleSeconds || 0);

  useEffect(() => {
    if (nextCycleSeconds !== null) {
      setRemaining(nextCycleSeconds);
    }
  }, [nextCycleSeconds]);

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(prev => Math.max(0, prev - 1));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  if (remaining <= 0) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '6px 12px',
        background: 'var(--amber)20',
        border: '1px solid var(--amber)40',
        borderRadius: 6,
      }}>
        <div style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: 'var(--amber)',
        }}
        className="animate-pulse-dot"
        />
        <span className="mono" style={{ fontSize: 11, color: 'var(--amber)', fontWeight: 500 }}>
          Updating signals...
        </span>
      </div>
    );
  }

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const progress = nextCycleSeconds ? ((nextCycleSeconds - remaining) / nextCycleSeconds) * 100 : 0;

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '6px 12px',
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 6,
    }}>
      <span className="mono" style={{ fontSize: 11, color: 'var(--text3)' }}>
        Next update in
      </span>
      <span className="mono" style={{ fontSize: 12, color: 'var(--text)', fontWeight: 600 }}>
        {minutes}:{seconds.toString().padStart(2, '0')}
      </span>
      <div style={{
        width: 60,
        height: 4,
        background: 'var(--bg4)',
        borderRadius: 2,
        overflow: 'hidden',
      }}>
        <div style={{
          height: '100%',
          width: `${progress}%`,
          background: 'linear-gradient(90deg, var(--amber), var(--amber)80)',
          transition: 'width 1s linear',
        }} />
      </div>
    </div>
  );
}

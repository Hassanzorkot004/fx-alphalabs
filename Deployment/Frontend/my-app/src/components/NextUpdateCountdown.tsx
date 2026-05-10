import { useState, useEffect } from 'react';

interface NextUpdateCountdownProps {
  nextCycleSeconds: number | null;
}

export default function NextUpdateCountdown({ nextCycleSeconds }: NextUpdateCountdownProps) {
  const [remaining, setRemaining] = useState(nextCycleSeconds || 0);

  useEffect(() => {
    if (nextCycleSeconds !== null) setRemaining(nextCycleSeconds);
  }, [nextCycleSeconds]);

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(prev => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  if (remaining <= 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <div style={{
          width: 5,
          height: 5,
          borderRadius: '50%',
          background: 'var(--cyan)',
        }} className="animate-pulse-dot" />
        <span className="mono" style={{ fontSize: 11, color: 'var(--cyan)', fontWeight: 600 }}>
          Updating…
        </span>
      </div>
    );
  }

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>AGN</span>
      <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', letterSpacing: '0.02em' }}>
        {minutes}:{seconds.toString().padStart(2, '0')}
      </span>
    </div>
  );
}

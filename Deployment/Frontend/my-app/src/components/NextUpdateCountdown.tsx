import { useState, useEffect } from 'react';

export default function NextUpdateCountdown({ nextCycleSeconds }: { nextCycleSeconds: number | null }) {
  const [remaining, setRemaining] = useState(nextCycleSeconds || 0);

  useEffect(() => { if (nextCycleSeconds !== null) setRemaining(nextCycleSeconds); }, [nextCycleSeconds]);

  useEffect(() => {
    const iv = setInterval(() => setRemaining(p => Math.max(0, p - 1)), 1000);
    return () => clearInterval(iv);
  }, []);

  const m = Math.floor(remaining / 60);
  const s = remaining % 60;
  const pct = nextCycleSeconds ? ((nextCycleSeconds - remaining) / nextCycleSeconds) * 100 : 0;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '4px 10px', background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 6 }}>
      <span className="mono" style={{ fontSize: 9, color: 'var(--text3)' }}>NEXT</span>
      <span className="mono" style={{ fontSize: 11, color: 'var(--cyan)', fontWeight: 600 }}>
        {m}:{s.toString().padStart(2, '0')}
      </span>
      <div className="progress-track" style={{ width: 50 }}>
        <div className="progress-fill" style={{ width: `${pct}%`, background: 'var(--cyan)' }} />
      </div>
    </div>
  );
}
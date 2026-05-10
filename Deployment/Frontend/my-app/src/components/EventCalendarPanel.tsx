import { useState } from 'react';
import type { CalendarEvent } from '../Types';

export default function EventCalendarPanel({ events, selectedPair, onEventClick }: {
  events: CalendarEvent[]; selectedPair?: string; onEventClick?: (e: CalendarEvent) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const filtered = selectedPair ? events.filter(e => e.pairs_affected.includes(selectedPair.replace('=X', ''))) : events;
  const upcoming = filtered.filter(e => e.status !== 'passed').slice(0, 8);

  return (
    <div style={{
      padding: 14, maxHeight: collapsed ? 40 : 320, overflow: 'hidden', transition: 'max-height 0.3s ease',
      background: 'var(--bg2)', border: '1px solid var(--border)', borderRadius: 12,
      backdropFilter: 'blur(16px)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: collapsed ? 0 : 10, cursor: 'pointer' }} onClick={() => setCollapsed(!collapsed)}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 600, color: '#ce93d8', letterSpacing: '1px' }}>CALENDAR</span>
        <span style={{ fontSize: 10, color: 'var(--text3)' }}>{upcoming.length} events {collapsed ? '▸' : '▾'}</span>
      </div>
      {!collapsed && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflowY: 'auto', maxHeight: 260 }}>
          {upcoming.map((e, i) => (
            <div key={i} onClick={() => onEventClick?.(e)}
              style={{ padding: '8px 10px', background: 'rgba(10,20,38,0.8)', border: '1px solid rgba(179,136,255,0.06)', borderRadius: 6, cursor: 'pointer', transition: 'all 0.15s ease' }}
              onMouseEnter={el => { el.currentTarget.style.borderColor = '#ce93d8'; el.currentTarget.style.background = 'rgba(179,136,255,0.04)'; }}
              onMouseLeave={el => { el.currentTarget.style.borderColor = 'rgba(179,136,255,0.06)'; el.currentTarget.style.background = 'rgba(10,20,38,0.8)'; }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                <div style={{ width: 5, height: 5, borderRadius: '50%', background: e.impact === 'high' ? 'var(--sell)' : 'var(--amber)' }} />
                <span className="mono" style={{ fontSize: 8, color: 'var(--text3)' }}>{e.currency}</span>
                <span className="mono" style={{ fontSize: 8, color: 'var(--text3)', marginLeft: 'auto' }}>in {e.hours_until?.toFixed(1)}h</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text)' }}>{e.event}</div>
              {(e.forecast || e.previous) && (
                <div style={{ fontSize: 9, color: 'var(--text3)', marginTop: 2 }}>
                  F: {e.forecast} · P: {e.previous}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
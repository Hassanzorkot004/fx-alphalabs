import type { CalendarEvent } from '../Types';

interface EventCalendarPanelProps {
  events: CalendarEvent[];
  selectedPair?: string;
}

export default function EventCalendarPanel({ events, selectedPair }: EventCalendarPanelProps) {
  // Filter to events affecting selected pair if provided
  const filteredEvents = selectedPair
    ? events.filter(e => e.pairs_affected.includes(selectedPair.replace('=X', '')))
    : events;

  const upcomingEvents = filteredEvents.filter(e => e.status !== 'passed').slice(0, 8);

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 16,
      maxHeight: 400,
      overflowY: 'auto',
    }}>
      <div className="mono" style={{ fontSize: 12, fontWeight: 600, color: 'var(--text3)', marginBottom: 12 }}>
        ECONOMIC CALENDAR
      </div>

      {upcomingEvents.length === 0 ? (
        <div style={{ color: 'var(--text3)', fontSize: 12 }}>
          No upcoming events
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {upcomingEvents.map((event, idx) => (
            <EventItem key={idx} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}

function EventItem({ event }: { event: CalendarEvent }) {
  const impactColor = 
    event.impact === 'high' ? 'var(--red)' :
    event.impact === 'medium' ? 'var(--amber)' :
    'var(--text3)';

  const hoursUntil = event.hours_until || 0;
  const isPassed = event.status === 'passed';

  return (
    <div style={{
      padding: 10,
      background: 'var(--bg3)',
      border: '1px solid var(--border)',
      borderRadius: 6,
      opacity: isPassed ? 0.5 : 1,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <div style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: impactColor,
        }} />
        <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', textTransform: 'uppercase' }}>
          {event.currency}
        </div>
        <div className="mono" style={{ fontSize: 10, color: 'var(--text3)', marginLeft: 'auto' }}>
          {isPassed ? 'Passed' : `in ${Math.abs(hoursUntil).toFixed(1)}h`}
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.4 }}>
        {event.event}
      </div>
      {(event.forecast || event.previous) && (
        <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 10, color: 'var(--text3)' }}>
          {event.forecast && <span>Forecast: {event.forecast}</span>}
          {event.previous && <span>Previous: {event.previous}</span>}
        </div>
      )}
    </div>
  );
}

import type { CalendarEvent } from '../Types';

interface EventCalendarPanelProps {
  events: CalendarEvent[];
  selectedPair?: string;
  onEventClick?: (event: CalendarEvent) => void;
}

export default function EventCalendarPanel({ events, selectedPair, onEventClick }: EventCalendarPanelProps) {
  const filteredEvents = selectedPair
    ? events.filter(e => e.pairs_affected.includes(selectedPair.replace('=X', '')))
    : events;

  const displayEvents = filteredEvents.slice(0, 8);

  return (
    <div style={{
      background: 'var(--bg2)',
      border: '1px solid var(--border)',
      borderRadius: 8,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        background: 'var(--bg3)',
      }}>
        <span className="mono" style={{ fontSize: 10, fontWeight: 700, color: 'var(--text3)', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
          Calendar
        </span>
        <span className="mono" style={{ fontSize: 10, color: 'var(--text3)' }}>
          {displayEvents.filter(e => e.status !== 'passed').length} event{displayEvents.filter(e => e.status !== 'passed').length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Events */}
      <div style={{ maxHeight: 320, overflowY: 'auto' }}>
        {displayEvents.length === 0 ? (
          <div style={{ padding: '20px 16px', color: 'var(--text3)', fontSize: 12, textAlign: 'center' }}>
            No upcoming events
          </div>
        ) : (
          displayEvents.map((event, idx) => (
            <EventItem
              key={idx}
              event={event}
              onClick={onEventClick}
              isLast={idx === displayEvents.length - 1}
            />
          ))
        )}
      </div>
    </div>
  );
}

function EventItem({
  event,
  onClick,
  isLast,
}: {
  event: CalendarEvent;
  onClick?: (event: CalendarEvent) => void;
  isLast: boolean;
}) {
  const impactColor =
    event.impact === 'high'   ? 'var(--red)'   :
    event.impact === 'medium' ? '#f59e0b'       : 'var(--text3)';

  const isPassed = event.status === 'passed';
  const hoursUntil = event.hours_until || 0;

  return (
    <div
      onClick={() => onClick?.(event)}
      title="Click to ask AlphaBot about this"
      style={{
        padding: '10px 16px',
        borderBottom: isLast ? 'none' : '1px solid var(--border)',
        cursor: 'pointer',
        opacity: isPassed ? 0.45 : 1,
        transition: 'background 0.12s ease',
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
      }}
      onMouseEnter={e => { if (!isPassed) (e.currentTarget as HTMLElement).style.background = 'var(--bg3)'; }}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'transparent'}
    >
      {/* Impact dot */}
      <div style={{
        width: 6,
        height: 6,
        borderRadius: '50%',
        background: impactColor,
        flexShrink: 0,
        marginTop: 5,
      }} />

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <span className="mono" style={{ fontSize: 10, fontWeight: 600, color: 'var(--text2)' }}>
            {event.currency}
          </span>
          {(event.forecast || event.previous) && (
            <span style={{ fontSize: 10, color: 'var(--text3)' }}>
              {event.forecast && `F: ${event.forecast}`}
              {event.forecast && event.previous && ' · '}
              {event.previous && `P: ${event.previous}`}
            </span>
          )}
        </div>
        <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.4 }}>
          {event.event}
        </div>
      </div>

      {/* Time */}
      <span className="mono" style={{ fontSize: 10, color: isPassed ? 'var(--text3)' : impactColor, flexShrink: 0, paddingTop: 2 }}>
        {isPassed ? 'Passed' : `in ${Math.abs(hoursUntil).toFixed(1)}h`}
      </span>
    </div>
  );
}

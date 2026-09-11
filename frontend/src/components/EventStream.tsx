import { useEffect, useRef } from 'react';
import { WsEvent } from '../types';
import { format } from 'date-fns';

const EVENT_COLOR: Record<string, string> = {
  REQUEST_COMPLETED: 'success',
  RECOVERY_COMPLETED: 'success',
  ROBOT_CONNECTED: 'info',
  REQUEST_RECEIVED: 'info',
  REQUEST_QUEUED: 'info',
  REQUEST_SCHEDULED: 'info',
  AGENT_DECISION: 'info',
  REQUEST_STARTED: 'info',
  RESOURCE_UPDATED: '',
  REQUEST_FAILED: 'error',
  ROBOT_DISCONNECTED: 'warn',
  RETRY_STARTED: 'warn',
  FALLBACK_SELECTED: 'warn',
};

interface Props {
  events: WsEvent[];
}

export default function EventStream({ events }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events.length]);

  const displayEvents = events.filter(e => e.type !== 'RESOURCE_UPDATED').slice(0, 80);

  return (
    <div className="panel h-full" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <span className="panel-title">System Events</span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          LIVE
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 16px' }}>
        {displayEvents.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 11, padding: '8px 0' }}>
            Awaiting events…
          </div>
        ) : (
          [...displayEvents].reverse().map((e, i) => {
            const cls = EVENT_COLOR[e.type] || '';
            const ts = (() => {
              try { return format(new Date(e.timestamp), 'HH:mm:ss'); }
              catch { return '--:--:--'; }
            })();
            return (
              <div key={i} className="event-row animate-in">
                <span className="event-time">{ts}</span>
                <span className={`event-msg ${cls}`}>
                  {e.message || `${e.type}${e.request_id ? ` · ${e.request_id}` : ''}`}
                </span>
              </div>
            );
          })
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

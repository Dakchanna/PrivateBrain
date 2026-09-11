import { Robot, AIRequest } from '../types';
import { format } from 'date-fns';

const STATUS_DOT: Record<string, string> = {
  ONLINE: 'dot-online', IDLE: 'dot-idle', PROCESSING: 'dot-processing',
  OFFLINE: 'dot-offline', ERROR: 'dot-error',
};

interface Props {
  robot: Robot | null;
  requests: AIRequest[];
  onClose: () => void;
  onSelectRequest: (r: AIRequest) => void;
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid var(--bg-border)' }}>
      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontSize: 11, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{value ?? '—'}</span>
    </div>
  );
}

export default function RobotDrawer({ robot, requests, onClose, onSelectRequest }: Props) {
  const successRate = robot && robot.total_requests > 0
    ? ((robot.success_count / robot.total_requests) * 100).toFixed(1)
    : '—';

  return (
    <div className={`drawer ${robot ? 'open' : ''}`}>
      {robot && (
        <>
          <div className="drawer-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span className={`dot ${STATUS_DOT[robot.status] || 'dot-offline'}`} />
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-mono)' }}>{robot.robot_id}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{robot.name || 'Unnamed robot'}</div>
              </div>
            </div>
            <button className="drawer-close" onClick={onClose}>✕</button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
            {/* Status */}
            <div style={{
              padding: '10px 14px', marginBottom: 16,
              background: 'var(--bg-surface)',
              borderRadius: 'var(--radius)',
              border: '1px solid var(--bg-border)',
              fontSize: 12, color: 'var(--text-secondary)',
            }}>
              <span className={`dot ${STATUS_DOT[robot.status] || 'dot-offline'}`} style={{ marginRight: 8 }} />
              {robot.status}
              {robot.last_seen && (
                <span style={{ float: 'right', color: 'var(--text-muted)', fontSize: 10 }}>
                  {format(new Date(robot.last_seen), 'HH:mm:ss')}
                </span>
              )}
            </div>

            {/* Stats */}
            <div style={{ marginBottom: 16 }}>
              <Row label="Total Requests" value={robot.total_requests} />
              <Row label="Successful" value={<span style={{ color: 'var(--green)' }}>{robot.success_count}</span>} />
              <Row label="Failed" value={<span style={{ color: 'var(--red)' }}>{robot.failure_count}</span>} />
              <Row label="Success Rate" value={`${successRate}%`} />
              <Row label="Avg Latency" value={`${robot.avg_latency_ms.toFixed(0)}ms`} />
              <Row label="Registered" value={format(new Date(robot.created_at), 'yyyy-MM-dd HH:mm')} />
            </div>

            {/* Recent requests */}
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
              Recent Requests
            </div>
            {requests.length === 0 ? (
              <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>No requests yet.</div>
            ) : (
              requests.slice(0, 10).map(r => (
                <div key={r.request_id}
                  onClick={() => onSelectRequest(r)}
                  style={{
                    padding: '8px 10px', marginBottom: 4,
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--bg-border)',
                    borderRadius: 'var(--radius)',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s',
                  }}
                  onMouseOver={e => (e.currentTarget.style.borderColor = 'var(--accent)')}
                  onMouseOut={e => (e.currentTarget.style.borderColor = 'var(--bg-border)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--accent)' }}>{r.request_id}</span>
                    <span className={`status-badge status-${r.status.toLowerCase()}`}>{r.status}</span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    {r.task_type.replace(/_/g, ' ')} · {r.priority}
                    {r.latency_ms ? ` · ${r.latency_ms.toFixed(0)}ms` : ''}
                  </div>
                </div>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

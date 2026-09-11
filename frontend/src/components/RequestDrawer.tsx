import { RequestDetail } from '../types';
import { format } from 'date-fns';

interface Props {
  request: RequestDetail | null;
  onClose: () => void;
}

const LIFECYCLE_STEPS = [
  'RECEIVED', 'VALIDATED', 'QUEUED', 'SCHEDULED',
  'PROCESSING', 'COMPLETED',
];

const FAILURE_STEPS = [
  'RECEIVED', 'VALIDATED', 'QUEUED', 'SCHEDULED',
  'PROCESSING', 'ERROR', 'RETRYING', 'RECOVERING', 'COMPLETED',
];

function getStepIcon(step: string, events: string[], currentStatus: string): 'done' | 'active' | 'failed' | 'pending' {
  const occurred = events.includes(step);
  if (occurred || LIFECYCLE_STEPS.indexOf(step) <= LIFECYCLE_STEPS.indexOf(currentStatus)) {
    if (step === 'ERROR' || step === 'FAILED') return 'failed';
    if (step === currentStatus && !['COMPLETED', 'FAILED', 'ERROR'].includes(currentStatus)) return 'active';
    return 'done';
  }
  return 'pending';
}

export default function RequestDrawer({ request, onClose }: Props) {
  if (!request) return <div className={`drawer`} />;

  const eventTypes = request.events.map(e => e.event);
  const hasFailure = ['FAILED', 'ERROR', 'RETRYING', 'RECOVERING'].includes(request.status);
  const steps = hasFailure ? FAILURE_STEPS : LIFECYCLE_STEPS;

  return (
    <div className={`drawer ${request ? 'open' : ''}`}>
      <div className="drawer-header">
        <div>
          <div style={{ fontSize: 12, fontFamily: 'var(--font-mono)', color: 'var(--accent)' }}>
            {request.request_id}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
            {request.robot_id} · {request.task_type.replace(/_/g, ' ')}
          </div>
        </div>
        <button className="drawer-close" onClick={onClose}>✕</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px' }}>
        {/* Header badges */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
          <span className={`badge badge-${request.priority}`}>{request.priority}</span>
          <span className={`status-badge status-${request.status.toLowerCase()}`}>{request.status}</span>
          {request.retry_count > 0 && (
            <span style={{ fontSize: 10, color: 'var(--purple)', fontFamily: 'var(--font-mono)' }}>
              retry ×{request.retry_count}
            </span>
          )}
        </div>

        {/* Request lifecycle */}
        <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12 }}>
          Lifecycle
        </div>
        <div style={{ marginBottom: 20 }}>
          {steps.map((step, i) => {
            const icon = getStepIcon(step, eventTypes, request.status);
            const matchingEvent = request.events.find(e => e.event === step);
            return (
              <div key={step}>
                <div className="lifecycle-step">
                  <div className={`lifecycle-icon ${icon}`}>
                    {icon === 'done' ? '✓' : icon === 'failed' ? '✗' : icon === 'active' ? '●' : '○'}
                  </div>
                  <div>
                    <div style={{ fontSize: 11, color: icon === 'pending' ? 'var(--text-muted)' : 'var(--text-primary)', fontWeight: icon === 'active' ? 600 : 400 }}>
                      {step}
                    </div>
                    {matchingEvent && (
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                        {matchingEvent.message} · {format(new Date(matchingEvent.timestamp), 'HH:mm:ss')}
                      </div>
                    )}
                  </div>
                </div>
                {i < steps.length - 1 && <div className="lifecycle-connector" />}
              </div>
            );
          })}
        </div>

        {/* Agent decisions */}
        {request.agent_decisions.length > 0 && (
          <>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8 }}>
              Agent Decisions
            </div>
            {request.agent_decisions.map((d, i) => (
              <div key={i} style={{
                padding: '8px 10px', marginBottom: 6,
                background: 'var(--bg-surface)',
                border: '1px solid var(--bg-border)',
                borderLeft: '2px solid var(--accent)',
                borderRadius: 'var(--radius)',
              }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent)', fontFamily: 'var(--font-mono)' }}>
                  {d.action}
                </div>
                {d.model && <div style={{ fontSize: 10, color: 'var(--text-secondary)' }}>Model: {d.model}</div>}
                {d.reason && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 3 }}>{d.reason}</div>}
                <div style={{ fontSize: 9, color: 'var(--text-muted)', marginTop: 4 }}>
                  {format(new Date(d.timestamp), 'HH:mm:ss')}
                </div>
              </div>
            ))}
          </>
        )}

        {/* Result */}
        {request.result && (
          <>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8, marginTop: 12 }}>
              Inference Result
            </div>
            <div style={{
              padding: '10px', background: 'var(--bg-surface)',
              border: '1px solid var(--bg-border)',
              borderLeft: `2px solid ${request.result.is_fallback ? 'var(--yellow)' : 'var(--green)'}`,
              borderRadius: 'var(--radius)',
            }}>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6, fontFamily: 'var(--font-mono)' }}>
                {request.result.model} {request.result.is_fallback && '(fallback)'}
                {request.result.confidence !== null && ` · conf: ${(request.result.confidence * 100).toFixed(1)}%`}
                {` · ${request.result.processing_time_ms.toFixed(0)}ms`}
              </div>
              <pre style={{
                fontSize: 9, color: 'var(--text-secondary)',
                fontFamily: 'var(--font-mono)', whiteSpace: 'pre-wrap',
                wordBreak: 'break-all', maxHeight: 160, overflowY: 'auto',
              }}>
                {JSON.stringify(request.result.data, null, 2)}
              </pre>
            </div>
          </>
        )}

        {/* Failure reason */}
        {request.failure_reason && (
          <div style={{
            marginTop: 12, padding: '10px', background: 'rgba(255,71,87,0.08)',
            border: '1px solid rgba(255,71,87,0.25)', borderRadius: 'var(--radius)',
          }}>
            <div style={{ fontSize: 10, color: 'var(--red)', fontWeight: 600, marginBottom: 4 }}>FAILURE REASON</div>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{request.failure_reason}</div>
          </div>
        )}

        {/* Timing */}
        <div style={{ marginTop: 16, fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          <div>Created: {format(new Date(request.created_at), 'HH:mm:ss.SSS')}</div>
          {request.started_at && <div>Started: {format(new Date(request.started_at), 'HH:mm:ss.SSS')}</div>}
          {request.completed_at && <div>Completed: {format(new Date(request.completed_at), 'HH:mm:ss.SSS')}</div>}
          {request.latency_ms && <div>Total latency: {request.latency_ms.toFixed(0)}ms</div>}
        </div>
      </div>
    </div>
  );
}

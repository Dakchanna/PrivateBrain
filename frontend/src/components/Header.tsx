import { SystemMetrics } from '../types';

interface Props {
  connected: boolean;
  metrics: SystemMetrics | null;
}

export default function Header({ connected, metrics }: Props) {
  return (
    <header style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '0 16px', height: '48px',
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--bg-border)',
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: 28, height: 28, borderRadius: 6,
          background: 'linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 700, color: '#000',
        }}>PB</div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, letterSpacing: '0.05em', color: 'var(--text-primary)' }}>
            PRIVATEBRAIN
          </div>
          <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
            Robotics AI Command Center
          </div>
        </div>
      </div>

      {/* Center — quick stats */}
      {metrics && (
        <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
          {[
            { label: 'ACTIVE', value: metrics.active_requests, color: 'var(--yellow)' },
            { label: 'QUEUED', value: metrics.queued_requests, color: 'var(--accent)' },
            { label: 'DONE', value: metrics.completed_requests, color: 'var(--green)' },
            { label: 'FAILED', value: metrics.failed_requests, color: 'var(--red)' },
          ].map(s => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-mono)', color: s.color }}>
                {s.value}
              </div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Right — WS status */}
      <div className={`ws-indicator ${connected ? 'ws-connected' : 'ws-disconnected'}`}>
        <span className="dot" style={{
          background: connected ? 'var(--green)' : 'var(--red)',
          boxShadow: connected ? '0 0 6px var(--green)' : 'none',
          animation: connected ? 'pulse 2s infinite' : 'none',
        }} />
        {connected ? 'LIVE' : 'DISCONNECTED'}
      </div>
    </header>
  );
}

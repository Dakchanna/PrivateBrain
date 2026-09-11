import { Robot, WsEvent } from '../types';

const STATUS_DOT: Record<string, string> = {
  ONLINE: 'dot-online', IDLE: 'dot-idle', PROCESSING: 'dot-processing',
  OFFLINE: 'dot-offline', ERROR: 'dot-error',
};

interface Props {
  robots: Robot[];
  loading: boolean;
  selected?: string;
  onSelect: (r: Robot) => void;
  wsEvents: WsEvent[];
}

export default function RobotFleet({ robots, loading, selected, onSelect, wsEvents }: Props) {
  return (
    <div className="panel h-full" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <span className="panel-title">Robot Fleet</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {robots.length} reg.
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {loading && robots.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 11, padding: '8px', textAlign: 'center' }}>
            Connecting…
          </div>
        ) : robots.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 11, padding: '12px 8px', textAlign: 'center', lineHeight: 1.8 }}>
            No robots registered.<br />
            Use the mock_robot/<br />client to register.
          </div>
        ) : (
          robots.map(robot => (
            <div
              key={robot.robot_id}
              className={`robot-node ${selected === robot.robot_id ? 'selected' : ''}`}
              onClick={() => onSelect(robot)}
            >
              <span className={`dot ${STATUS_DOT[robot.status] || 'dot-offline'}`} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="robot-id">{robot.robot_id}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  {robot.status} · {robot.total_requests} req
                </div>
              </div>
              {robot.status === 'PROCESSING' && (
                <div style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'var(--yellow)', animation: 'pulse 1s infinite',
                }} />
              )}
            </div>
          ))
        )}
      </div>

      {/* Mini legend */}
      <div style={{
        padding: '8px 12px',
        borderTop: '1px solid var(--bg-border)',
        display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        {[
          ['ONLINE', 'dot-online'], ['PROCESSING', 'dot-processing'],
          ['IDLE', 'dot-idle'], ['OFFLINE', 'dot-offline'],
        ].map(([label, cls]) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: 'var(--text-muted)' }}>
            <span className={`dot ${cls}`} style={{ width: 6, height: 6 }} />
            {label}
          </div>
        ))}
      </div>
    </div>
  );
}

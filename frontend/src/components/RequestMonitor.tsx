import { AIRequest, WsEvent } from '../types';

function priorityClass(p: string) {
  return `badge badge-${p.toLowerCase()}`;
}
function statusClass(s: string) {
  return `status-badge status-${s.toLowerCase()}`;
}

function taskLabel(t: string) {
  return t === 'object_detection' ? 'Obj Detect'
    : t === 'image_classification' ? 'Img Class'
    : t === 'speech_processing' ? 'Speech'
    : t;
}

interface Props {
  requests: AIRequest[];
  loading: boolean;
  onSelect: (r: AIRequest) => void;
  wsEvents: WsEvent[];
}

export default function RequestMonitor({ requests, loading, onSelect, wsEvents }: Props) {
  // Show latest first, limit 30
  const displayed = [...requests].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  ).slice(0, 30);

  return (
    <div className="panel h-full" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="panel-header">
        <span className="panel-title">Live Request Monitor</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          {requests.length} total
        </span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading && requests.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 11 }}>
            Awaiting requests…
          </div>
        ) : requests.length === 0 ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 11, lineHeight: 1.8 }}>
            No requests yet.<br />
            Run: <code style={{ color: 'var(--accent)' }}>python mock_robot/client.py --scenario all</code>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Request ID</th>
                <th>Robot</th>
                <th>Task</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Model</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {displayed.map(r => (
                <tr key={r.request_id} onClick={() => onSelect(r)} className="animate-in">
                  <td>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--accent)' }}>
                      {r.request_id}
                    </span>
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{r.robot_id}</td>
                  <td style={{ color: 'var(--text-secondary)', fontSize: 11 }}>{taskLabel(r.task_type)}</td>
                  <td><span className={priorityClass(r.priority)}>{r.priority}</span></td>
                  <td><span className={statusClass(r.status)}>{r.status}</span></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>
                    {r.selected_model ? r.selected_model.replace(/_/g, ' ') : '—'}
                  </td>
                  <td style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-secondary)' }}>
                    {r.latency_ms ? `${r.latency_ms.toFixed(0)}ms` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

import { SystemMetrics } from '../types';

interface Props {
  metrics: SystemMetrics | null;
  loading: boolean;
}

function GaugeBar({ value, max = 100, color = 'accent' }: { value: number; max?: number; color?: string }) {
  const pct = Math.min(100, (value / max) * 100);
  const fillColor = pct > 85 ? 'var(--red)' : pct > 60 ? 'var(--yellow)' : `var(--${color})`;
  return (
    <div className="gauge-bar" style={{ marginTop: 4 }}>
      <div className="gauge-fill" style={{ width: `${pct}%`, background: fillColor }} />
    </div>
  );
}

function Metric({ label, value, sub, color }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="metric" style={{ marginBottom: 12 }}>
      <div className="metric-label">{label}</div>
      <div className="metric-value" style={{ color: color || 'var(--text-primary)', fontSize: 18 }}>{value}</div>
      {sub && <div className="metric-sub">{sub}</div>}
    </div>
  );
}

export default function SystemHealth({ metrics, loading }: Props) {
  if (loading || !metrics) {
    return (
      <div className="panel h-full">
        <div className="panel-header"><span className="panel-title">System Health</span></div>
        <div className="panel-body" style={{ color: 'var(--text-muted)', fontSize: 11 }}>
          Connecting to backend…
        </div>
      </div>
    );
  }

  const modelEntries = Object.entries(metrics.model_health);

  return (
    <div className="panel h-full" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div className="panel-header">
        <span className="panel-title">System Health</span>
      </div>
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>

        {/* Request counts */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 12px' }}>
          <Metric label="Active" value={metrics.active_requests} color="var(--yellow)" />
          <Metric label="Queued" value={metrics.queued_requests} color="var(--accent)" />
          <Metric label="Done" value={metrics.completed_requests} color="var(--green)" />
          <Metric label="Failed" value={metrics.failed_requests} color="var(--red)" />
        </div>

        <div style={{ borderTop: '1px solid var(--bg-border)', margin: '8px 0' }} />

        {/* Robots */}
        <Metric label="Robots Online"
          value={`${metrics.online_robots} / ${metrics.total_robots}`}
          color="var(--accent)" />

        <div style={{ borderTop: '1px solid var(--bg-border)', margin: '8px 0' }} />

        {/* CPU */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span className="metric-label">CPU</span>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              {metrics.cpu_percent.toFixed(1)}%
            </span>
          </div>
          <GaugeBar value={metrics.cpu_percent} />
        </div>

        {/* Memory */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span className="metric-label">Memory</span>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              {metrics.memory_percent.toFixed(1)}%
            </span>
          </div>
          <GaugeBar value={metrics.memory_percent} />
        </div>

        {/* GPU / Workers */}
        <div style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
            <span className="metric-label">Workers</span>
            <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
              {(metrics.worker_utilization * 100).toFixed(0)}%
            </span>
          </div>
          <GaugeBar value={metrics.worker_utilization * 100} color="green" />
        </div>

        <div style={{ borderTop: '1px solid var(--bg-border)', margin: '8px 0' }} />

        {/* Latency */}
        <Metric
          label="Avg Latency"
          value={`${metrics.avg_latency_ms.toFixed(0)}ms`}
          color="var(--text-primary)"
        />

        <div style={{ borderTop: '1px solid var(--bg-border)', margin: '8px 0' }} />

        {/* Model health */}
        <div className="metric-label" style={{ marginBottom: 6 }}>AI Models</div>
        {modelEntries.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 10 }}>Initializing…</div>
        ) : (
          modelEntries.map(([name, status]) => (
            <div key={name} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginBottom: 5, fontSize: 10,
            }}>
              <span style={{ color: 'var(--text-secondary)', maxWidth: 140 }} className="truncate">
                {name.replace(/_/g, ' ')}
              </span>
              <span style={{
                color: status === 'AVAILABLE' ? 'var(--green)' : 'var(--red)',
                fontFamily: 'var(--font-mono)', fontSize: 9,
                textTransform: 'uppercase',
              }}>{status}</span>
            </div>
          ))
        )}

        {/* GPU indicator */}
        <div style={{ marginTop: 8, fontSize: 10, color: 'var(--text-muted)' }}>
          GPU: {metrics.gpu_available
            ? <span style={{ color: 'var(--green)' }}>{metrics.gpu_percent ?? 0}%</span>
            : <span style={{ color: 'var(--text-muted)' }}>N/A</span>
          }
        </div>
      </div>
    </div>
  );
}

import { useEffect, useState, useCallback } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { api } from './api/client';
import { Robot, AIRequest, SystemMetrics, RequestDetail, WsEvent } from './types';
import Header from './components/Header';
import RobotFleet from './components/RobotFleet';
import RequestMonitor from './components/RequestMonitor';
import SystemHealth from './components/SystemHealth';
import EventStream from './components/EventStream';
import RobotDrawer from './components/RobotDrawer';
import RequestDrawer from './components/RequestDrawer';

const POLL_MS = 8000;

export default function App() {
  const [robots, setRobots] = useState<Robot[]>([]);
  const [requests, setRequests] = useState<AIRequest[]>([]);
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [selectedRobot, setSelectedRobot] = useState<Robot | null>(null);
  const [selectedRequest, setSelectedRequest] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);

  const { events, connected, latestEvent } = useWebSocket();

  const fetchAll = useCallback(async () => {
    try {
      const [r, req, m] = await Promise.all([
        api.getRobots(),
        api.getRequests(50),
        api.getMetrics(),
      ]);
      setRobots(r);
      setRequests(req);
      setMetrics(m);
    } catch { /* backend not yet ready */ }
    finally { setLoading(false); }
  }, []);

  // Initial load
  useEffect(() => { fetchAll(); }, [fetchAll]);

  // Refresh data when relevant WS events arrive
  useEffect(() => {
    if (!latestEvent) return;
    const refreshTypes = [
      'REQUEST_COMPLETED', 'REQUEST_FAILED', 'ROBOT_CONNECTED',
      'ROBOT_DISCONNECTED', 'RECOVERY_COMPLETED', 'REQUEST_STARTED',
    ];
    if (refreshTypes.includes(latestEvent.type)) {
      fetchAll();
    }
    // Live metrics update from RESOURCE_UPDATED
    if (latestEvent.type === 'RESOURCE_UPDATED' && latestEvent.metrics) {
      setMetrics(prev => prev ? { ...prev, ...latestEvent.metrics! } : latestEvent.metrics!);
    }
    // Live request status update from any request event
    if (latestEvent.request_id && latestEvent.status) {
      setRequests(prev => prev.map(r =>
        r.request_id === latestEvent.request_id
          ? { ...r, status: latestEvent.status as any }
          : r
      ));
    }
  }, [latestEvent, fetchAll]);

  // Background polling fallback
  useEffect(() => {
    const t = setInterval(fetchAll, POLL_MS);
    return () => clearInterval(t);
  }, [fetchAll]);

  const openRobot = async (robot: Robot) => {
    setSelectedRequest(null);
    setSelectedRobot(robot);
  };

  const openRequest = async (req: AIRequest) => {
    setSelectedRobot(null);
    try {
      const detail = await api.getRequest(req.request_id);
      setSelectedRequest(detail);
    } catch { setSelectedRequest(req as any); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      <Header connected={connected} metrics={metrics} />

      <main style={{
        flex: 1, display: 'grid', overflow: 'hidden',
        gridTemplateColumns: '220px 1fr 260px',
        gridTemplateRows: '1fr 180px',
        gap: '8px',
        padding: '8px',
      }}>
        {/* Left — Robot Fleet */}
        <div style={{ gridRow: '1 / 3', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <RobotFleet
            robots={robots}
            loading={loading}
            selected={selectedRobot?.robot_id}
            onSelect={openRobot}
            wsEvents={events}
          />
        </div>

        {/* Center top — Request Monitor */}
        <div style={{ overflow: 'hidden' }}>
          <RequestMonitor
            requests={requests}
            loading={loading}
            onSelect={openRequest}
            wsEvents={events}
          />
        </div>

        {/* Right — System Health */}
        <div style={{ gridRow: '1 / 3', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <SystemHealth metrics={metrics} loading={loading} />
        </div>

        {/* Center bottom — Event Stream */}
        <div style={{ overflow: 'hidden' }}>
          <EventStream events={events} />
        </div>
      </main>

      {/* Sliding drawers */}
      <RobotDrawer
        robot={selectedRobot}
        requests={requests.filter(r => r.robot_id === selectedRobot?.robot_id)}
        onClose={() => setSelectedRobot(null)}
        onSelectRequest={openRequest}
      />
      <RequestDrawer
        request={selectedRequest}
        onClose={() => setSelectedRequest(null)}
      />
    </div>
  );
}

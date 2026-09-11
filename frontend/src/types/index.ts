// All shared TypeScript types for PrivateBrain frontend

export type RobotStatus = 'ONLINE' | 'IDLE' | 'PROCESSING' | 'OFFLINE' | 'ERROR';
export type TaskType = 'object_detection' | 'image_classification' | 'speech_processing';
export type Priority = 'critical' | 'high' | 'normal' | 'low';
export type RequestStatus =
  | 'RECEIVED' | 'AUTHENTICATING' | 'VALIDATED' | 'QUEUED'
  | 'SCHEDULED' | 'PROCESSING' | 'COMPLETED' | 'RETRYING'
  | 'RECOVERING' | 'ERROR' | 'FAILED';

export interface Robot {
  robot_id: string;
  name: string | null;
  status: RobotStatus;
  last_seen: string | null;
  total_requests: number;
  success_count: number;
  failure_count: number;
  avg_latency_ms: number;
  created_at: string;
}

export interface AIRequest {
  request_id: string;
  robot_id: string;
  task_type: TaskType;
  priority: Priority;
  status: RequestStatus;
  selected_model: string | null;
  latency_ms: number | null;
  retry_count: number;
  created_at: string;
}

export interface RequestDetail extends AIRequest {
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  events: Array<{ event: string; message: string; timestamp: string }>;
  result: {
    model: string;
    data: Record<string, unknown>;
    confidence: number | null;
    is_fallback: boolean;
    processing_time_ms: number;
  } | null;
  agent_decisions: Array<{
    action: string;
    reason: string | null;
    model: string | null;
    timestamp: string;
  }>;
}

export interface SystemMetrics {
  total_requests: number;
  active_requests: number;
  queued_requests: number;
  completed_requests: number;
  failed_requests: number;
  avg_latency_ms: number;
  total_robots: number;
  online_robots: number;
  cpu_percent: number;
  memory_percent: number;
  gpu_percent: number | null;
  gpu_available: boolean;
  worker_utilization: number;
  ai_utilization: number;
  model_health: Record<string, string>;
}

export interface WsEvent {
  type: string;
  robot_id?: string;
  request_id?: string;
  task_type?: string;
  priority?: string;
  status?: string;
  message?: string;
  latency_ms?: number;
  model?: string;
  selected_model?: string;
  action?: string;
  reason?: string;
  retry_count?: number;
  metrics?: SystemMetrics;
  timestamp: string;
}

export interface SystemEvent {
  id: string;
  type: string;
  robot_id: string | null;
  request_id: string | null;
  message: string;
  severity: string;
  timestamp: string;
}

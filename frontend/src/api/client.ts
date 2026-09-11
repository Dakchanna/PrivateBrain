// REST API client for PrivateBrain backend

const BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Robots
  getRobots: () => request<any[]>('/robots'),
  getRobot: (id: string) => request<any>(`/robots/${id}`),
  getRobotStatus: (id: string) => request<any>(`/robots/${id}/status`),

  // Requests
  getRequests: (limit = 50) => request<any[]>(`/requests?limit=${limit}`),
  getRequest: (id: string) => request<any>(`/requests/${id}`),
  getResult: (id: string) => request<any>(`/requests/${id}/result`),

  // System
  getMetrics: () => request<any>('/system/metrics'),
  getStatus: () => request<any>('/system/status'),
  getEvents: (limit = 100) => request<any[]>(`/system/events?limit=${limit}`),
};
